# Live Mic Streaming — Design Doc

## Problem
Voice input is batch-only: record → stop → upload → transcribe. No feedback while speaking.

## Approach: Chunked POST + Session Buffer
`MediaRecorder.start(500)` emits 500ms WebM chunks; each chunk POSTed to a new `/chat/voice/chunk` endpoint with a `stream_session_id`. Backend buffers in `AudioBuffer`, periodically sends to Groq for partial transcripts, streams them back.

## Frontend

### VoiceRecorderButton — new `streaming` prop
- `streaming: boolean` (default false) — enables chunked mode
- `onPartialTranscript?: (text: string) => void` — called with each partial result
- On record start: generate `stream_session_id` UUID, `MediaRecorder.start(500)`
- Each `ondataavailable`: POST multipart to `/chat/voice/chunk` with `stream_session_id`, `audio`, `final=false`
- On stop: POST with `final=true`, returns final transcript → calls `onTranscript`
- `disabled` while any in-flight chunk resolves (simple semaphore)

### Ask page — partial transcript display
- New state `partialTranscript: string`
- Pass `onPartialTranscript={setPartialTranscript}` to VoiceRecorderButton
- Show partial transcript below the mic button in a muted, italic style while recording

## Backend

### VoiceStreamSession (new file: `src/voice/streaming/session.py`)
```python
@dataclass
class VoiceStreamSession:
    stream_session_id: str
    buffer: AudioBuffer
    language: str
    last_partial: str = ""
    last_activity: datetime
```

### VoiceStreamManager (same file)
- Dict of `stream_session_id → VoiceStreamSession`
- `get_or_create(id, lang)` — create or return existing
- `remove(id)` — cleanup
- `clear_expired()` — TTL 300s
- Tracks chunk count per session

### `/chat/voice/chunk` endpoint (in `src/api/chat.py`)
```
POST /chat/voice/chunk
Form fields: audio (file), stream_session_id (str), final (bool),
             language, grade_level, topic, user_id
Auth: Bearer token
```
1. Lookup/create `VoiceStreamSession` by `stream_session_id`
2. Append audio bytes to `AudioBuffer`
3. Heuristic: transcribe every 2 chunks (or on `final=true`) using Groq
4. If partial differs from `last_partial`, include `partial_transcript` in response
5. On `final=true`: transcribe once more, return `final_transcript`, remove session
6. Return JSON: `{ partial_transcript?: string, final_transcript?: string }`

### Heuristic detail
- Track `_chunks_since_last_transcribe` per session
- Transcribe when ≥ 2 chunks accumulated OR `final=true`
- Compare result with `last_partial`; only emit on change (avoid duplicate UI updates)
- On `final=true`: flush all buffered audio regardless of chunk count

## Files Changed
- `dashboard/src/components/VoiceRecorderButton.tsx` — streaming mode
- `dashboard/src/app/(dashboard)/ask/page.tsx` — partial transcript display
- `src/api/chat.py` — add `/chat/voice/chunk` endpoint
- `src/voice/streaming/session.py` — NEW: `VoiceStreamSession` + `VoiceStreamManager`
- `src/voice/streaming/__init__.py` — export new classes
