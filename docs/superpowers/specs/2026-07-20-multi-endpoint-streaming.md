# Multi-Endpoint Streaming — Design Spec

**2026-07-20**

## 1. Goal

Extend LLM token streaming (SSE) from `/chat` to all agent-based endpoints: lesson plan, quiz/diagnostic, diagram, and teacher copilot. Users see tokens arrive incrementally instead of waiting for the full response.

## 2. Pattern

Each agent-based endpoint follows the same three-line pattern already proven in `/chat`:

```
agent accepts token_queue: asyncio.Queue[TokenChunk | None] = None
  └── calls router.route_stream() instead of route() when queue is set
  └── pushes TokenChunk{delta, status, done} to queue
API handler wraps queue in StreamingResponse via _stream_events()
```

No new abstraction layer — just plumbing `token_queue` through existing agent `generate()` methods. The `TokenChunk` schema, `_stream_events()` generator, SSE headers, and client format are all reusable as-is.

## 3. Endpoint Details

### 3.1 Lesson Plan (`POST /lesson-plan/generate`)

**Agent:** `LessonPlannerAgent.generate(grade_level, topic, ...)`

Currently returns a single JSON with explanation, activities, assessment, etc. To stream:
- `generate()` accepts `token_queue`
- Each section title becomes a `status: true` chunk: "Generating objective...", "Designing activities..."
- Section body text streams as `status: false` tokens
- The final accumulated string is still parsed into structured JSON for the response

### 3.2 Unit Plan (`POST /lesson-plan/unit/generate`)

Same as lesson plan, but loops over N lessons. Each lesson title is a status chunk.

### 3.3 Quiz (`POST /quiz/generate`)

Currently background-task + poll pattern. Add an optional `stream: bool = True` query param:
- When streaming: skip the background task; generate synchronously but stream each question as it completes
- Each question is one SSE event burst (question text + options as delta)
- No status chunks unless generation takes >5s per question

### 3.4 Diagnostic (`POST /quiz/diagnostic`)

Same pattern as quiz but per-topic.

### 3.5 Diagram (`POST /diagram/generate`)

**Agent:** `DiagramAgent.generate(topic, grade_level, ...)`

SVG output is large (20k+ chars). Stream SVG node by node — start tag, attributes, child elements. The `status` flag marks section boundaries (e.g., "Drawing cell membrane...", "Adding mitochondria...").

### 3.6 Teacher Copilot (`POST /copilot/query`)

Uses a separate LangGraph pipeline (`build_teacher_pipeline`). Needs `token_queue` wired through its graph nodes, similar to how `run_graph` passes it to `TutorNode`. Lower priority — complex graph retooling.

## 4. Streaming Changes Per Endpoint

| Endpoint | File | Agent | Change |
|----------|------|-------|--------|
| Lesson plan | `src/api/lesson.py` | `LessonPlannerAgent` in `src/agents/lesson_planner.py` | `generate()` accepts `token_queue`; calls `route_stream()` when set |
| Quiz | `src/api/quiz.py` | `QuizAgent` in `src/agents/quiz.py` | Same pattern — `token_queue` through `generate()` |
| Diagram | `src/api/diagram.py` | `DiagramAgent` in `src/agents/diagram.py` | Same pattern — `token_queue` through `generate()` |
| Copilot | `src/api/teacher_copilot.py` | Teacher pipeline in `src/agents/teacher_copilot_pipeline.py` | Wire `token_queue` through LangGraph pipeline nodes |

## 5. Backward Compatibility

- `stream` param defaults to `False` everywhere
- Non-streaming path is completely unchanged
- Quiz background-task polling continues to work alongside streaming

## 6. Implementation Order

1. Lesson plan — **[DONE]** `src/agents/lesson_planner.py`, `src/api/lesson.py`
2. Quiz + Diagnostic — **[DONE]** `src/agents/quiz.py`, `src/api/quiz.py`
3. Diagram SVG — **[DONE]** `src/agents/diagram.py`, `src/api/diagram.py`
4. Teacher Copilot — separate LangGraph pipeline, lower priority
