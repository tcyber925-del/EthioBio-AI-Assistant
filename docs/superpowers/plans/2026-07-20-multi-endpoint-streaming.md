# Multi-Endpoint Streaming — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SSE token streaming to lesson-plan, quiz, diagram, and teacher-copilot endpoints

**Architecture:** Each agent's `generate()` method accepts an optional `token_queue`. When set, it calls `router.route_stream()` instead of `route()` and pushes `TokenChunk` objects to the queue. The API handler wraps the queue in a `StreamingResponse` via the existing `_stream_events()` helper. No new abstractions.

**Tech Stack:** Python 3.12+, FastAPI, SSE (text/event-stream), TokenChunk schema

---

### Task 1: Lesson plan streaming

**Files:**
- Modify: `src/agents/lesson_planner.py` — add `token_queue` param to `generate()`
- Modify: `src/api/lesson.py` — add SSE path for streaming
- Test: `tests/test_streaming.py` — add lesson plan streaming tests

- [ ] **Step 1: Read current lesson planner agent**

```
Read src/agents/lesson_planner.py to understand generate() signature and how it calls router.route()
```

- [ ] **Step 2: Read current lesson API endpoint**

```
Read src/api/lesson.py to understand the endpoint handler
```

- [ ] **Step 3: Add streaming path to LessonPlannerAgent.generate()**

```python
async def generate(
    self,
    grade_level: int,
    topic: str,
    language: str = "en",
    token_queue: asyncio.Queue[TokenChunk | None] | None = None,
) -> dict[str, Any]:
```

Inside the method, when `token_queue` is set, replace `await self.router.route(...)` with streaming:
- Push status chunks before each section: "Generating lesson objective...", "Designing activities..."
- Stream the LLM response via `self.router.route_stream(...)`
- Accumulate the full text in a buffer
- Parse the final buffer into JSON (same as current code)

- [ ] **Step 4: Add SSE endpoint to lesson API**

In `src/api/lesson.py`, add a parallel handler:
```python
async def _handle_lesson_plan_stream(
    request: LessonPlanRequest,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()
    agent = LessonPlannerAgent()
    task = asyncio.create_task(
        agent.generate(
            grade_level=request.grade_level,
            topic=request.topic,
            language=_resolve_language(current_user),
            token_queue=queue,
        )
    )
    return StreamingResponse(
        _stream_events(queue, task),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
```

Add `stream: bool = False` to `LessonPlanRequest`. Route to streaming handler when `stream=True`.

- [ ] **Step 5: Add tests**

```python
async def test_lesson_plan_streaming():
    agent = LessonPlannerAgent()
    queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()
    task = asyncio.create_task(
        agent.generate(grade_level=10, topic="Cell division", token_queue=queue)
    )
    chunks = []
    while True:
        chunk = await queue.get()
        if chunk is None:
            break
        chunks.append(chunk)
        if chunk.done:
            break
    await task
    assert len(chunks) >= 2
    assert any(c.status for c in chunks)
    deltas = [c.delta for c in chunks if not c.status and not c.done]
    assert len("".join(deltas)) > 0
```

- [ ] **Step 6: Run lint + typecheck**

```
ruff check src/agents/lesson_planner.py src/api/lesson.py
mypy src/agents/lesson_planner.py src/api/lesson.py
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: stream lesson plan generation via SSE"
```

---

### Task 2: Quiz + Diagnostic streaming **[DONE]**

- [x] **Step 1: Read QuizAgent.generate()**
- [x] **Step 2: Add token_queue to QuizAgent.generate() & DiagnosticAgent.generate()**
- [x] **Step 3: Add SSE endpoint to /quiz/generate + /quiz/diagnostic**
- [x] **Step 4: Run lint + typecheck**
- [x] **Step 5: Commit**

---

**Files:**
- Modify: `src/agents/quiz.py` — add `token_queue` param to `generate()`
- Modify: `src/api/quiz.py` — add SSE path
- Test: `tests/test_streaming.py`

- [ ] **Step 1: Read QuizAgent.generate()**

- [ ] **Step 2: Add token_queue to QuizAgent.generate()**

Same pattern as lesson plan: accept `token_queue`, use `route_stream()` when set, push `TokenChunk{delta, node="quiz", done}` per question.

- [ ] **Step 3: Add SSE endpoint to /quiz/generate**

When `stream=True`, bypass the background task pattern and stream questions inline. Each question burst is: question text streamed, then options, then a `done: false` sentinel before the next question.

- [ ] **Step 4: Apply same pattern to /quiz/diagnostic**

- [ ] **Step 5: Run lint + typecheck**

- [ ] **Step 6: Commit**

---

### Task 3: Diagram SVG streaming **[DONE]**

- [x] **Step 1: Read DiagramAgent.generate()**
- [x] **Step 2: Add token_queue to DiagramAgent.generate()**
- [x] **Step 3: Add SSE endpoint to /diagram/generate**
- [x] **Step 4: Run lint + typecheck**
- [x] **Step 5: Commit**

---

**Files:**
- Modify: `src/agents/diagram.py` — add `token_queue` param
- Modify: `src/api/diagram.py` — add SSE path
- Test: `tests/test_streaming.py`

- [ ] **Step 1: Read DiagramAgent.generate()**

- [ ] **Step 2: Add token_queue to DiagramAgent.generate()**

Push status chunks for each diagram section ("Drawing cell membrane...", "Adding mitochondria..."). Stream SVG text as delta tokens.

- [ ] **Step 3: Add SSE endpoint to /diagram/generate**

Same pattern: `stream: bool` query param → `StreamingResponse`.

- [ ] **Step 4: Run lint + typecheck**

- [ ] **Step 5: Commit**

---

### Task 4: Teacher Copilot streaming (lower priority)

**Files:**
- Modify: `src/agents/teacher_copilot_pipeline.py`
- Modify: `src/api/teacher_copilot.py`
- Test: `tests/`

- [ ] **Step 1: Read teacher copilot pipeline**

- [ ] **Step 2: Wire token_queue through LangGraph pipeline**

- [ ] **Step 3: Add SSE endpoint**

- [ ] **Step 4: Run lint + typecheck**

- [ ] **Step 5: Commit**
