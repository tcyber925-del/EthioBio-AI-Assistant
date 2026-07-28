import struct
from typing import Optional

AUDIO_FORMATS: dict[str, str] = {
    "ogg": "Ogg Opus (Telegram voice)",
    "mp3": "MPEG Layer III",
    "wav": "RIFF WAV PCM",
    "m4a": "AAC / MPEG-4",
    "webm": "WebM (Opus)",
    "amr": "AMR Narrowband",
    "aac": "Advanced Audio Coding",
    "flac": "FLAC (Free Lossless)",
}

MIME_TO_EXT: dict[str, str] = {
    "audio/ogg": "ogg",
    "audio/mp3": "mp3",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/webm": "webm",
    "audio/amr": "amr",
    "audio/aac": "aac",
    "audio/flac": "flac",
}

EXT_TO_MIME: dict[str, str] = {v: k for k, v in MIME_TO_EXT.items()}

OGG_HEADER = b"OggS"
RIFF_HEADER = b"RIFF"
FLAC_HEADER = b"fLaC"


def guess_mime_from_bytes(data: bytes) -> Optional[str]:
    if len(data) < 4:
        return None
    if data[:4] == OGG_HEADER:
        return "audio/ogg"
    if data[:4] == RIFF_HEADER:
        return "audio/wav"
    if data[:4] == FLAC_HEADER:
        return "audio/flac"
    if data[:3] == b"ID3" or (data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "audio/mpeg"
    if data[4:8] == b"ftyp":
        return "audio/m4a"
    if data[:4] == b"\x00\x00\x00\x18" and data[8:12] == b"wide":
        return "audio/amr"
    return None


def format_name(mime_type: str) -> str:
    ext = MIME_TO_EXT.get(mime_type, "")
    return AUDIO_FORMATS.get(ext, mime_type)


def estimate_duration(audio_bytes: bytes, mime_type: str = "audio/ogg") -> float:
    size = len(audio_bytes)
    if mime_type == "audio/ogg":
        return size / (16 * 1024)
    if mime_type in ("audio/mpeg", "audio/mp3"):
        kb = size / 1024
        return kb / 16
    if mime_type == "audio/wav":
        if size < 44:
            return 0.0
            # 16-bit mono 16kHz PCM = 32000 bytes/sec
        return size / 32000
    return size / (16 * 1024)


def validate_audio_size(
    audio_bytes: bytes,
    max_size: int = 20_971_520,
) -> Optional[str]:
    if len(audio_bytes) == 0:
        return "Audio is empty"
    if len(audio_bytes) > max_size:
        return f"Audio too large: {len(audio_bytes)} bytes (max {max_size})"
    mime = guess_mime_from_bytes(audio_bytes)
    if mime is None:
        return "Could not detect audio format"
    return None


def read_ogg_page_duration(data: bytes) -> float:
    """Parse OGG Opus headers to estimate duration.

    Only reads the first few pages — heuristic, not exact.
    """
    if len(data) < 4 or data[:4] != OGG_HEADER:
        return 0.0

    if len(data) < 100:
        return 0.0
    try:
        pos = 0
        total_samples = 0
        page_count = 0
        while pos + 27 <= len(data) and page_count < 20:
            if data[pos:pos+4] != OGG_HEADER:
                break
            _version = data[pos+4]
            _header_type = data[pos+5]
            _granule = struct.unpack("<Q", data[pos+6:pos+14])[0]
            _serial = struct.unpack("<I", data[pos+14:pos+18])[0]
            _page_seq = struct.unpack("<I", data[pos+18:pos+22])[0]
            _checksum = data[pos+22:pos+26]
            _page_segments = data[pos+26]
            seg_table = data[pos+27:pos+27+_page_segments]
            segment_size = sum(seg_table)
            if _page_seq == 0:
                total_samples = 0
            else:
                total_samples = _granule
            pos += 27 + _page_segments + segment_size
            page_count += 1
        return total_samples / 48000.0 if total_samples else 0.0
    except (struct.error, IndexError, ValueError):
        return 0.0
