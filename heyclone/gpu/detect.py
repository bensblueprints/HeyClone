"""GPU enumeration and VRAM tiering.

HeyClone (a talking-head lip-sync / avatar pipeline) needs to know how much
video memory is available so it can pick a runtime preset — e.g. a 32 GB card
runs full-resolution fp32, while an 8 GB card drops the face-crop resolution and
switches to fp16 / layer offloading.

Detection tries backends in order of reliability and falls back gracefully:

1. ``pynvml``        — NVML binding (exact bytes, programmatic).
2. ``nvidia-smi``    — CLI query (exact MB).
3. ``torch.cuda``    — CUDA runtime (if torch is installed).
4. ``rocm-smi``      — ROCm CLI (exact MB).
5. Windows WMI        — last resort; presence + approximate memory only.

A machine with no discrete GPU (e.g. integrated graphics or CPU-only) is
reported as ``VramTier.NONE`` rather than crashing.
"""

from __future__ import annotations

import csv
import io
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class GpuBackend(str, Enum):
    """Which mechanism produced the GPU information."""

    NVML = "nvml"
    NVIDIA_SMI = "nvidia-smi"
    TORCH = "torch"
    ROCM = "rocm-smi"
    WINDOWS_WMI = "wmi"
    NONE = "none"


class VramTier(str, Enum):
    """Coarse VRAM buckets used to select model/runtime presets."""

    NONE = "none"   # no usable discrete GPU
    LOW = "low"     # < 6 GB — CPU / aggressive offload only
    GB8 = "8gb"     # ~8 GB
    GB16 = "16gb"   # ~16 GB
    GB32 = "32gb"   # ~24 GB and above


@dataclass
class GpuInfo:
    """A single detected GPU."""

    index: int
    name: str
    total_mb: int
    backend: GpuBackend
    is_cuda: bool = False

    @property
    def total_gb(self) -> float:
        return round(self.total_mb / 1024.0, 2)

    @property
    def tier(self) -> VramTier:
        return classify_vram(self.total_mb)


@dataclass
class DetectionResult:
    """The outcome of a full GPU scan."""

    gpus: list[GpuInfo] = field(default_factory=list)
    backend: GpuBackend = GpuBackend.NONE
    note: str = ""

    @property
    def best_gpu(self) -> Optional[GpuInfo]:
        """The GPU with the most VRAM, or ``None`` if nothing was found."""
        if not self.gpus:
            return None
        return max(self.gpus, key=lambda g: g.total_mb)

    @property
    def tier(self) -> VramTier:
        gpu = self.best_gpu
        return VramTier.NONE if gpu is None else gpu.tier

    @property
    def has_cuda(self) -> bool:
        return any(g.is_cuda for g in self.gpus)


def classify_vram(total_mb: int) -> VramTier:
    """Map a GPU's total memory (in MB) to the closest preset tier.

    Boundaries are deliberately generous so that e.g. a 24 GB RTX 3090/4090
    selects the 32 GB preset and a 6 GB laptop GPU still selects the 8 GB preset.
    """
    gb = total_mb / 1024.0
    if gb < 6:
        return VramTier.LOW
    if gb < 12:
        return VramTier.GB8
    if gb < 24:
        return VramTier.GB16
    return VramTier.GB32


def _try_nvml() -> Optional[list[GpuInfo]]:
    try:
        import warnings

        with warnings.catch_warnings():
            # The PyPI "pynvml" package is a deprecated shim over nvidia-ml-py;
            # its API is unchanged, so silence the FutureWarning it emits.
            warnings.simplefilter("ignore", FutureWarning)
            import pynvml  # type: ignore
    except ImportError:
        return None
    try:
        pynvml.nvmlInit()
    except Exception:
        return None
    try:
        gpus: list[GpuInfo] = []
        for i in range(pynvml.nvmlDeviceGetCount()):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            raw_name = pynvml.nvmlDeviceGetName(handle)
            name = raw_name.decode("utf-8", "replace") if isinstance(raw_name, bytes) else str(raw_name)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            total_mb = int(mem.total / (1024 * 1024))
            gpus.append(GpuInfo(i, name, total_mb, GpuBackend.NVML, is_cuda=True))
        return gpus or None
    except Exception:
        return None
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass


def _try_nvidia_smi() -> Optional[list[GpuInfo]]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, "--query-gpu=index,name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    gpus: list[GpuInfo] = []
    for line in proc.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            idx = int(parts[0])
            total_mb = int(float(parts[2]))
        except ValueError:
            continue
        gpus.append(GpuInfo(idx, parts[1], total_mb, GpuBackend.NVIDIA_SMI, is_cuda=True))
    return gpus or None


def _try_torch() -> Optional[list[GpuInfo]]:
    try:
        import torch  # type: ignore
    except ImportError:
        return None
    if not torch.cuda.is_available():
        return None
    gpus: list[GpuInfo] = []
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        name = torch.cuda.get_device_name(i)
        total_mb = int(props.total_memory / (1024 * 1024))
        gpus.append(GpuInfo(i, name, total_mb, GpuBackend.TORCH, is_cuda=True))
    return gpus or None


def _try_rocm() -> Optional[list[GpuInfo]]:
    exe = shutil.which("rocm-smi")
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, "--showmeminfo", "vram", "--csv"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    gpus: list[GpuInfo] = []
    for line in proc.stdout.strip().splitlines():
        if not line or line.startswith("device"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        try:
            idx = int(parts[0].removeprefix("card"))
            total_mb = int(float(parts[1]))
        except ValueError:
            continue
        gpus.append(GpuInfo(idx, f"AMD GPU {idx}", total_mb, GpuBackend.ROCM))
    return gpus or None


def _try_windows_wmi() -> Optional[list[GpuInfo]]:
    if sys.platform != "win32":
        return None
    cmd = (
        "Get-CimInstance Win32_VideoController | "
        "Select-Object Name, AdapterRAM | ConvertTo-Csv -NoTypeInformation"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=25,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    gpus: list[GpuInfo] = []
    reader = csv.DictReader(io.StringIO(proc.stdout))
    for i, row in enumerate(reader):
        name = (row.get("Name") or "Unknown GPU").strip()
        raw_ram = (row.get("AdapterRAM") or "").strip()
        try:
            total_mb = int(int(raw_ram) / (1024 * 1024)) if raw_ram else 0
        except ValueError:
            total_mb = 0
        # WMI's AdapterRAM is a 32-bit value and can under-report discrete VRAM,
        # so only the presence (not exact memory) should be trusted here.
        gpus.append(GpuInfo(i, name, total_mb, GpuBackend.WINDOWS_WMI))
    return gpus or None


_BACKENDS: list[Callable[[], Optional[list[GpuInfo]]]] = [
    _try_nvml,
    _try_nvidia_smi,
    _try_torch,
    _try_rocm,
    _try_windows_wmi,
]


def detect_gpus() -> DetectionResult:
    """Enumerate GPUs using the first backend that returns a result."""
    for fn in _BACKENDS:
        gpus = fn()
        if gpus:
            backend = gpus[0].backend
            note = ""
            if backend is GpuBackend.WINDOWS_WMI:
                note = (
                    "VRAM reported via Windows is approximate; install the NVIDIA "
                    "driver + nvidia-smi (or pynvml/torch) for exact detection."
                )
            return DetectionResult(gpus=gpus, backend=backend, note=note)
    return DetectionResult(
        gpus=[],
        backend=GpuBackend.NONE,
        note="No usable GPU detected — running in CPU-only mode.",
    )
