"""Modern CustomTkinter GUI for HeyClone.

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
from tkinter import filedialog

import customtkinter as ctk

from .avatar.clone import AvatarCloner
from .config import get_preset
from .doctor import check_environment
from .gpu.detect import detect_gpus
from .voice.clone import VoiceCloner

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Palette
ACCENT = "#6366f1"
ACCENT_HOVER = "#4f46e5"
SUCCESS = "#22c55e"
DANGER = "#ef4444"
CARD = "#242424"
BORDER = "#2f2f2f"
MUTED = "#9ca3af"

_AUDIO_TYPES = [("Audio", "*.wav *.mp3 *.flac *.m4a *.ogg"), ("All files", "*.*")]
_SOURCE_TYPES = [
    ("Image / Video", "*.jpg *.jpeg *.png *.bmp *.webp *.mp4 *.mov *.avi *.mkv *.webm"),
    ("All files", "*.*"),
]


def _font(size: int = 14, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)


class HeyCloneApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("HeyClone")
        self.geometry("1000x720")
        self.minsize(880, 620)

        self._queue: queue.Queue = queue.Queue()
        self._busy = False
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._sections: dict[str, ctk.CTkFrame] = {}
        self.detection = detect_gpus()

        self._build_layout()
        self._refresh_gpu()
        self.show_section("detect")

    # ------------------------------------------------------------- layout
    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()

        status = ctk.CTkFrame(self, corner_radius=0, fg_color="#1a1a1a", height=34)
        status.grid(row=1, column=0, columnspan=2, sticky="ew")
        status.grid_columnconfigure(1, weight=1)
        self.progress = ctk.CTkProgressBar(status, width=120, mode="indeterminate")
        self.progress.grid(row=0, column=0, padx=(14, 10), pady=6)
        self.progress.set(0)
        self.progress.stop()
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(status, textvariable=self.status_var, font=_font(12), text_color=MUTED, anchor="w")
        self.status_label.grid(row=0, column=1, sticky="w")

    def _build_sidebar(self) -> None:
        side = ctk.CTkFrame(self, width=230, corner_radius=0, fg_color="#1a1a1a")
        side.grid(row=0, column=0, sticky="nsw")
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(side, text="HeyClone", font=_font(24, "bold"), text_color="#ffffff").grid(
            row=0, column=0, padx=24, pady=(26, 2), sticky="w"
        )
        ctk.CTkLabel(side, text="Avatar & voice cloning", font=_font(12), text_color=MUTED).grid(
            row=1, column=0, padx=24, pady=(0, 22), sticky="w"
        )

        for i, (key, label) in enumerate(
            [("detect", "Detect"), ("voice", "Voice Clone"), ("avatar", "Avatar"), ("clone", "Full Clone")]
        ):
            btn = ctk.CTkButton(
                side,
                text=label,
                height=40,
                corner_radius=8,
                fg_color="transparent",
                hover_color="#2b2b2b",
                anchor="w",
                font=_font(14),
                command=lambda k=key: self.show_section(k),
            )
            btn.grid(row=2 + i, column=0, padx=14, pady=3, sticky="ew")
            self._nav_buttons[key] = btn

        self.side_gpu = ctk.CTkLabel(
            side, text="", font=_font(11), text_color=MUTED, wraplength=190, justify="left"
        )
        self.side_gpu.grid(row=99, column=0, padx=20, pady=20, sticky="sw")

    def _build_content(self) -> None:
        content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        content.grid(row=0, column=1, sticky="nsew", padx=26, pady=26)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self._sections["detect"] = self._build_detect(content)
        self._sections["voice"] = self._build_voice(content)
        self._sections["avatar"] = self._build_avatar(content)
        self._sections["clone"] = self._build_clone(content)

    def _section(self, parent, title: str, subtitle: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, corner_radius=0, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=title, font=_font(26, "bold"), text_color="#ffffff").grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(frame, text=subtitle, font=_font(13), text_color=MUTED).grid(
            row=1, column=0, sticky="w", pady=(2, 18)
        )
        return frame

    def _card(self, parent, row: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=14, fg_color=CARD, border_width=1, border_color=BORDER)
        card.grid(row=row, column=0, sticky="ew", pady=8)
        card.grid_columnconfigure(1, weight=1)
        return card

    # ----------------------------------------------------------- sections
    def _build_detect(self, parent) -> ctk.CTkFrame:
        frame = self._section(parent, "Detect", "GPU, VRAM tier, and environment readiness")
        frame.grid_rowconfigure(3, weight=1)

        card = self._card(frame, 2)
        self.gpu_var = tk.StringVar(value="Detecting ...")
        self.preset_var = tk.StringVar(value="")
        ctk.CTkLabel(card, text="GPU", font=_font(13, "bold"), text_color=ACCENT).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 2)
        )
        ctk.CTkLabel(card, textvariable=self.gpu_var, font=_font(17, "bold"), text_color="#ffffff", wraplength=560, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=18
        )
        ctk.CTkLabel(card, textvariable=self.preset_var, font=_font(13), text_color=MUTED, wraplength=560, justify="left").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=18, pady=(2, 14)
        )
        ctk.CTkButton(
            card, text="Re-detect GPU", width=150, height=34, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=_font(13),
            command=self._detect_gpu,
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 16))

        card2 = self._card(frame, 3)
        card2.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(card2, text="Environment", font=_font(13, "bold"), text_color=ACCENT).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 2)
        )
        ctk.CTkButton(
            card2, text="Run check", width=120, height=32, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=_font(13),
            command=self._run_doctor,
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(4, 12))
        self.doctor_text = ctk.CTkTextbox(card2, corner_radius=8, fg_color="#1b1b1b", border_width=1, border_color=BORDER, font=_font(13))
        self.doctor_text.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 16))
        self.doctor_text.configure(state="disabled")
        return frame

    def _build_voice(self, parent) -> ctk.CTkFrame:
        frame = self._section(parent, "Voice Clone", "Clone a voice from a reference clip")
        card = self._card(frame, 2)
        self.ref_var = self._field(card, 0, "Reference audio (6-15s clip)")
        self._browse(card, 0, self.ref_var, _AUDIO_TYPES, "audio")
        self.text_var = self._field(card, 1, "Text to speak")
        self.lang_var = self._field(card, 2, "Language code", "en")
        self.out_voice_var = self._field(card, 3, "Output audio (.wav)")
        self._browse(card, 3, self.out_voice_var, [("WAV", "*.wav")], "saveaudio")
        ctk.CTkButton(
            card, text="Clone Voice", height=42, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=_font(14, "bold"),
            command=self._clone_voice,
        ).grid(row=4, column=1, sticky="w", pady=(18, 16))
        self.voice_result = self._result_box(frame, 3)
        return frame

    def _build_avatar(self, parent) -> ctk.CTkFrame:
        frame = self._section(parent, "Avatar", "Detect and crop the face for the avatar")
        card = self._card(frame, 2)
        self.src_var = self._field(card, 0, "Source image or video")
        self._browse(card, 0, self.src_var, _SOURCE_TYPES, "source")
        ctk.CTkButton(
            card, text="Prepare Avatar", height=42, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=_font(14, "bold"),
            command=self._prepare_avatar,
        ).grid(row=1, column=1, sticky="w", pady=(18, 16))
        self.avatar_result = self._result_box(frame, 3)
        return frame

    def _build_clone(self, parent) -> ctk.CTkFrame:
        frame = self._section(parent, "Full Clone", "Avatar + cloned voice -> talking avatar")
        card = self._card(frame, 2)
        self.c_src_var = self._field(card, 0, "Source image or video")
        self._browse(card, 0, self.c_src_var, _SOURCE_TYPES, "source2")
        self.c_ref_var = self._field(card, 1, "Reference audio (voice)")
        self._browse(card, 1, self.c_ref_var, _AUDIO_TYPES, "audio2")
        self.c_text_var = self._field(card, 2, "Text to speak")
        self.c_lang_var = self._field(card, 3, "Language code", "en")
        self.c_out_var = self._field(card, 4, "Output video (.mp4)")
        self._browse(card, 4, self.c_out_var, [("MP4", "*.mp4"), ("All files", "*.*")], "savevideo")
        ctk.CTkButton(
            card, text="Create Clone", height=42, corner_radius=8,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=_font(14, "bold"),
            command=self._full_clone,
        ).grid(row=5, column=1, sticky="w", pady=(18, 16))
        self.clone_result = self._result_box(frame, 3)
        return frame

    # ---------------------------------------------------------- widgets
    def _field(self, card: ctk.CTkFrame, row: int, label: str, default: str = "") -> tk.StringVar:
        ctk.CTkLabel(card, text=label, font=_font(13), text_color="#d1d5db").grid(
            row=row, column=0, sticky="w", padx=18, pady=8
        )
        var = tk.StringVar(value=default)
        ctk.CTkEntry(
            card, textvariable=var, height=38, corner_radius=8,
            fg_color="#1b1b1b", border_color=BORDER, font=_font(13),
        ).grid(row=row, column=1, sticky="ew", padx=(12, 18), pady=8)
        return var

    def _browse(self, card: ctk.CTkFrame, row: int, var: tk.StringVar, filetypes, kind: str) -> None:
        def choose():
            if kind in ("audio", "audio2", "source", "source2"):
                path = filedialog.askopenfilename(filetypes=filetypes)
            else:
                ext = ".wav" if kind == "saveaudio" else ".mp4"
                path = filedialog.asksaveasfilename(filetypes=filetypes, defaultextension=ext)
            if path:
                var.set(path)

        ctk.CTkButton(
            card, text="Browse", width=90, height=38, corner_radius=8,
            fg_color="#2b2b2b", hover_color="#363636", font=_font(13),
            command=choose,
        ).grid(row=row, column=2, padx=(0, 18), pady=8)

    def _result_box(self, frame: ctk.CTkFrame, row: int) -> ctk.CTkTextbox:
        box = ctk.CTkTextbox(
            frame, height=64, corner_radius=10, fg_color=CARD,
            border_width=1, border_color=BORDER, font=_font(13),
        )
        box.grid(row=row, column=0, sticky="ew", pady=(4, 0))
        box.configure(state="disabled")
        return box

    # ------------------------------------------------------------ nav
    def show_section(self, name: str) -> None:
        for key, frame in self._sections.items():
            if key == name:
                frame.grid()
            else:
                frame.grid_remove()
        for key, btn in self._nav_buttons.items():
            if key == name:
                btn.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", hover_color="#2b2b2b", text_color="#e5e7eb")

    # ---------------------------------------------------------- actions
    def _refresh_gpu(self) -> None:
        if not self.detection.gpus:
            self.gpu_var.set("No discrete GPU detected")
            self.preset_var.set("CPU-only mode — voice cloning only (very slow).")
            self.side_gpu.configure(text="No discrete GPU\nCPU-only mode")
            return
        best = self.detection.best_gpu
        preset = get_preset(best.tier)
        self.gpu_var.set(f"{best.name}  ·  {best.total_gb:.2f} GB")
        self.preset_var.set(
            f"{preset.label}  ·  {preset.face_resolution[0]}x{preset.face_resolution[1]}  ·  "
            f"{preset.model_precision}  ·  batch {preset.max_batch_size}"
        )
        self.side_gpu.configure(text=f"{best.tier.value.upper()} tier\n{best.total_gb:.2f} GB")

    def _detect_gpu(self) -> None:
        self.detection = detect_gpus()
        self._refresh_gpu()
        self._set_status("GPU re-detected", SUCCESS)

    def _run_doctor(self) -> None:
        def fn():
            checks = check_environment(detection=self.detection)
            return "\n".join(
                f"[{'OK  ' if c.ok else 'MISS'}] {c.name}: {c.status}" for c in checks
            )

        self._run_async(fn, self.doctor_text, "Running environment check")

    def _clone_voice(self) -> None:
        ref, text, out, lang = self._voice_inputs()
        if not ref or not text or not out:
            self._show_error(self.voice_result, "Please fill in reference audio, text, and output audio.")
            return
        cloner = VoiceCloner(detection=self.detection)

        def fn():
            r = cloner.clone_voice(ref, text, out, lang)
            return f"Saved voice to {r.output_path}\nSample rate: {r.sample_rate} Hz · GPU: {r.gpu_used}"

        self._run_async(fn, self.voice_result, "Cloning voice")

    def _prepare_avatar(self) -> None:
        src = self.src_var.get().strip()
        if not src:
            self._show_error(self.avatar_result, "Please choose a source image or video.")
            return
        cloner = AvatarCloner(detection=self.detection)

        def fn():
            p = cloner.prepare(src)
            return (
                f"Face crop: {p.face_crop_path or 'no face detected'}\n"
                f"Faces: {p.num_faces} · Resolution: {p.face_resolution[0]}x{p.face_resolution[1]}"
            )

        self._run_async(fn, self.avatar_result, "Preparing avatar")

    def _full_clone(self) -> None:
        src = self.c_src_var.get().strip()
        ref = self.c_ref_var.get().strip()
        text = self.c_text_var.get().strip()
        out = self.c_out_var.get().strip()
        lang = self.c_lang_var.get().strip() or "en"
        if not (src and ref and text and out):
            self._show_error(self.clone_result, "Please fill in source, reference audio, text, and output video.")
            return
        avatar = AvatarCloner(detection=self.detection)
        voice = VoiceCloner(detection=self.detection)

        def fn():
            profile = avatar.prepare(src)
            voice_out = Path(out).with_name("cloned_voice.wav")
            vres = voice.clone_voice(ref, text, voice_out, lang)
            ares = avatar.animate(profile, vres.output_path, out)
            return f"Talking avatar saved to {ares.output_video}"

        self._run_async(fn, self.clone_result, "Creating clone")

    def _voice_inputs(self):
        return (
            self.ref_var.get().strip(),
            self.text_var.get().strip(),
            self.out_voice_var.get().strip(),
            self.lang_var.get().strip() or "en",
        )

    # ------------------------------------------------------- background
    def _run_async(self, fn, result_box: ctk.CTkTextbox, label: str) -> None:
        if self._busy:
            self._set_status("Busy — another operation is running", DANGER)
            return
        self._busy = True
        self._set_status(f"{label} ...", ACCENT)
        self.progress.start()

        def worker():
            try:
                self._queue.put(("ok", fn()))
            except Exception as exc:  # noqa: BLE001
                self._queue.put(("err", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_queue(result_box, label)

    def _poll_queue(self, result_box: ctk.CTkTextbox, label: str) -> None:
        try:
            status, payload = self._queue.get_nowait()
        except queue.Empty:
            self.after(100, lambda: self._poll_queue(result_box, label))
            return
        self._busy = False
        self.progress.stop()
        if status == "ok":
            self._set_status(f"Done — {label}", SUCCESS)
            self._show_ok(result_box, payload)
        else:
            self._set_status(f"Failed — {label}", DANGER)
            self._show_error(result_box, payload)

    # ----------------------------------------------------------- helpers
    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.status_var.set(text)
        self.status_label.configure(text_color=color)

    def _set_textbox(self, box: ctk.CTkTextbox, text: str) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", text)
        box.configure(state="disabled")

    def _show_ok(self, box: ctk.CTkTextbox, text: str) -> None:
        self._set_textbox(box, text)

    def _show_error(self, box: ctk.CTkTextbox, text: str) -> None:
        self._set_textbox(box, text)


def launch_gui() -> None:
    """Open the HeyClone GUI and block until the window is closed."""
    app = HeyCloneApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
