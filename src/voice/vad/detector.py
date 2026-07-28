import enum
import struct


class VADState(enum.Enum):
    SILENCE = "silence"
    SPEAKING = "speaking"
    PROCESSING = "processing"


class VADDetector:
    """Lightweight energy-based Voice Activity Detection.

    Uses RMS energy threshold — no external dependencies.
    Replace with WebRTC VAD or Silero VAD for production accuracy.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_ms: int = 30,
        threshold: float = 0.02,
        min_speech_frames: int = 3,
        min_silence_frames: int = 10,
    ):
        self.sample_rate = sample_rate
        self.frame_size = sample_rate * frame_ms // 1000
        self.threshold = threshold
        self.min_speech_frames = min_speech_frames
        self.min_silence_frames = min_silence_frames
        self._state = VADState.SILENCE
        self._speech_frames = 0
        self._silence_frames = 0

    @property
    def state(self) -> VADState:
        return self._state

    def process_frame(self, pcm_data: bytes) -> VADState:
        if len(pcm_data) < 2:
            return self._state
        count = len(pcm_data) // 2
        fmt = f"<{count}h"
        try:
            samples = struct.unpack(fmt, pcm_data[:count * 2])
        except struct.error:
            return self._state
        if not samples:
            return self._state
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        is_speech = rms > self.threshold
        if is_speech:
            self._speech_frames += 1
            self._silence_frames = 0
        else:
            self._silence_frames += 1
            self._speech_frames = 0
        if self._speech_frames >= self.min_speech_frames:
            self._state = VADState.SPEAKING
        elif self._silence_frames >= self.min_silence_frames:
            self._state = VADState.SILENCE
        return self._state

    def reset(self) -> None:
        self._state = VADState.SILENCE
        self._speech_frames = 0
        self._silence_frames = 0
