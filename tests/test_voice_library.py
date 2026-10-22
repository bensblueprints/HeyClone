import tempfile
import unittest
from pathlib import Path
from unittest import mock
import wave

import numpy as np
import soundfile as sf

from heyclone.voice.library import VoiceLibrary
from heyclone.voice.recording import VoiceRecorder


class TestVoiceLibrary(unittest.TestCase):
    def test_upload_survives_source_removal_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "upload.wav"
            sf.write(source, np.sin(np.arange(16000 * 4) * 0.1) * 0.1, 16000)
            library = VoiceLibrary(root / "library")
            first = library.add("My voice", source)
            second = library.add("My voice", source)
            source.unlink()
            voices = VoiceLibrary(library.root).voices()
            self.assertEqual(len(voices), 2)
            self.assertNotEqual(first.id, second.id)
            self.assertTrue(all(v.reference.is_file() for v in voices))
            self.assertNotEqual(library.output_path(), library.output_path())

    def test_invalid_uploads_do_not_create_voices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = VoiceLibrary(root / "library")
            source = root / "silent.wav"
            sf.write(source, np.zeros(16000 * 4), 16000)
            with self.assertRaisesRegex(ValueError, "silent"):
                library.add("Silent", source)
            source.write_bytes(b"invalid audio")
            with self.assertRaises(ValueError):
                library.add("Invalid", source)
            self.assertEqual(library.voices(), [])

    def test_short_recording_closes_stream_without_saving(self):
        recorder = VoiceRecorder()
        stream = mock.Mock()
        recorder.stream = stream
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clip.wav"
            with self.assertRaisesRegex(ValueError, "at least 3 seconds"):
                recorder.save(path)
            self.assertFalse(path.exists())
        stream.stop.assert_called_once()
        stream.close.assert_called_once()

    def test_recorded_pcm_is_saved_as_valid_wav(self):
        recorder = VoiceRecorder()
        recorder.frames = recorder.sample_rate * 4
        recorder.chunks = [b"\x01\x00" * recorder.frames]
        with tempfile.TemporaryDirectory() as tmp:
            path = recorder.save(Path(tmp) / "clip.wav")
            with wave.open(str(path)) as audio:
                self.assertEqual(audio.getnframes(), recorder.frames)
                self.assertEqual(audio.getnchannels(), 1)
