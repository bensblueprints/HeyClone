"""PyInstaller entry point for the HeyClone desktop application.

Build a standalone Windows GUI executable from the project root:

    packaging\\windows\\build-exe.bat

Run HeyClone.exe --check-opencv to check the bundled detector (exit code 0
on success, 1 on failure) without opening the GUI.
"""

import sys

if __name__ == "__main__":
    if "--check-voice-engine" in sys.argv:
        try:
            from heyclone.voice.clone import VoiceCloner
            from heyclone.gpu.detect import DetectionResult

            index = sys.argv.index("--check-voice-engine")
            engine, reference, output = sys.argv[index + 1:index + 4]
            VoiceCloner(detection=DetectionResult(gpus=[]), use_runtime=True, engine=engine).clone_voice(
                reference, "Hello. The voice engine is working inside HeyClone.", output)
        except Exception:
            sys.exit(1)
        sys.exit(0)

    # Allows CI to verify the native library and cascade inside the frozen app.
    if "--check-opencv" in sys.argv or "--check-installation" in sys.argv:
        try:
            from heyclone.avatar.opencv import load_face_detector
            import numpy as np

            cv2, cascade = load_face_detector()
            cascade.detectMultiScale(np.zeros((128, 128), dtype=np.uint8))
            if "--check-installation" in sys.argv:
                import sounddevice
                import soundfile
                from heyclone.gui import HeyCloneApp

                sounddevice.get_portaudio_version()
                assert "WAV" in soundfile.available_formats()
                from pathlib import Path
                import heyclone
                license_dir = Path(heyclone.__file__).parent / "voice" / "licenses"
                assert "Coqui Public Model License" in (license_dir / "XTTS.txt").read_text(encoding="utf-8")
                assert "MIT License" in (license_dir / "Chatterbox.txt").read_text(encoding="utf-8")
                app = HeyCloneApp()
                app.withdraw()
                app.update()
                app.destroy()
        except Exception:
            sys.exit(1)
        sys.exit(0)

    from heyclone.gui import launch_gui

    launch_gui()
