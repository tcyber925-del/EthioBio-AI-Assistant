# LLM Streaming Response — Design Spec

**2026-07-20**

## 1. Architecture

```
User (Web/Telegram)
  │
  └── POST /chat?stream=true
        │
        ▼
  handle_chat_request()
    ├── asyncio.create_task(run_graph(request, token_queue=q))
    │     │
    │     ├── orchestrator node (sync, no stream)
    │     ├── tutor node ──publishes──→ q: TokenChunk{delta, node, done}
    │     ├── claim_verifier node (sync, no stream)
    │     └── safety node (sync, no stream)
    │
    └── return StreamingResponse(stream_tokens(q), media_type="text/event-stream")
          │
          └── async generator reads q, yields SSE data: frames
```

## 2. TokenChunk Model

```python
@dataclass
class TokenChunk:
    delta: str              # text delta from LLM
    node: str = ""          # graph node name that produced this chunk
    done: bool = False      # stream complete
    error: str | None = None # error message if failed
    status: bool = False    # True = status/progress message, not answer content
```

## 3. Provider Streaming

### `LLMProvider` base (`src/llm/providers/base.py`)

```python
class LLMProvider(ABC):
    @abstractmethod
    async def chat_stream(self, messages: list[ChatMessage], **kwargs) -> AsyncGenerator[str, None]:
        ...
```

Each provider implements `chat_stream`:

| Provider | Implementation |
|----------|---------------|
| **Ollama** | `POST /api/chat` with `"stream": True`, iterate response lines parsing `message.content` |
| **OpenAI** | `client.chat.completions.create(stream=True)`, iterate `choice.delta.content` |
| **Anthropic** | `client.messages.create(stream=True)`, iterate `content_block_delta.text` |
| **OpenRouter** | Extends OpenAI, same pattern |

### Provider Chain (`src/llm/manager.py`)

- `ProviderManager.route_stream()` new method
- Tries primary provider's `chat_stream()`, falls back to next provider's `chat_stream()` on error
- Same retry/fallback semantics as `route()`

### ModelRouter (`src/llm/router.py`)

- `ModelRouter.route_stream()` new async method
- Returns `AsyncGenerator[TokenChunk, None]`
- Calls `ProviderManager.route_stream()`
- Accepts same arguments as `route()` plus optional `node_name: str`

## 4. Graph State

```python
class AgentState(TypedDict):
    ...
    token_queue: NotRequired[asyncio.Queue[TokenChunk | None]]
```

## 5. TutorNode Streaming

`TutorNode.__call__` checks `state.get("token_queue")`:

- **If present**: calls `ModelRouter.route_stream()` with `node_name="tutor"`, wraps result in `async for chunk`, pushes each chunk to `state["token_queue"]`, accumulates full text, returns normally
- **If absent**: existing non-streaming path unchanged

Streaming path:

```python
if "token_queue" in state and state["token_queue"]:
    full_content = ""
    queue = state["token_queue"]
    async for chunk in self.router.route_stream(messages, node_name="tutor"):
        queue.put_nowait(chunk)
        full_content += chunk.delta
    queue.put_nowait(None)  # sentinel
    # proceed with full_content as before (populate draft, confidence, etc.)
```

## 6. API /chat Endpoint

```python
@router.post("/chat")
async def handle_chat(request: TutorRequest):
    if not request.stream:
        return await _handle_chat_blocking(request)  # unchanged

    queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()
    task = asyncio.create_task(_run_graph_stream(request, queue))

    return StreamingResponse(
        _token_event_stream(queue, task),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

async def _token_event_stream(
    queue: asyncio.Queue[TokenChunk | None],
    task: asyncio.Task,
) -> AsyncGenerator[str, None]:
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        yield f"data: {chunk.model_dump_json()}\n\n"
        if chunk.done:
            while True:  # drain remaining
                c = await queue.get()
                if c is None:
                    break
                if c.error:
                    yield f"data: {c.model_dump_json()}\n\n"
            break

    # check for unhandled task exception
    if task.done() and (exc := task.exception()):
        yield f"data: {TokenChunk(delta='', done=True, error=str(exc)).model_dump_json()}\n\n"
```

## 7. SSE Event Format

```
data: {"delta":"Photosynthesis ","node":"tutor","done":false,"error":null}

data: {"delta":"is the process...","node":"tutor","done":false,"error":null}

data: {"delta":"","node":"tutor","done":true,"error":null}
```

## 8. Telegram Bot — Phase 2

The bot uses the same `token_queue` mechanism as the SSE endpoint:

1. Sends a "Thinking..." placeholder message
2. Passes `token_queue` to `run_graph()` as a background task
3. `_stream_and_edit()` reads chunks from the queue in 400ms intervals
4. Calls `edit_text()` on the thinking message with accumulated tokens
5. When the stream is done, final edit includes reply markup

Status messages (`status: true`) are filtered out — Telegram doesn't show
"Searching curriculum..." status; only the final answer tokens are displayed.

Key function in `src/telegram/bot.py`:

```python
STREAM_FLUSH_INTERVAL = 0.4

async def _stream_and_edit(
    msg,
    token_queue: asyncio.Queue[TokenChunk | None],
    graph_task: asyncio.Task,
    final_markup=None,
    parse_mode=None,
):
    """Read tokens from queue and progressively update the Telegram message."""
    buffer = ""
    last_edit = ""
    last_update = 0.0
    done = False

    while True:
        try:
            chunk = await asyncio.wait_for(token_queue.get(), timeout=STREAM_FLUSH_INTERVAL)
        except asyncio.TimeoutError:
            chunk = None

        now = asyncio.get_event_loop().time()

        if chunk is not None:
            if chunk.error:
                buffer += f"\n\n❌ {chunk.error}"
                done = True
            elif chunk.done:
                done = True
            elif not chunk.status:
                buffer += chunk.delta

        should_flush = done or (buffer != last_edit and now - last_update >= STREAM_FLUSH_INTERVAL)

        if should_flush and buffer and buffer != last_edit:
            try:
                display = sanitize_for_telegram(format_for_telegram(buffer))[:4096]
                await msg.edit_text(display, parse_mode=parse_mode)
            except Exception:
                pass
            last_edit = buffer
            last_update = now

        if done or (chunk is None and buffer != last_edit):
            break

    # Flush any remaining text
    try:
        display = sanitize_for_telegram(format_for_telegram(buffer))[:4096]
        await msg.edit_text(display, reply_markup=final_markup, parse_mode=parse_mode)
    except Exception:
        pass

    return buffer
```

Rate-limit considerations:
- Edit interval: 400ms (stays under Telegram's ~1 edit/sec per chat)
- Each edit replaces the full text (Telegram doesn't support partial updates)
- Max 4096 chars per `edit_text()` — handled by existing `_reply_long()` for overflow
- If `edit_text()` fails (rate limit, deleted message), the error is silently caught

## 9. Backward Compatibility

- `request.stream` defaults to `False`
- Non-streaming path is completely unchanged
- All existing clients work as before
- No changes to Telegram bot, quiz, diagram, or other endpoints

## 10. Implementation Order

### Phase 1 — SSE Streaming (complete)

1. `TokenChunk` dataclass in `src/schemas/streaming.py`
2. `chat_stream()` on `LLMProvider` base + all 4 providers
3. `route_stream()` on `ModelRouter` + `ProviderManager`
4. `token_queue` field in `AgentState`
5. Streaming path in `TutorNode`
6. SSE endpoint in `/chat`
7. Test with existing providers
8. Lint + typecheck

### Phase 2 — Time-to-first-token (complete)

9. Added `status: bool` field to `TokenChunk`
10. Immediate status push in `_handle_chat_stream` before graph task starts
11. Status pushes from `OrchestratorNode` during intent classification
12. Status pushes from `RetrievalNode` during search rounds
13. Status-aware client examples (JS + React)

### Phase 3 — Telegram Streaming (complete)

14. `_stream_and_edit()` helper in `src/telegram/bot.py`
15. 400ms flush interval with `edit_text()` on thinking message
16. Status chunks filtered out (Telegram shows only answer text)
17. Backward compatible: non-streaming path unchanged

## 11. Client Usage

### Curl

```bash
# Requires auth token (JWT)
curl -s -N -X POST https://api.ethiobio.ai/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "question": "What is photosynthesis?",
    "grade_level": 10,
    "stream": true,
    "user_id": "your-uuid-here"
  }'
```

### JavaScript (Browser — EventSource not suitable; use fetch with ReadableStream)

```javascript
async function streamChat(question, gradeLevel, token, userId) {
  const response = await fetch('/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      question,
      grade_level: gradeLevel,
      stream: true,
      user_id: userId,
    }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let statusEl = document.getElementById('status');
  let outputEl = document.getElementById('answer');
  let answerStarted = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const json = JSON.parse(line.slice(6));
      if (json.error) {
        console.error('Stream error:', json.error);
        return;
      }
      if (json.status) {
        // Status/progress message — show in status bar
        statusEl.textContent = json.delta;
      } else {
        // Actual answer token
        if (!answerStarted) {
          statusEl.textContent = '';
          answerStarted = true;
        }
        outputEl.textContent += json.delta;
      }
      if (json.done) {
        console.log('Stream complete');
        statusEl.textContent = 'Complete';
        return;
      }
    }
  }
}
```

### TypeScript (React hook)

```tsx
import { useState, useCallback } from 'react';

interface StreamChunk {
  delta: string;
  node: string;
  done: boolean;
  error: string | null;
  status: boolean;
}

export function useStreamChat() {
  const [text, setText] = useState('');
  const [status, setStatus] = useState('');
  const [streaming, setStreaming] = useState(false);
  const answerStartedRef = useRef(false);

  const send = useCallback(async (question: string, gradeLevel: number) => {
    setText('');
    setStatus('');
    setStreaming(true);
    answerStartedRef.current = false;

    const res = await fetch('/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Authorization header from your auth provider
      },
      body: JSON.stringify({ question, grade_level: gradeLevel, stream: true }),
    });

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const chunk: StreamChunk = JSON.parse(line.slice(6));
        if (chunk.error) { setStreaming(false); return; }
        if (chunk.status) {
          setStatus(chunk.delta);
        } else {
          if (!answerStartedRef.current) {
            setStatus('');
            answerStartedRef.current = true;
          }
          setText(prev => prev + chunk.delta);
        }
        if (chunk.done) { setStreaming(false); return; }
      }
    }
    setStreaming(false);
  }, []);

  return { text, status, streaming, send };
}
```

## 12. SSE Event Reference

Each SSE event is a single line: `data: <json>\n\n`

| Field | Type | Description |
|-------|------|-------------|
| `delta` | string | Text content (token or status message) |
| `node` | string | Graph node name that produced this chunk |
| `done` | boolean | Stream complete |
| `error` | string\|null | Error message (if failed) |
| `status` | boolean | True = status/progress, not answer content |

### Event types

**Status event** — appears at start while orchestrator/retrieval run:
```json
{"delta": "Searching the curriculum...", "node": "orchestrator", "done": false, "error": null, "status": true}
```

**Token event** — actual answer content from the LLM:
```json
{"delta": "Photosynthesis", "node": "tutor", "done": false, "error": null, "status": false}
```

**Done event** — stream complete, no more tokens:
```json
{"delta": "", "node": "tutor", "done": true, "error": null, "status": false}
```

**Error event** — something went wrong, stream aborted:
```json
{"delta": "", "node": "tutor", "done": false, "error": "Provider timeout", "status": false}
```
