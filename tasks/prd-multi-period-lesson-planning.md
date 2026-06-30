# PRD: Multi-Period Lesson Planning

## Introduction

The current `LessonPlannerAgent` produces a flat lesson plan with a single `activities` array. Biology teachers naturally structure their classes into labeled periods/sections — Opening (5 min), Direct Instruction (15 min), Guided Practice (10 min), etc. This flat structure makes it hard for teachers to scan, reorder, or adapt a plan before class.

This feature restructures the lesson plan output into labeled period blocks (Phase 1) and lays the database groundwork for multi-day unit plans (Phase 2). The existing `activities` field is preserved for backward compatibility so no consuming code breaks immediately.

## Goals

- Split a single lesson plan into labeled period blocks with typed fields
- Keep the existing `activities` field working for backward compatibility
- Add DB columns (`unit_id`, `day_index`, `section_order`) to support future multi-day plans
- Update all exporters (DOCX, PDF), API schemas, and frontend to render periods
- Add unit-level feature flags (exit ticket, differentiation, etc.) — not per-period

## User Stories

### US-001: Update LESSON_SYSTEM_PROMPT to output periods
**Description:** As a developer, I want the LLM prompt to generate `periods` instead of a flat `activities` array so the lesson plan has structure.

**Acceptance Criteria:**
- [ ] `LESSON_SYSTEM_PROMPT` (or equivalent) instructs the LLM to output `periods` as a JSON array of `Period` objects
- [ ] Each period includes: `name`, `duration_minutes`, `objective`, `description`, `activity_type`, `teacher_activity`, `student_activity`, `materials_needed`
- [ ] The existing `activities` field is derived from `periods` for backward compatibility
- [ ] `LessonPlanOutput` / response schema accepts both `periods: list[Period]` and `activities: list[Activity]`
- [ ] Typecheck passes

### US-002: Add DB columns for multi-day groundwork
**Description:** As a developer, I want `unit_id`, `day_index`, and `section_order` columns on the `LessonPlan` table to support future multi-day plans.

**Acceptance Criteria:**
- [ ] Migration adds `unit_id` (UUID, nullable), `day_index` (int, nullable), `section_order` (int, nullable) to the `LessonPlan` table
- [ ] Existing rows backfilled as `null` for all three columns
- [ ] No existing functionality breaks
- [ ] Typecheck passes

### US-003: Update LessonPlanResponse schema with periods field
**Description:** As a frontend developer, I want the API to return `periods` in the lesson plan response so the UI can render them.

**Acceptance Criteria:**
- [ ] `LessonPlanResponse` Pydantic schema includes optional `periods: list[Period]`
- [ ] `Period` sub-schema defined with all required fields
- [ ] The `activities` field remains in the response (not removed)
- [ ] `GET /lesson/{id}` returns `periods` when populated
- [ ] Typecheck passes

### US-004: Update DOCX/PDF exporters to render periods
**Description:** As a teacher, I want exported lesson documents to show period blocks so I can follow the lesson structure in print.

**Acceptance Criteria:**
- [ ] DOCX exporter renders periods as labeled sections with name, duration, and description
- [ ] PDF exporter renders periods as labeled sections with name, duration, and description
- [ ] Fallback to rendering `activities` when `periods` is empty
- [ ] Unit tests for both exporters
- [ ] Typecheck passes

### US-005: Update frontend detail page to render periods
**Description:** As a teacher, I want to see period blocks on the lesson plan detail page so I can quickly scan the class structure.

**Acceptance Criteria:**
- [ ] Lesson plan detail page renders periods as visually distinct cards/sections
- [ ] Each period shows name, duration, objective, description, activity_type, teacher_activity, student_activity, materials_needed
- [ ] Fallback to rendering `activities` when `periods` is not available
- [ ] Typecheck passes
- [ ] Verify in browser using Playwright browser tools

### US-006: Add unit tests
**Description:** As a developer, I want unit tests covering period generation, schema validation, and exporter rendering so the feature is regression-safe.

**Acceptance Criteria:**
- [ ] Test that `LESSON_SYSTEM_PROMPT` produces valid period output from LLM mock
- [ ] Test that `LessonPlanResponse` schema accepts and validates periods
- [ ] Test that DOCX/PDF exporters render periods correctly
- [ ] Test backward compatibility: API still works when no periods are present
- [ ] All tests pass with `pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint"`

### US-007: (Phase 2 placeholder) Multi-day generate endpoint
**Description:** As a teacher, I want to generate a full unit (multiple days) of lesson plans in one request so I can plan a week ahead.

**Acceptance Criteria:**
- [ ] `POST /lesson/unit/generate` accepts `days: int`, `unit_title: str`, and existing lesson params
- [ ] Returns list of lesson plans with `day_index` populated 1..N
- [ ] Each lesson plan has its own `periods` as defined in Phase 1
- [ ] Typecheck passes
- [ ] Verify in browser using Playwright browser tools

## Functional Requirements

- FR-1: `LESSON_SYSTEM_PROMPT` must be updated to emit `periods: [...]` in the structured output
- FR-2: The `Period` object must contain: `name`, `duration_minutes`, `objective`, `description`, `activity_type`, `teacher_activity`, `student_activity`, `materials_needed`
- FR-3: The existing `activities` field must remain functional and be populated alongside `periods`
- FR-4: `LessonPlan` DB model gains nullable columns: `unit_id` (UUID), `day_index` (int), `section_order` (int)
- FR-5: `LessonPlanResponse` schema includes optional `periods: list[Period]` without removing `activities`
- FR-6: DOCX exporter must render period blocks when `periods` is non-empty, falling back to `activities`
- FR-7: PDF exporter must render period blocks when `periods` is non-empty, falling back to `activities`
- FR-8: Frontend lesson detail page must render period blocks as visually distinct sections
- FR-9: Feature flags (`generate_exit_ticket`, `differentiation`, `diagram_suggestions`, `misconception_activities`) must apply at the lesson level, not per-period
- FR-10: The 4 existing sub-generators (ExitTicketGenerator, DifferentiationGenerator, etc.) must remain unchanged
- FR-11: `POST /lesson/unit/generate` (Phase 2) must accept `days` and `unit_title` and return multiple lesson plans with incremented `day_index`
- FR-12: All existing tests must pass without modification

## Non-Goals

- No monthly or term-level plan generation
- No per-period feature flags (exit ticket, differentiation, diagram suggestions, misconception activities remain lesson-level)
- No automatic scheduling or calendar integration
- No drag-and-drop period reordering in the frontend (future enhancement)
- No changes to the Telegram bot lesson flow
- No removal or deprecation of the `activities` field
- No migration of existing lesson plans to the new period structure

## Design Considerations

- **Backward compatibility:** The `activities` field stays in the response. The `periods` field is additive. Any consumer that reads `activities` continues to work unchanged.
- **Prompt design:** Use the existing `_call_structured` pattern with a new Pydantic model for the structured output. The prompt instructs the LLM to produce `periods`, and `activities` is derived post-hoc.
- **Existing 4 sub-generators** (ExitTicketGenerator, DifferentiationGenerator, DiagramSuggestionGenerator, MisconceptionGenerator) remain untouched. Feature flags are evaluated once per lesson, not per period.
- **Frontend rendering:** Reuse existing card/list component patterns. Add a `PeriodCard` component that mirrors the existing activity layout but adds period-specific fields.

## Technical Considerations

- **Prompt engineering:** The `LESSON_SYSTEM_PROMPT` will need careful design to produce high-quality period splits. Typical periods for a biology class: Opening (5min), Review/Homework Check (5min), Direct Instruction (10-15min), Guided Practice (10-15min), Independent Practice (10min), Closing/Exit Ticket (5min).
- **Backward compat hack:** The LLM must generate both `periods` and `activities` in one call. If this produces inconsistent output, a simpler approach is to generate `periods` and derive `activities` by flattening period content post-hoc.
- **DB migration safety:** `unit_id`, `day_index`, `section_order` are nullable. No existing queries break. Phase 2 will add foreign key constraints when the `Unit` table is introduced.
- **Exporter changes:** Both `docx_exporter.py` and `pdf_exporter.py` need a new `_render_periods()` helper. Follow the same pattern as the existing `_render_activities()`.
- **Phase 2 endpoint:** `POST /lesson/unit/generate` will call the existing `LessonPlannerAgent` in a loop (once per day), passing `day_index` and `unit_id`.

## Success Metrics

- All 6 US stories pass their acceptance criteria
- All existing tests pass without modification
- DOCX/PDF exports render periods without regressions
- Frontend renders periods with no visual regressions on existing lesson plans (which have `activities` but no `periods`)
- Typecheck and lint pass with zero new warnings

## Open Questions

- **Should `materials_needed` be per-period or lesson-level?** Currently specced as per-period. If materials rarely change between periods, a lesson-level list reduces duplication. Decision: keep per-period for granularity; the LLM can repeat items across periods if needed.
- **Should `objective` also exist at the lesson level alongside per-period objectives?** A lesson-level objective could serve as the summary, while per-period objectives are more granular. Decision deferred — start with per-period only, add lesson-level if teachers request it.
- **Should the existing `activities` array be flat-mapped from periods or generated separately by the LLM?** Flat-mapping from periods is simpler and guarantees consistency. The PRD assumes the LLM generates `periods` and `activities` is derived. Verify during US-001 implementation.
- **Phase 2 scope:** Should `POST /lesson/unit/generate` support mixed activity types across days? Decision deferred until Phase 2 specification.
