"""PyInstaller entry point for the HeyClone desktop application.

Build a standalone Windows GUI executable from the project root:

    packaging\\windows\\build-exe.bat

Run HeyClone.exe --check-opencv to check the bundled detector (exit code 0
on success, 1 on failure) without opening the GUI.
"""

import sys

if __name__ == "__main__":
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
                app = HeyCloneApp()
                app.withdraw()
                app.update()
                app.destroy()
        except Exception:
            sys.exit(1)
        sys.exit(0)

    from heyclone.gui import launch_gui

    launch_gui()
