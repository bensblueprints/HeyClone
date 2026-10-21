"""Tkinter GUI for HeyClone.

Launch with:
    heyclone gui            (via the CLI)
    heyclone-gui            (dedicated entry point)
    python -m heyclone.gui
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .avatar.clone import AvatarCloner
from .config import get_preset
from .doctor import check_environment
from .gpu.detect import detect_gpus
from .voice.clone import VoiceCloner

_AUDIO_TYPES = [("Audio", "*.wav *.mp3 *.flac *.m4a *.ogg"), ("All files", "*.*")]
_SOURCE_TYPES = [
    ("Image / Video", "*.jpg *.jpeg *.png *.bmp *.webp *.mp4 *.mov *.avi *.mkv *.webm"),
    ("All files", "*.*"),
]


class HeyCloneApp:
    """Main application window."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("HeyClone")
        root.geometry("780x700")
        root.minsize(640, 560)

        self.detection = detect_gpus()
        self._queue: queue.Queue = queue.Queue()
        self._busy = False

        self._build_ui()
        self._refresh_gpu()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self._build_detect_tab(nb)
        self._build_voice_tab(nb)
        self._build_avatar_tab(nb)
        self._build_clone_tab(nb)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w", padding=(8, 4)).pack(
            fill="x", side="bottom"
        )

    def _build_detect_tab(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, padding=12)
        nb.add(tab, text="Detect")

        ttk.Label(tab, text="GPU", font=("", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.gpu_var = tk.StringVar(value="Detecting ...")
        ttk.Label(tab, textvariable=self.gpu_var, wraplength=660).grid(row=1, column=0, sticky="w", pady=(0, 4))
        self.preset_var = tk.StringVar(value="")
        ttk.Label(tab, textvariable=self.preset_var, wraplength=660).grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Button(tab, text="Re-detect GPU", command=self._detect_gpu).grid(row=3, column=0, sticky="w")

        ttk.Label(tab, text="Environment", font=("", 12, "bold")).grid(row=4, column=0, sticky="w", pady=(16, 0))
        ttk.Button(tab, text="Run Doctor (check dependencies)", command=self._run_doctor).grid(
            row=5, column=0, sticky="w", pady=(4, 4)
        )
        self.doctor_text = tk.Text(tab, height=14, width=84, wrap="word")
        self.doctor_text.grid(row=6, column=0, sticky="nsew")
        tab.rowconfigure(6, weight=1)
        tab.columnconfigure(0, weight=1)

    def _build_voice_tab(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, padding=12)
        nb.add(tab, text="Voice Clone")

        ttk.Label(tab, text="Clone a voice and synthesize speech", font=("", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        self.ref_var = self._field(tab, 1, "Reference audio (6-15s clip)")
        self._browse(tab, 1, self.ref_var, _AUDIO_TYPES, "audio")

        self.text_var = self._field(tab, 2, "Text to speak")
        self.lang_var = self._field(tab, 3, "Language code", "en")

        self.out_voice_var = self._field(tab, 4, "Output audio (.wav)")
        self._browse(tab, 4, self.out_voice_var, [("WAV", "*.wav")], "saveaudio")

        ttk.Button(tab, text="Clone Voice", command=self._clone_voice).grid(row=5, column=1, sticky="w", pady=(12, 0))

    def _build_avatar_tab(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, padding=12)
        nb.add(tab, text="Avatar")

        ttk.Label(tab, text="Build the face avatar (detect + crop)", font=("", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        self.src_var = self._field(tab, 1, "Source image or video")
        self._browse(tab, 1, self.src_var, _SOURCE_TYPES, "source")

        ttk.Button(tab, text="Prepare Avatar", command=self._prepare_avatar).grid(row=2, column=1, sticky="w", pady=(12, 0))

    def _build_clone_tab(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, padding=12)
        nb.add(tab, text="Full Clone")

        ttk.Label(tab, text="Avatar + cloned voice -> talking avatar", font=("", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        self.c_src_var = self._field(tab, 1, "Source image or video")
        self._browse(tab, 1, self.c_src_var, _SOURCE_TYPES, "source2")

        self.c_ref_var = self._field(tab, 2, "Reference audio (voice)")
        self._browse(tab, 2, self.c_ref_var, _AUDIO_TYPES, "audio2")

        self.c_text_var = self._field(tab, 3, "Text to speak")
        self.c_lang_var = self._field(tab, 4, "Language code", "en")

        self.c_out_var = self._field(tab, 5, "Output video (.mp4)")
        self._browse(tab, 5, self.c_out_var, [("MP4", "*.mp4"), ("All files", "*.*")], "savevideo")

        ttk.Button(tab, text="Create Clone", command=self._full_clone).grid(row=6, column=1, sticky="w", pady=(12, 0))

    # ---------------------------------------------------------- widgets
    def _field(self, tab: ttk.Frame, row: int, label: str, default: str = "") -> tk.StringVar:
        ttk.Label(tab, text=label).grid(row=row, column=0, sticky="w", pady=4)
        var = tk.StringVar(value=default)
        ttk.Entry(tab, textvariable=var, width=52).grid(row=row, column=1, sticky="we", pady=4)
        tab.columnconfigure(1, weight=1)
        return var

    def _browse(self, tab: ttk.Frame, row: int, var: tk.StringVar, filetypes, kind: str) -> None:
        def choose():
            if kind in ("audio", "audio2", "source", "source2"):
                path = filedialog.askopenfilename(filetypes=filetypes)
            else:
                path = filedialog.asksaveasfilename(filetypes=filetypes, defaultextension=".wav" if kind == "saveaudio" else ".mp4")
            if path:
                var.set(path)

        ttk.Button(tab, text="Browse...", command=choose).grid(row=row, column=2, padx=(6, 0))

    # ---------------------------------------------------------- actions
    def _refresh_gpu(self) -> None:
        if not self.detection.gpus:
            self.gpu_var.set("No discrete GPU detected (CPU-only mode).")
            self.preset_var.set("Preset: CPU-only — voice cloning only (very slow).")
            return
        best = self.detection.best_gpu
        preset = get_preset(best.tier)
        self.gpu_var.set(f"{best.name} — {best.total_gb:.2f} GB ({best.tier.value} tier)")
        self.preset_var.set(
            f"Preset: {preset.label} — {preset.face_resolution[0]}x{preset.face_resolution[1]}, "
            f"{preset.model_precision}, batch {preset.max_batch_size}"
        )

    def _detect_gpu(self) -> None:
        self.detection = detect_gpus()
        self._refresh_gpu()
        self._set_status("GPU re-detected.")

    def _run_doctor(self) -> None:
        def fn():
            checks = check_environment(detection=self.detection)
            lines = []
            for c in checks:
                mark = "OK  " if c.ok else "MISS"
                lines.append(f"[{mark}] {c.name}: {c.status}")
            return "\n".join(lines)

        def done(payload: str):
            self.doctor_text.delete("1.0", "end")
            self.doctor_text.insert("1.0", payload)

        self._run_async(fn, done, "Running doctor")

    def _clone_voice(self) -> None:
        ref, text, out, lang = self._voice_inputs()
        if not ref or not text or not out:
            messagebox.showerror("HeyClone", "Please fill in reference audio, text, and output audio.")
            return

        cloner = VoiceCloner(detection=self.detection)

        def fn():
            result = cloner.clone_voice(ref, text, out, lang)
            return f"Saved voice to {result.output_path}\nSample rate: {result.sample_rate} Hz\nGPU: {result.gpu_used}"

        self._run_async(fn, None, "Cloning voice")

    def _prepare_avatar(self) -> None:
        src = self.src_var.get().strip()
        if not src:
            messagebox.showerror("HeyClone", "Please choose a source image or video.")
            return

        cloner = AvatarCloner(detection=self.detection)

        def fn():
            profile = cloner.prepare(src)
            return (
                f"Face crop: {profile.face_crop_path or 'no face detected'}\n"
                f"Faces found: {profile.num_faces}\n"
                f"Resolution: {profile.face_resolution[0]}x{profile.face_resolution[1]}"
            )

        self._run_async(fn, None, "Preparing avatar")

    def _full_clone(self) -> None:
        src = self.c_src_var.get().strip()
        ref = self.c_ref_var.get().strip()
        text = self.c_text_var.get().strip()
        out = self.c_out_var.get().strip()
        lang = self.c_lang_var.get().strip() or "en"

        if not src or not ref or not text or not out:
            messagebox.showerror("HeyClone", "Please fill in source, reference audio, text, and output video.")
            return

        avatar = AvatarCloner(detection=self.detection)
        voice = VoiceCloner(detection=self.detection)

        def fn():
            profile = avatar.prepare(src)
            voice_out = Path(out).with_name("cloned_voice.wav")
            vres = voice.clone_voice(ref, text, voice_out, lang)
            ares = avatar.animate(profile, vres.output_path, out)
            return f"Talking avatar saved to {ares.output_video}"

        self._run_async(fn, None, "Creating clone")

    def _voice_inputs(self):
        return (
            self.ref_var.get().strip(),
            self.text_var.get().strip(),
            self.out_voice_var.get().strip(),
            self.lang_var.get().strip() or "en",
        )

    # ------------------------------------------------------- background
    def _run_async(self, fn, done_cb, label: str) -> None:
        if self._busy:
            messagebox.showinfo("HeyClone", "Another operation is already running.")
            return
        self._busy = True
        self._set_status(f"{label} ...")

        def worker():
            try:
                result = fn()
                self._queue.put(("ok", result))
            except Exception as exc:  # noqa: BLE001
                self._queue.put(("err", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_queue(done_cb, label)

    def _poll_queue(self, done_cb, label: str) -> None:
        try:
            status, payload = self._queue.get_nowait()
        except queue.Empty:
            self.root.after(100, lambda: self._poll_queue(done_cb, label))
            return

        self._busy = False
        if status == "ok":
            self._set_status(f"Done: {label}")
            messagebox.showinfo("HeyClone", f"{label} complete.\n\n{payload}")
            if done_cb:
                done_cb(payload)
        else:
            self._set_status(f"Failed: {label}")
            messagebox.showerror("HeyClone", f"{label} failed:\n\n{payload}")

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)


def launch_gui() -> None:
    """Open the HeyClone GUI and block until the window is closed."""
    root = tk.Tk()
    HeyCloneApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
