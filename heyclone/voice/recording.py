"""Bounded microphone capture with explicit start/stop and resource cleanup."""

import wave


class VoiceRecorder:
    def __init__(self):
        self.stream = None
        self.chunks = []
        self.frames = 0
        self.error = None
        self.sample_rate = 44100

    @property
    def seconds(self):
        return self.frames / self.sample_rate

    def start(self):
        import sounddevice as sd

        self.sample_rate = int(sd.query_devices(kind="input")["default_samplerate"])
        self.chunks = []
        self.frames = 0
        self.error = None

        def callback(data, frames, time_info, status):
            if status:
                self.error = str(status)
            remaining = max(0, self.sample_rate * 30 - self.frames)
            take = min(remaining, frames)
            if take:
                self.chunks.append(bytes(data)[:take * 2])
                self.frames += take

        self.stream = sd.RawInputStream(samplerate=self.sample_rate, channels=1, dtype="int16", callback=callback)
        try:
            self.stream.start()
        except Exception:
            self.close()
            raise

    def close(self):
        stream, self.stream = self.stream, None
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()

    def save(self, path):
        self.close()
        if self.error:
            raise ValueError(f"Microphone recording was interrupted ({self.error}). Please try again.")
        if self.seconds < 3:
            raise ValueError("Record at least 3 seconds of speech; 6-15 seconds is recommended.")
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(self.sample_rate)
            audio.writeframes(b"".join(self.chunks))
        self.chunks = []
        return path
