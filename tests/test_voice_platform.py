import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.observability.voice_metrics import (
    STTTimer,
    TTSTimer,
    record_provider_error,
    record_recording_cleanup,
    record_recording_created,
    record_stt_request,
    record_tts_request,
)
from src.voice.audio import (
    MIME_TO_EXT,
    estimate_duration,
    format_name,
    guess_mime_from_bytes,
    read_ogg_page_duration,
    validate_audio_size,
)
from src.voice.session.manager import VoiceSession, VoiceSessionManager
from src.voice.streaming.buffer import AudioBuffer, AudioChunk
from src.voice.vad import VADDetector
from src.voice.vad.detector import VADState

OGG_HEADER = b"OggS"
RIFF_HEADER = b"RIFF"
MP3_ID3 = b"ID3xxx"
MP3_RAW = b"\xff\xfb\x90\x00"
FLAC_HEADER = b"fLaC"
M4A_HEADER = b"\x00\x00\x00\x18ftyp"


class TestGuessMimeFromBytes:
    def test_ogg(self):
        assert guess_mime_from_bytes(OGG_HEADER + b"\x00" * 10) == "audio/ogg"

    def test_wav(self):
        assert guess_mime_from_bytes(RIFF_HEADER + b"\x00" * 10) == "audio/wav"

    def test_flac(self):
        assert guess_mime_from_bytes(FLAC_HEADER + b"\x00" * 10) == "audio/flac"

    def test_mp3_id3(self):
        assert guess_mime_from_bytes(MP3_ID3) == "audio/mpeg"

    def test_mp3_raw(self):
        assert guess_mime_from_bytes(MP3_RAW) == "audio/mpeg"

    def test_m4a(self):
        assert guess_mime_from_bytes(M4A_HEADER) == "audio/m4a"

    def test_empty_bytes(self):
        assert guess_mime_from_bytes(b"") is None

    def test_too_short(self):
        assert guess_mime_from_bytes(b"\x00\x00") is None

    def test_unknown(self):
        assert guess_mime_from_bytes(b"\xde\xad\xbe\xef") is None


class TestFormatName:
    def test_known_mime(self):
        assert format_name("audio/ogg") == "Ogg Opus (Telegram voice)"

    def test_unknown_mime(self):
        assert format_name("audio/x-custom") == "audio/x-custom"


class TestMimeToExt:
    def test_known_mime(self):
        assert MIME_TO_EXT["audio/ogg"] == "ogg"
        assert MIME_TO_EXT["audio/mpeg"] == "mp3"

    def test_ext_to_mime(self):
        from src.voice.audio import EXT_TO_MIME

        assert EXT_TO_MIME["ogg"] == "audio/ogg"


class TestValidateAudioSize:
    def test_empty_audio(self):
        assert validate_audio_size(b"") is not None

    def test_acceptable_size(self):
        assert validate_audio_size(OGG_HEADER + b"\x00" * 100) is None

    def test_too_large(self):
        big = b"\x00" * 21_000_000
        err = validate_audio_size(big)
        assert err is not None
        assert "too large" in err

    def test_unrecognized_format(self):
        err = validate_audio_size(b"\x01\x02\x03\x04")
        assert err is not None
        assert "Could not detect" in err

    def test_custom_max_size(self):
        assert validate_audio_size(b"\x00" * 5000, max_size=1000) is not None
        assert validate_audio_size(OGG_HEADER + b"\x00" * 500, max_size=1000) is None


class TestEstimateDuration:
    def test_ogg_default(self):
        dur = estimate_duration(b"\x00" * 32000, "audio/ogg")
        assert isinstance(dur, float)
        assert dur > 0

    def test_mp3_kbps(self):
        dur = estimate_duration(b"\x00" * 16000, "audio/mpeg")
        assert dur == pytest.approx(1.0, rel=0.2)

    def test_wav_pcm(self):
        dur = estimate_duration(b"\x00" * 32000, "audio/wav")
        assert dur == pytest.approx(1.0, rel=0.1)

    def test_wav_too_short(self):
        assert estimate_duration(b"\x00" * 10, "audio/wav") == 0.0

    def test_fallback(self):
        dur = estimate_duration(b"\x00" * 16000, "audio/x-unknown")
        assert dur == pytest.approx(1.0, rel=0.2)


class TestReadOggPageDuration:
    def test_no_ogg_header(self):
        assert read_ogg_page_duration(b"\x00" * 100) == 0.0

    def test_empty(self):
        assert read_ogg_page_duration(b"") == 0.0

    def test_too_short(self):
        assert read_ogg_page_duration(b"OggS\x00") == 0.0

    def test_parse_first_page(self):
        data = bytearray(OGG_HEADER)
        data.extend([0, 0, 0, 0])  # version, header_type, granule
        data.extend(b"\x00" * 8)  # granule position
        data.extend(b"\x00" * 4)  # serial
        data.extend(b"\x00" * 4)  # page sequence
        data.extend(b"\x00" * 4)  # checksum
        data.append(0)  # page segments
        dur = read_ogg_page_duration(bytes(data))
        assert dur == 0.0


class TestVoiceSessionManager:
    def test_get_or_create_new(self):
        mgr = VoiceSessionManager(ttl_seconds=600)
        session = mgr.get_or_create("user:1")
        assert isinstance(session, VoiceSession)
        assert mgr.active_count == 1

    def test_get_or_create_existing(self):
        mgr = VoiceSessionManager(ttl_seconds=600)
        s1 = mgr.get_or_create("user:1")
        s2 = mgr.get_or_create("user:1")
        assert s1 is s2
        assert mgr.active_count == 1

    def test_get_or_create_multiple_keys(self):
        mgr = VoiceSessionManager(ttl_seconds=600)
        s1 = mgr.get_or_create("user:1")
        s2 = mgr.get_or_create("user:2")
        assert s1 is not s2
        assert mgr.active_count == 2

    def test_get_existing(self):
        mgr = VoiceSessionManager(ttl_seconds=600)
        mgr.get_or_create("user:1")
        assert mgr.get("user:1") is not None

    def test_get_nonexistent(self):
        mgr = VoiceSessionManager(ttl_seconds=600)
        assert mgr.get("user:none") is None

    def test_touch(self):
        mgr = VoiceSessionManager(ttl_seconds=600)
        mgr.get_or_create("user:1")
        assert mgr.get("user:1").turn_count == 0
        mgr.touch("user:1")
        assert mgr.get("user:1").turn_count == 1

    def test_touch_nonexistent_no_error(self):
        mgr = VoiceSessionManager(ttl_seconds=600)
        mgr.touch("missing")  # should not raise

    def test_remove(self):
        mgr = VoiceSessionManager(ttl_seconds=600)
        mgr.get_or_create("user:1")
        mgr.remove("user:1")
        assert mgr.get("user:1") is None
        assert mgr.active_count == 0

    def test_remove_nonexistent(self):
        mgr = VoiceSessionManager(ttl_seconds=600)
        mgr.remove("missing")  # should not raise

    def test_clear_expired(self):
        mgr = VoiceSessionManager(ttl_seconds=0)
        mgr.get_or_create("user:1")
        time.sleep(0.01)
        cleared = mgr.clear_expired()
        assert cleared == 1
        assert mgr.active_count == 0

    def test_clear_expired_no_op(self):
        mgr = VoiceSessionManager(ttl_seconds=600)
        mgr.get_or_create("user:1")
        assert mgr.clear_expired() == 0
        assert mgr.active_count == 1

    def test_session_ttl_expiry(self):
        mgr = VoiceSessionManager(ttl_seconds=0)
        s1 = mgr.get_or_create("user:1")
        time.sleep(0.01)
        s2 = mgr.get_or_create("user:1")
        assert s1 is not s2

    def test_user_id_on_create(self):
        mgr = VoiceSessionManager()
        session = mgr.get_or_create("user:42", user_id=42)
        assert session.user_id == 42

    def test_session_has_uuid(self):
        mgr = VoiceSessionManager()
        session = mgr.get_or_create("test")
        assert session.session_id is not None
        assert len(str(session.session_id)) > 0

    def test_topic_and_metadata(self):
        session = VoiceSession(topic="DNA", source_language="am")
        assert session.topic == "DNA"
        assert session.source_language == "am"


class TestAudioBuffer:
    def test_append_and_assemble(self):
        buf = AudioBuffer()
        buf.append(AudioChunk(data=b"hello", sequence=0))
        buf.append(AudioChunk(data=b" world", sequence=1))
        assert buf.assemble() == b"hello world"
        assert buf.chunk_count == 2

    def test_total_bytes(self):
        buf = AudioBuffer()
        buf.append(AudioChunk(data=b"\x00" * 100, sequence=0))
        buf.append(AudioChunk(data=b"\x00" * 200, sequence=1))
        assert buf.total_bytes == 300

    def test_closed_rejects(self):
        buf = AudioBuffer()
        buf.append(AudioChunk(data=b"final", sequence=0, is_final=True))
        with pytest.raises(ValueError, match="Buffer is closed"):
            buf.append(AudioChunk(data=b"extra", sequence=1))

    def test_complete_on_final(self):
        buf = AudioBuffer()
        assert not buf.complete
        buf.append(AudioChunk(data=b"x", sequence=0, is_final=True))
        assert buf.complete

    def test_clear(self):
        buf = AudioBuffer()
        buf.append(AudioChunk(data=b"x", sequence=0))
        buf.clear()
        assert buf.chunk_count == 0
        assert buf.total_bytes == 0
        buf.append(AudioChunk(data=b"y", sequence=0))
        assert buf.assemble() == b"y"

    def test_max_chunks_eviction(self):
        buf = AudioBuffer(max_chunks=2)
        buf.append(AudioChunk(data=b"a", sequence=0))
        buf.append(AudioChunk(data=b"b", sequence=1))
        buf.append(AudioChunk(data=b"c", sequence=2))
        assert buf.chunk_count == 2
        assert buf.assemble() == b"bc"

    def test_empty_assemble(self):
        assert AudioBuffer().assemble() == b""

    def test_last_mime_type(self):
        buf = AudioBuffer()
        assert buf.last_mime_type() is None
        buf.append(AudioChunk(data=b"x", sequence=0, mime_type="audio/ogg"))
        assert buf.last_mime_type() == "audio/ogg"

    def test_initial_duration_zero(self):
        assert AudioBuffer().duration_seconds == 0.0


class TestAudioChunk:
    def test_defaults(self):
        c = AudioChunk(data=b"test", sequence=0)
        assert c.data == b"test"
        assert c.sequence == 0
        assert c.is_final is False
        assert c.mime_type is None
        assert isinstance(c.timestamp, datetime)

    def test_final_flag(self):
        c = AudioChunk(data=b"done", sequence=5, is_final=True)
        assert c.is_final


class TestVADDetector:
    def test_initial_state(self):
        vad = VADDetector()
        assert vad.state == VADState.SILENCE

    def test_silence_frame(self):
        vad = VADDetector(threshold=0.1)
        # silence = all zeros
        pcm = b"\x00\x00" * (vad.frame_size)
        state = vad.process_frame(pcm)
        assert state == VADState.SILENCE

    def test_speech_frame(self):
        vad = VADDetector(threshold=0.001, min_speech_frames=1)
        # high amplitude samples
        pcm = b"\xff\x7f" * (vad.frame_size)
        state = vad.process_frame(pcm)
        assert state == VADState.SPEAKING

    def test_speech_to_silence_transition(self):
        vad = VADDetector(threshold=0.001, min_speech_frames=1, min_silence_frames=1)
        # speech frame
        vad.process_frame(b"\xff\x7f" * vad.frame_size)
        assert vad.state == VADState.SPEAKING
        # silence frame
        vad.process_frame(b"\x00\x00" * vad.frame_size)
        assert vad.state == VADState.SILENCE

    def test_min_speech_frames(self):
        vad = VADDetector(threshold=0.001, min_speech_frames=3)
        # just 2 speech frames — should stay SILENCE
        vad.process_frame(b"\xff\x7f" * vad.frame_size)
        assert vad.state == VADState.SILENCE
        vad.process_frame(b"\xff\x7f" * vad.frame_size)
        assert vad.state == VADState.SILENCE
        # third frame crosses threshold
        vad.process_frame(b"\xff\x7f" * vad.frame_size)
        assert vad.state == VADState.SPEAKING

    def test_min_silence_frames(self):
        vad = VADDetector(threshold=0.001, min_speech_frames=1, min_silence_frames=2)
        vad.process_frame(b"\xff\x7f" * vad.frame_size)
        assert vad.state == VADState.SPEAKING
        vad.process_frame(b"\x00\x00" * vad.frame_size)
        assert vad.state == VADState.SPEAKING  # not enough silence frames yet
        vad.process_frame(b"\x00\x00" * vad.frame_size)
        assert vad.state == VADState.SILENCE

    def test_reset(self):
        vad = VADDetector(threshold=0.001, min_speech_frames=1)
        vad.process_frame(b"\xff\x7f" * vad.frame_size)
        assert vad.state == VADState.SPEAKING
        vad.reset()
        assert vad.state == VADState.SILENCE

    def test_process_empty_frame(self):
        vad = VADDetector()
        state = vad.process_frame(b"")
        assert state == VADState.SILENCE

    def test_process_short_frame(self):
        vad = VADDetector()
        state = vad.process_frame(b"\x00")
        assert state == VADState.SILENCE

    def test_rms_calculation(self):
        vad = VADDetector(threshold=0.001, min_speech_frames=1)
        # constant moderate amplitude
        pcm = b"\x10\x00" * vad.frame_size
        state = vad.process_frame(pcm)
        assert state == VADState.SPEAKING


class TestVoiceMetrics:
    @patch("src.observability.voice_metrics._r")
    def test_record_stt_request(self, mock_r):
        mock_counter = MagicMock()
        mock_r.return_value.counter.return_value = mock_counter
        record_stt_request("groq", "am", "ok")
        mock_r.return_value.counter.assert_called_once_with("voice.stt.requests")
        mock_counter.inc.assert_called_once_with(
            {"provider": "groq", "language": "am", "status": "ok"}
        )

    @patch("src.observability.voice_metrics._r")
    def test_record_tts_request(self, mock_r):
        mock_counter = MagicMock()
        mock_r.return_value.counter.return_value = mock_counter
        record_tts_request("edge-tts", "ok")
        mock_counter.inc.assert_called_once_with({"provider": "edge-tts", "status": "ok"})

    @patch("src.observability.voice_metrics._r")
    def test_record_recording_created(self, mock_r):
        mock_counter = MagicMock()
        mock_r.return_value.counter.return_value = mock_counter
        record_recording_created("user", "voice")
        mock_counter.inc.assert_called_once_with({"direction": "user", "modality": "voice"})

    @patch("src.observability.voice_metrics._r")
    def test_record_recording_cleanup(self, mock_r):
        mock_counter = MagicMock()
        mock_r.return_value.counter.return_value = mock_counter
        record_recording_cleanup(5)
        mock_counter.inc.assert_called_once_with({"count": "5"})

    @patch("src.observability.voice_metrics._r")
    def test_record_provider_error(self, mock_r):
        mock_counter = MagicMock()
        mock_r.return_value.counter.return_value = mock_counter
        record_provider_error("groq", "stt")
        mock_counter.inc.assert_called_once_with({"provider": "groq", "operation": "stt"})

    @patch("src.observability.voice_metrics.record_stt_duration")
    def test_stt_timer(self, mock_record):
        with STTTimer("groq"):
            time.sleep(0.01)
        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        assert args[1] == "groq"
        assert args[0] > 0

    @patch("src.observability.voice_metrics.record_tts_duration")
    def test_tts_timer(self, mock_record):
        with TTSTimer("edge-tts"):
            time.sleep(0.01)
        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        assert args[1] == "edge-tts"
        assert args[0] > 0


class TestWebVoiceAdapterUserId:
    def test_user_id_normalized_to_string(self):
        from uuid import UUID

        from src.schemas.chat import TutorRequest
        from src.voice.gateways.web import WebVoiceAdapter

        uid = UUID("00000000-0000-0000-0000-000000000001")
        request = TutorRequest(user_id=uid, question="What is a cell?")
        conv = WebVoiceAdapter().build_request(request)
        assert conv.user_id == "00000000-0000-0000-0000-000000000001"
        assert conv.metadata["user_id"] == "00000000-0000-0000-0000-000000000001"
        assert isinstance(conv.user_id, str)

    def test_user_id_string_passthrough(self):
        from src.schemas.chat import TutorRequest
        from src.voice.gateways.web import WebVoiceAdapter

        request = TutorRequest(
            user_id="00000000-0000-0000-0000-000000000001", question="What is a cell?"
        )
        conv = WebVoiceAdapter().build_request(request)
        assert conv.user_id == "00000000-0000-0000-0000-000000000001"

    def test_user_id_none_becomes_empty(self):
        from src.schemas.chat import TutorRequest
        from src.voice.gateways.web import WebVoiceAdapter

        conv = WebVoiceAdapter().build_request(TutorRequest(question="What is a cell?"))
        assert conv.user_id == ""
