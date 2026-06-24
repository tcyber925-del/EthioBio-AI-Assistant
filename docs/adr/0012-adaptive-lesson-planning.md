# Adaptive Lesson Planning — Differentiation and Diagram Suggestions

The Adaptive Lesson Planning module (Wave 7) extends the existing `LessonPlannerAgent` with three new LLM-generated components: differentiated activities for three learner groups (support/standard/advanced), suggested diagrams matched to the lesson topic, and structured exit tickets (the latter carried over from Wave 4 but consolidated here).

**Status:** accepted

## Context

The existing `LessonPlannerAgent` at `src/agents/lesson_planner.py` generated a single-track lesson plan with `activities`, `assessment`, and `teacher_notes`. Two gaps prevented adaptive teaching:

1. **No differentiation**: All students received the same activities regardless of readiness level. Ethiopian classrooms often have 40+ students with wide ability ranges.
2. **No diagram integration**: Biology is heavily visual (cell structure, photosynthesis, genetics), but the lesson planner never suggested or linked to diagrams.

## Decision

Three new parameters on `POST /lesson-plan/generate`:

1. **`generate_differentiation: bool`**: When true, calls a separate LLM prompt (`DIFFERENTIATION_PROMPT`) that generates three `DifferentiationActivity` objects — one each for support (scaffolded), standard (grade-level), and advanced (extended) groups. Each includes `group`, `description`, and `duration_minutes`.

2. **`generate_diagram_suggestions: bool`**: When true, calls `DIAGRAM_SUGGESTION_PROMPT` to generate `DiagramSuggestion` objects with `title`, `description`, and `diagram_type` (flowchart/labeling/concept_map/comparison/process/anatomy).

3. **`generate_exit_ticket: bool`**: Carried over from Wave 4 — generates 3 structured questions.

All three use a shared `_call_structured()` helper that handles JSON extraction and error handling uniformly.

The `LessonPlanResponse` schema now includes optional `differentiation`, `diagram_suggestions`, and `exit_ticket` fields.

## Consequences

- Differentiation and diagram suggestions are computed on-the-fly and not persisted in the `LessonPlan` table — they are re-generated each time. This keeps the DB schema stable and avoids duplication of LLM output.
- The three sub-prompts run sequentially (not parallel) to stay within the agent's single-LLM pattern. For latency-sensitive use, they could be parallelized with `asyncio.gather()`.
- Diagram suggestions are descriptive only — they don't create actual diagram files. Integration with the existing diagram labeling module (`src/api/diagram.py`) is future work.
- The schema validation on `diagram_type` ensures frontends can reliably render the right visual component.
