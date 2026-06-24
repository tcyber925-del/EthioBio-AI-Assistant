# Assessment Studio — Diagnostic Assessment and Exit Tickets

The Assessment Studio (Wave 4) extends the existing quiz generation system with two new structured assessment types: multi-topic diagnostic pre-tests and lesson-level exit tickets. The Teacher Copilot pipeline was also wired to route `assessment_creation` intent directly to `QuizAgent`.

**Status:** accepted

## Context

The existing quiz infrastructure (`QuizAgent`, `POST /quiz/generate`) generates single-topic quizzes on demand. Two gaps remained:

1. **Diagnostic assessment**: No way to generate a multi-topic baseline pre-test that establishes a student's starting knowledge across several topics in a single request.
2. **Exit tickets**: The lesson planner's `assessment` field was a free-text string (e.g., "Ask students to explain photosynthesis"). No structured, gradable exit ticket existed.
3. **Teacher Copilot integration**: The `assessment_creation` intent was classified but not acted on — the pipeline returned reasoning but never generated an actual assessment.

## Decision

Three additions to the assessment system:

1. **Diagnostic Agent** (`src/agents/diagnostic_assessment.py`, `src/api/diagnostic.py`): A new `DiagnosticAgent` that generates one `Quiz` per topic in a single LLM call, all at EASY difficulty, creating a baseline snapshot. The `POST /quiz/diagnostic` endpoint accepts `user_id`, `grade_level`, `topics[]`, `questions_per_topic`, and returns a `DiagnosticResponse` with per-topic baselines and overall severity.

2. **Exit Ticket integration** (`src/agents/lesson_planner.py`, `src/api/lesson.py`): A `generate_exit_ticket: bool` parameter added to `POST /lesson-plan/generate`. When true, a separate LLM call generates 3 structured questions (MC/TF/short_answer) after the lesson plan, returned as `ExitTicketQuestion[]` in the response.

3. **Teacher Copilot assessment route** (`src/core/teacher_copilot/pipeline.py`): A conditional edge `route_after_classify()` routes `assessment_creation` intent to a new `AssessmentCreatorNode` that extracts grade/topic from natural language and calls `QuizAgent.generate()`. The generated assessment is returned in the response text.

## Consequences

- Diagnostics and quizzes share the same `Quiz`/`Question` tables — no new storage needed.
- Exit tickets are computed on-the-fly and not persisted (re-generated when needed). This avoids schema changes to the `LessonPlan` model.
- Teacher Copilot now produces actual assessments instead of just reasoning about them.
- The diagnostic's `effectiveness_score` and `overall_severity` are placeholders (0.0 / "pending") until the student submits answers via `POST /quiz/submit`.
- Multi-topic diagnostics can be expensive (one LLM call for all topics at once), but fine-tuning on the curriculum data will reduce cost over time.
