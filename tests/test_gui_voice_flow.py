"""Exercise the upload/save/select/script flow without a microphone or model."""

import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import soundfile as sf

from heyclone.gpu.detect import DetectionResult
from heyclone.voice.library import VoiceLibrary


@unittest.skipUnless(os.name == "nt" or os.environ.get("DISPLAY"), "Needs a desktop display")
class TestVoiceFlow(unittest.TestCase):
    def test_upload_create_select_and_generate(self):
        from heyclone.gui import HeyCloneApp
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "voice.wav"
            sf.write(source, 0.1 * np.sin(np.arange(64000) * 0.1), 16000)
            with mock.patch("heyclone.gui.detect_gpus", return_value=DetectionResult(gpus=[])), \
                 mock.patch("heyclone.gui.VoiceLibrary", return_value=VoiceLibrary(root / "library")):
                app = HeyCloneApp()
            app.withdraw()
            try:
                with mock.patch("heyclone.gui.filedialog.askopenfilename", return_value=str(source)):
                    app._upload_voice()
                self.assertEqual(app.voice_name_var.get(), "voice")
                app._save_voice()
                self._wait(app)
                self.assertEqual(len(app._voice_map), 1)
                app.script_box.insert("1.0", "Hello from my saved voice.")
                def generate(reference, text, output, language):
                    self.assertTrue(Path(reference).is_file())
                    self.assertEqual(text, "Hello from my saved voice.")
                    sf.write(output, np.ones(1000) * 0.1, 16000)
                    return SimpleNamespace(output_path=str(output))
                with mock.patch("heyclone.gui.VoiceCloner") as cloner:
                    cloner.return_value.clone_voice.side_effect = generate
                    app._clone_voice()
                    self._wait(app)
                    cloner.return_value.clone_voice.assert_called_once()
                self.assertTrue(app._last_speech.is_file())
                self.assertEqual(app.play_button.cget("state"), "normal")
            finally:
                app.destroy()

    def _wait(self, app):
        deadline = time.monotonic() + 20
        while app._busy and time.monotonic() < deadline:
            app.update()
            time.sleep(0.02)
        self.assertFalse(app._busy, "Background operation did not complete")
