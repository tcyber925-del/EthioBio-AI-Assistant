# Amharic Localization — Phase 1: Amharic-First Student Mode

## Overview

Move from "English with Amharic sprinkles" to true Amharic-first AI output. Three language modes (`en`, `am`, `both`), persisted preferences, and localized Telegram bot strings.

## Scope

Dashboard UI i18n is **deferred** — students interact via Telegram + API, not the dashboard.

## Design

### 1. Language Enum

`src/schemas/common.py` — replace bare `str` with typed enum:

```python
class LanguageEnum(str, enum.Enum):
    EN = "en"    # English only (default)
    AM = "am"    # Pure Amharic output
    BOTH = "both" # Bilingual mixed

    def is_amharic(self) -> bool: ...
    def is_bilingual(self) -> bool: ...
```

All schema classes (`ChatRequest`, `TutorRequest`, `GraphChatRequest`, `QuizGenerateRequest`, `LessonPlanRequest`, `ParentSummaryRequest`) switch from `str` → `LanguageEnum`. No behavior change for callers passing `"en"` — string enum accepts both.

### 2. Three-Way LLM Prompts

Each agent's language instruction becomes an explicit 3-way switch:

| Mode | Tutor/Node | Quiz | Lesson | Parent Summary | Safety |
|------|-----------|------|--------|----------------|--------|
| `en` | "Answer in English." (unchanged) | "Generate questions in English." | "Generate in English." | English summary | English check |
| `am` | "Respond entirely in Amharic. Never mix English unless quoting a scientific term." | "Generate questions in Amharic with Amharic answer explanations." | "Generate content entirely in Amharic." | Pure Amharic summary | Amharic check |
| `both` | "Answer in English with Amharic explanation." (unchanged) | "Questions in English, answers in Amharic." | "English with Amharic key terms." | English + Amharic (current) | Bilingual check |

`_build_system_prompt(language)` — factory method on `TutorAgent`/`TutorNode`. Same pattern already exists; just adds the `am` branch.

### 3. SafetyNode Language Awareness

`SafetyNode.__call__()` receives `AgentState.language`. System prompt includes language-quality criteria matching the output language. Currently it has no `language` context — adds `"Language quality (proper Amharic)"` for `am` mode, `"proper English/Amharic"` for `both`.

### 4. Language Persistence

- **Telegram bot**: On `/language` selection, call `PATCH /users/{telegram_id}/language` with body `{"language": "am"}`. Added endpoint in `src/api/users.py`.
- **Bot startup**: Look up `User.language_preference` by telegram_id on first interaction, store in `context.user_data["language"]`.
- **API default**: `/chat` endpoint reads `user.language_preference` from DB if `language` not explicitly provided in request.

### 5. RetrievalFilter Language

`to_chroma_where()` currently ignores its `language` field. Add filter `metadata["language"] == language` when language is `"am"` or `"both"`. No Amharic chunks exist yet — this is future-proofing and will return empty rather than English chunks for `am` mode (forcing LLM to translate from retrieved English context).

### 6. Telegram Bot Localization

`src/telegram/i18n.py` — translation dict (~40 strings):

```python
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": { ... },
    "am": { ... },
}
def t(key: str, lang: str = "en") -> str: ...
```

`keyboards.py` — functions accept `language: str = "en"` param, call `t(key, lang)` for button labels.

`bot.py` — pass `context.user_data.get("language", "en")` to all keyboard calls.

String list (appx):
- Main menu: Ask a Question, Take a Quiz, Lesson Plan, Parent Report, Recovery Plan, Progress, Language, Help
- Quiz: Start Quiz, Next Question, Show Hint, Reveal Answer, Grade Quiz
- Recovery: View Plans, Complete Task, Back
- General: Back to Menu, Cancel, Confirm, Yes, No, Loading, Error generic, Language selector prompt
- 7 error/status messages

### 7. Files Changed

| File | Change |
|------|--------|
| `src/schemas/common.py` | Add `LanguageEnum`, update `ChatRequest.language` |
| `src/schemas/quiz.py` | `language: LanguageEnum` |
| `src/schemas/lesson.py` | `language: LanguageEnum` |
| `src/schemas/progress.py` | `language: LanguageEnum` |
| `src/graph/state.py` | `language: LanguageEnum` |
| `src/agents/tutor.py` | 3-way `_build_system_prompt()` |
| `src/agents/quiz.py` | 3-way `lang_instruction` |
| `src/agents/lesson_planner.py` | 3-way `lang_instruction` |
| `src/agents/parent_summary.py` | 3-way generation |
| `src/agents/safety.py` | Accept `language` param, 3-way check |
| `src/graph/nodes/tutor.py` | 3-way prompt |
| `src/graph/nodes/safety.py` | Pass `state.language` |
| `src/graph/orchestrator.py` | Accept `LanguageEnum` |
| `src/api/chat.py` | Default to DB `language_preference` |
| `src/api/graph.py` | `LanguageEnum` type |
| `src/api/parent.py` | `LanguageEnum` type |
| `src/api/quiz.py` | `LanguageEnum` type |
| `src/api/lesson.py` | `LanguageEnum` type |
| `src/api/users.py` | Add `PATCH /users/{telegram_id}/language` |
| `src/retrieval/adapter.py` | `to_chroma_where()` language filter |
| `src/telegram/i18n.py` | **New** — translation dict |
| `src/telegram/keyboards.py` | Accept `language` param |
| `src/telegram/bot.py` | Sync language to/from DB, pass lang to keyboards |

### 8. Out of Scope (Deferred)

- Dashboard i18n (sidebar, pages, components)
- Email templates (`src/notifications/templates/`)
- Amharic textbook ingestion/OCR
- Locale-aware date/number formatting
- Ethiopian calendar support
