import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class AudioChunk:
    data: bytes
    sequence: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_final: bool = False
    mime_type: Optional[str] = None


class AudioBuffer:
    def __init__(self, max_chunks: int = 200, max_duration_seconds: float = 60.0):
        self._chunks: list[AudioChunk] = []
        self._max_chunks = max_chunks
        self._max_duration = max_duration_seconds
        self._closed = False

    def append(self, chunk: AudioChunk) -> None:
        if self._closed:
            raise ValueError("Buffer is closed")
        if chunk.is_final:
            self._closed = True
        if len(self._chunks) >= self._max_chunks:
            self._chunks.pop(0)
        self._chunks.append(chunk)

    @property
    def complete(self) -> bool:
        return self._closed or self.duration_seconds >= self._max_duration

    @property
    def total_bytes(self) -> int:
        return sum(len(c.data) for c in self._chunks)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    @property
    def duration_seconds(self) -> float:
        if not self._chunks:
            return 0.0
        first = self._chunks[0].timestamp
        latest = self._chunks[-1].timestamp
        return (latest - first).total_seconds()

    def assemble(self) -> bytes:
        buf = io.BytesIO()
        for c in self._chunks:
            buf.write(c.data)
        return buf.getvalue()

    def clear(self) -> None:
        self._chunks.clear()
        self._closed = False

    def last_mime_type(self) -> Optional[str]:
        if not self._chunks:
            return None
        return self._chunks[-1].mime_type
