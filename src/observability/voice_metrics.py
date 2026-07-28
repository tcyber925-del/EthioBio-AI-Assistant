import time

from .metrics import _r

STT_REQUESTS = "voice.stt.requests"
STT_DURATION = "voice.stt.duration_ms"
TTS_REQUESTS = "voice.tts.requests"
TTS_DURATION = "voice.tts.duration_ms"
RECORDINGS_CREATED = "voice.recordings.created"
RECORDINGS_CLEANED = "voice.recordings.cleaned"
PROVIDER_ERRORS = "voice.provider.errors"


def record_stt_request(provider: str, language: str, status: str) -> None:
    _r().counter(STT_REQUESTS).inc({"provider": provider, "language": language, "status": status})


def record_stt_duration(duration_ms: float, provider: str) -> None:
    _r().histogram(STT_DURATION).observe(duration_ms, {"provider": provider})


def record_tts_request(provider: str, status: str) -> None:
    _r().counter(TTS_REQUESTS).inc({"provider": provider, "status": status})


def record_tts_duration(duration_ms: float, provider: str) -> None:
    _r().histogram(TTS_DURATION).observe(duration_ms, {"provider": provider})


def record_recording_created(direction: str = "user", modality: str = "voice") -> None:
    _r().counter(RECORDINGS_CREATED).inc({"direction": direction, "modality": modality})


def record_recording_cleanup(count: int) -> None:
    _r().counter(RECORDINGS_CLEANED).inc({"count": str(count)})


def record_provider_error(provider: str, operation: str) -> None:
    _r().counter(PROVIDER_ERRORS).inc({"provider": provider, "operation": operation})


class STTTimer:
    def __init__(self, provider: str):
        self.provider = provider
        self.start: float = 0.0

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        duration_ms = (time.monotonic() - self.start) * 1000
        record_stt_duration(duration_ms, self.provider)


class TTSTimer:
    def __init__(self, provider: str):
        self.provider = provider
        self.start: float = 0.0

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        duration_ms = (time.monotonic() - self.start) * 1000
        record_tts_duration(duration_ms, self.provider)
