import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from heyclone.voice import runtime


class TestVoiceEngines(unittest.TestCase):
    def test_engines_are_isolated_and_readiness_is_model_specific(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("heyclone.voice.library.data_dir", return_value=Path(tmp)):
            nano = runtime.runtime_python("nano")
            xtts = runtime.runtime_python("xtts")
            self.assertNotEqual(nano, xtts)
            nano.parent.mkdir(parents=True)
            nano.touch()
            self.assertFalse(runtime.engine_ready("nano"))
            runtime._marker("nano").write_text(json.dumps(runtime.ENGINES["nano"]))
            self.assertTrue(runtime.engine_ready("nano"))
            self.assertFalse(runtime.engine_ready("xtts"))
            runtime._marker("nano").write_text('{"old": true}')
            self.assertFalse(runtime.engine_ready("nano"))

    def test_nano_does_not_require_coqui_terms(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("heyclone.voice.library.data_dir", return_value=Path(tmp)):
            self.assertNotIn("COQUI_TOS_AGREED", runtime._environment("nano"))
            with self.assertRaisesRegex(RuntimeError, "Review the XTTS license"):
                runtime._environment("xtts")

    def test_unsupported_language_fails_before_starting_worker(self):
        with mock.patch.object(runtime, "_run") as run:
            with self.assertRaisesRegex(ValueError, "supports: en"):
                runtime.synthesize("ignored", "voice.wav", "Hello", "out.wav", "fr", False, engine="nano")
            run.assert_not_called()

    def test_worker_error_has_actionable_log(self):
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "engine.log"
            with self.assertRaisesRegex(RuntimeError, "Full log:"):
                runtime._run([sys.executable, "-c", "raise RuntimeError('engine broken')"], log=log)
            self.assertIn("engine broken", log.read_text())

    def test_install_does_not_mark_failed_model_ready(self):
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch("heyclone.voice.library.data_dir", return_value=Path(tmp)), \
             mock.patch.object(runtime.sys, "platform", "win32"), \
             mock.patch.object(runtime, "_run", side_effect=RuntimeError("download failed")):
            tools = Path(tmp) / "tools"
            tools.mkdir()
            (tools / "uv.exe").touch()
            with self.assertRaisesRegex(RuntimeError, "download failed"):
                runtime.install_runtime("nano")
            self.assertFalse(runtime.engine_ready("nano"))
