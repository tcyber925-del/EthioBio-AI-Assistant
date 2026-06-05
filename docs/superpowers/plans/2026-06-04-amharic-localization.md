# Amharic Localization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) for syntax tracking.

**Goal:** Add true pure-Amharic output mode (`am`) alongside existing `en` and `both`, persist language preference to DB, sync Telegram bot language, and localize Telegram bot strings.

**Architecture:** Replace bare `str` with `LanguageEnum` across all schemas; add 3-way prompt branches in all 5 agents (tutor, quiz, lesson, parent_summary, safety); add `src/telegram/i18n.py` translation dict; wire language filter in `RetrievalFilter`; sync Telegram → DB.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, LangGraph, ChromaDB, Ollama, python-telegram-bot

---

### Task 1: Add LanguageEnum and update schemas

**Files:**
- Modify: `src/schemas/common.py`
- Modify: `src/schemas/quiz.py:26`
- Modify: `src/schemas/lesson.py:13`
- Modify: `src/schemas/progress.py:26`
- Test: (covered by existing tests — no behavior change)

- [ ] **Step 1: Add LanguageEnum to common schemas**

```python
# Add to src/schemas/common.py
import enum

class LanguageEnum(str, enum.Enum):
    EN = "en"
    AM = "am"
    BOTH = "both"

    def is_amharic(self) -> bool:
        return self == self.AM

    def is_bilingual(self) -> bool:
        return self == self.BOTH

    def is_english(self) -> bool:
        return self == self.EN
```

- [ ] **Step 2: Update ChatRequest.language to use LanguageEnum**

```python
# In src/schemas/common.py, change:
    language: str = "en"
# to:
    language: LanguageEnum = LanguageEnum.EN
```

- [ ] **Step 3: Update QuizGenerateRequest.language**

```python
# In src/schemas/quiz.py, change:
    language: str = "en"
# to:
    language: LanguageEnum = LanguageEnum.EN
# Add import:
from src.schemas.common import LanguageEnum
```

- [ ] **Step 4: Update LessonPlanRequest.language**

```python
# In src/schemas/lesson.py, change:
    language: str = "en"
# to:
    language: LanguageEnum = LanguageEnum.EN
# Add import:
from src.schemas.common import LanguageEnum
```

- [ ] **Step 5: Update ParentSummaryRequest.language**

```python
# In src/schemas/progress.py, change:
    language: str = "en"
# to:
    language: LanguageEnum = LanguageEnum.EN
# Add import:
from src.schemas.common import LanguageEnum
```

- [ ] **Step 6: Update GraphChatRequest.language**

```python
# In src/api/graph.py, change:
    language: str = "en"
# to:
    language: LanguageEnum = LanguageEnum.EN
# Add import:
from src.schemas.common import LanguageEnum
```

- [ ] **Step 7: Verify no other schemas use bare `language: str`**

Run: `rg 'language: str = "en"' src/schemas/ src/api/`
Expected: no remaining bare-string language fields.

- [ ] **Step 8: Commit**

```bash
git add src/schemas/common.py src/schemas/quiz.py src/schemas/lesson.py src/schemas/progress.py src/api/graph.py
git commit -m "feat(i18n): add LanguageEnum, update all schemas from str to enum"
```

---

### Task 2: Three-way prompts in TutorAgent and TutorNode

**Files:**
- Modify: `src/agents/tutor.py:160-161`
- Modify: `src/graph/nodes/tutor.py:96`
- Modify: `src/graph/state.py:27`

- [ ] **Step 1: Update AgentState.language to LanguageEnum**

```python
# In src/graph/state.py, change:
    language: str = "en"
# to:
    language: str = "en"  # keep str for dataclass serialization, cast at use site
```

(AgentState is a dataclass, not a Pydantic model — keep as str for now; the orchestator casts from the schema enum before setting.)

- [ ] **Step 2: Replace TutorAgent's 2-way language with 3-way**

```python
# In src/agents/tutor.py, replace line 160:
        lang_context = "Answer in English." if language == "en" else "Answer in English with Amharic explanation."
# with:
        if language == "am":
            lang_context = (
                "Respond entirely in Amharic (አማርኛ). "
                "Use Amharic biology terminology. "
                "Never mix English unless quoting a technical term or scientific name. "
                "Always provide the Amharic equivalent of key terms."
            )
        elif language == "both":
            lang_context = (
                "Answer in English with Amharic explanation. "
                "Provide key terms in both English and Amharic."
            )
        else:
            lang_context = "Answer in English."
```

- [ ] **Step 3: Replace TutorNode's 2-way language with 3-way**

```python
# In src/graph/nodes/tutor.py, replace line 96:
        lang_context = "Answer in English." if state.language == "en" else "Answer in English with Amharic explanation."
# with:
        lang = state.language
        if lang == "am":
            lang_context = (
                "Respond entirely in Amharic (አማርኛ). "
                "Use Amharic biology terminology. "
                "Never mix English unless quoting a technical term or scientific name. "
                "Always provide the Amharic equivalent of key terms."
            )
        elif lang == "both":
            lang_context = "Answer in English with Amharic explanation. Provide key terms in both English and Amharic."
        else:
            lang_context = "Answer in English."
```

- [ ] **Step 4: Update TutorAgent's system prompt to remove old Amharic reference**

The system prompt says "The curriculum is English-first. You may also provide explanations in Amharic when requested." This is now superseded by the explicit `lang_context`. Remove this line or leave it as a fallback — leaving it is harmless but less precise. Change to:

```python
# In TUTOR_SYSTEM_PROMPT and SOCRATIC_SYSTEM_PROMPT (both files), replace:
"The curriculum is English-first. You may also provide explanations in Amharic when requested."
# with:
"The curriculum is in English. Follow language instructions provided in the user message."
```

- [ ] **Step 5: Commit**

```bash
git add src/agents/tutor.py src/graph/nodes/tutor.py src/graph/state.py
git commit -m "feat(i18n): 3-way language prompts in TutorAgent and TutorNode"
```

---

### Task 3: Three-way prompts in QuizAgent, LessonPlannerAgent, ParentSummaryAgent

**Files:**
- Modify: `src/agents/quiz.py:56`
- Modify: `src/agents/lesson_planner.py:41-42`
- Modify: `src/agents/parent_summary.py:50-51,76-85`

- [ ] **Step 1: QuizAgent 3-way lang_instruction**

```python
# In src/agents/quiz.py, replace line 56:
        lang_instruction = "Generate all content in English." if language == "en" else "Generate questions in English with Amharic answer explanations."
# with:
        if language == "am":
            lang_instruction = "Generate all content in Amharic (አማርኛ). Questions, options, correct answer, and explanations must all be in Amharic."
        elif language == "both":
            lang_instruction = "Generate questions in English with Amharic answer explanations. Key terms in both languages."
        else:
            lang_instruction = "Generate all content in English."
```

- [ ] **Step 2: LessonPlannerAgent 3-way lang_instruction**

```python
# In src/agents/lesson_planner.py, replace lines 41-42:
        lang_instruction = "Generate all content in English." if language == "en" else \
            "Generate content in English with key terms also in Amharic."
# with:
        if language == "am":
            lang_instruction = "Generate all content in Amharic (አማርኛ). Lesson plan explanation, activities, assessment — all in Amharic."
        elif language == "both":
            lang_instruction = "Generate content in English with key terms and explanations also in Amharic."
        else:
            lang_instruction = "Generate all content in English."
```

- [ ] **Step 3: ParentSummaryAgent 3-way lang_instruction + translation**

```python
# In src/agents/parent_summary.py, replace lines 50-51:
        lang_instruction = "Write the summary in English." if language == "en" else \
            "Write the summary in Amharic."
# with:
        if language == "am":
            lang_instruction = "Write the summary in Amharic (አማርኛ) only. Use polite, encouraging tone."
        elif language == "both":
            lang_instruction = "Write the summary in English. Include key points also in Amharic."
        else:
            lang_instruction = "Write the summary in English."
```

```python
# Also update the Amharic-translation block (lines 76-85).
# Currently it only generates Amharic translation when language == "en".
# For language="both", also generate Amharic translation.
# For language="am", the summary itself is in Amharic, so skip translation.

        amharic_content = None
        if language in ("en", "both"):
            bilingual = await self._call_llm(
                system_prompt="Translate the following summary to Amharic. Keep the tone positive and constructive.",
                user_message=result["content"],
                session=session,
                temperature=0.3,
                max_tokens=1024,
                request_type="summary_translation",
            )
            amharic_content = bilingual["content"]
```

- [ ] **Step 4: Commit**

```bash
git add src/agents/quiz.py src/agents/lesson_planner.py src/agents/parent_summary.py
git commit -m "feat(i18n): 3-way language in quiz, lesson, parent_summary agents"
```

---

### Task 4: Language-aware SafetyAgent and SafetyNode

**Files:**
- Modify: `src/agents/safety.py:11-21,28,33-35`
- Modify: `src/graph/nodes/safety.py:8-16,23,28`

- [ ] **Step 1: SafetyAgent accepts language param**

```python
# In src/agents/safety.py, change review() signature:
    async def review(
        self,
        content: str,
        grade_level: Optional[int] = None,
        language: str = "en",
        session: Optional[AsyncSession] = None,
    ) -> dict:
```

- [ ] **Step 2: SafetyAgent 3-way prompt**

```python
# Replace SAFETY_SYSTEM_PROMPT with:
SAFETY_SYSTEM_PROMPT = """You are EthioBio Safety Agent, responsible for reviewing content for:
1. Factual accuracy (especially biology curriculum alignment)
2. Grade-appropriateness (content suitable for Grade 7-12 students)
3. Safety (no harmful, dangerous, or inappropriate content)
4. Curriculum match (does it follow Ethiopian biology curriculum)
5. Clarity (is the explanation clear and understandable)
6. Language quality (proper {language})

Analyze the content and respond with a JSON object:
{"safe": true/false, "issues": ["issue1", "issue2"], "score": 0.0-1.0, "suggestions": ["suggestion"]}
"""

# In review() method, use language to format the prompt:
        lang_name = {"en": "English", "am": "Amharic", "both": "English/Amharic"}.get(language, "English")
        safety_prompt = SAFETY_SYSTEM_PROMPT.format(language=lang_name)
```

- [ ] **Step 3: SafetyNode 3-way prompt**

```python
# In src/graph/nodes/safety.py, replace SAFETY_PROMPT and __call__:
SAFETY_PROMPT = """You are EthioBio Safety Agent. Review the following biology content for:
1. Factual accuracy
2. Grade-appropriateness
3. Safety (no harmful content)
4. Curriculum alignment
5. Clarity
6. Language quality (proper {language})

Respond with ONLY a JSON object:
{"safe": true/false, "issues": ["issue1"], "score": 0.0-1.0, "suggestions": ["suggestion"]}"""

    async def __call__(self, state: AgentState) -> AgentState:
        grade_context = f" (Grade {state.grade_level})" if state.grade_level else ""
        lang_name = {"en": "English", "am": "Amharic", "both": "English/Amharic"}.get(state.language, "English")
        safety_prompt = SAFETY_PROMPT.format(language=lang_name)
        # ... rest of method unchanged, use safety_prompt instead of SAFETY_PROMPT
```

- [ ] **Step 4: Commit**

```bash
git add src/agents/safety.py src/graph/nodes/safety.py
git commit -m "feat(i18n): language-aware safety checks in SafetyAgent and SafetyNode"
```

---

### Task 5: Language persistence — DB sync from Telegram

**Files:**
- Modify: `src/telegram/bot.py:68,467-474,1479-1488`
- Modify: `src/api/users.py` (create if not exists) or add to `src/api/admin.py`
- Modify: `src/database/models.py` (check language_preference exists)

- [ ] **Step 1: Add endpoint to update user language preference**

If `src/api/users.py` doesn't exist, create it. Otherwise add to appropriate module.

```python
# In src/api/users.py (create if needed):
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import User
from src.database.session import get_session

router = APIRouter(prefix="/users", tags=["Users"])

@router.patch("/{telegram_id}/language")
async def update_user_language(telegram_id: int, language: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if language not in ("en", "am", "both"):
        raise HTTPException(status_code=400, detail="Invalid language. Must be en, am, or both.")
    user.language_preference = language
    await session.commit()
    return {"status": "ok", "language": language}
```

- [ ] **Step 2: Register the users router in main.py**

```python
# In src/main.py, add:
from src.api.users import router as users_router
# and:
app.include_router(users_router)
```

- [ ] **Step 3: Sync Telegram language selection → DB**

```python
# In src/telegram/bot.py, in handle_language_select (around line 1484), after:
    context.user_data["language"] = code
# add:
    await _db_try(_sync_language)
    async def _sync_language():
        factory = async_session_factory()
        async with factory() as session:
            async with httpx.AsyncClient() as client:
                api_base = settings.api_base_url
                await client.patch(
                    f"{api_base}/users/{update.effective_user.id}/language",
                    params={"language": code},
                )
```

- [ ] **Step 4: Load DB language preference on bot startup/start**

In the `start()` function (line 77), after `_try_register_user`:

```python
    lang = context.user_data.get("language")
    if not lang:
        async def _load_lang():
            factory = async_session_factory()
            async with factory() as session:
                result = await session.execute(
                    select(User.language_preference).where(User.telegram_id == update.effective_user.id)
                )
                row = result.scalar_one_or_none()
                if row:
                    context.user_data["language"] = row
        await _db_try(_load_lang)
```

- [ ] **Step 5: Commit**

```bash
git add src/api/users.py src/main.py src/telegram/bot.py
git commit -m "feat(i18n): persist language preference, sync Telegram to DB"
```

---

### Task 6: Telegram bot localization (i18n.py + keyboards.py)

**Files:**
- Create: `src/telegram/i18n.py`
- Modify: `src/telegram/keyboards.py`
- Modify: `src/telegram/bot.py` (pass language to keyboards)

- [ ] **Step 1: Create translation dict**

```python
# src/telegram/i18n.py
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "ask_question": "🧬 Ask a Question",
        "take_quiz": "📝 Take a Quiz",
        "my_progress": "📊 My Progress",
        "socratic_on": "🧠 Socratic: ON",
        "socratic_off": "🧠 Socratic: OFF",
        "language": "🌐 Language",
        "teacher_tools": "👨‍🏫 Teacher Tools",
        "help": "❓ Help",
        "start_quiz": "Start Quiz",
        "next_question": "➡️ Next Question",
        "show_hint": "💡 Show Hint",
        "reveal_answer": "🔍 Reveal Answer",
        "grade_quiz": "Grade Quiz",
        "retry_quiz": "🔁 Retry Quiz",
        "new_quiz": "📝 New Quiz",
        "main_menu": "🏠 Main Menu",
        "back": "← Back",
        "back_to_menu": "← Back to Menu",
        "cancel": "Cancel",
        "confirm": "Confirm",
        "yes": "Yes",
        "no": "No",
        "loading": "Loading...",
        "error_generic": "Something went wrong. Please try again.",
        "choose_language": "Choose your language:",
        "language_set": "Language set to {name}!",
        "create_lesson_plan": "📋 Create Lesson Plan",
        "review_quizzes": "📄 Review Quizzes",
        "open_dashboard": "📈 Open Dashboard",
        "view_recovery": "Recovery Plan",
        "view_progress": "📊 Progress",
        "broad_hint": "💡 Broad Hint",
        "specific_hint": "💡 Specific Hint",
        "strong_hint": "💡 Strong Hint",
        "end_quiz": "🔙 End Quiz",
        "true": "✅ True",
        "false": "❌ False",
        "choose_grade": "Choose your grade:",
        "choose_topic": "Choose a topic:",
        "choose_quiz_type": "Choose quiz type:",
    },
    "am": {
        "ask_question": "🧬 ጥያቄ ጠይቅ",
        "take_quiz": "📝 ፈተና ውሰድ",
        "my_progress": "📊 እድገቴ",
        "socratic_on": "🧠 ሶክራቲክ: በርቷል",
        "socratic_off": "🧠 ሶክራቲክ: ጠፍቷል",
        "language": "🌐 ቋንቋ",
        "teacher_tools": "👨‍🏫 የመምህራን መሣሪያዎች",
        "help": "❓ እገዛ",
        "start_quiz": "ፈተና ጀምር",
        "next_question": "➡️ ቀጣይ ጥያቄ",
        "show_hint": "💡 ፍንጭ አሳይ",
        "reveal_answer": "🔍 መልሱን ግለጽ",
        "grade_quiz": "ፈተናውን አስተካክል",
        "retry_quiz": "🔁 ፈተናውን ድገም",
        "new_quiz": "📝 አዲስ ፈተና",
        "main_menu": "🏠 ዋና ሜኑ",
        "back": "← ተመለስ",
        "back_to_menu": "← ወደ ዋና ሜኑ ተመለስ",
        "cancel": "ሰርዝ",
        "confirm": "አረጋግጥ",
        "yes": "አዎ",
        "no": "አይ",
        "loading": "በመጫን ላይ...",
        "error_generic": "የሆነ ስህተት ተፈጥሯል። እባክዎ እንደገና ይሞክሩ።",
        "choose_language": "ቋንቋዎን ይምረጡ:",
        "language_set": "ቋንቋ ወደ {name} ተቀይሯል!",
        "create_lesson_plan": "📋 የትምህርት እቅድ ፍጠር",
        "review_quizzes": "📄 ፈተናዎችን አስተካክል",
        "open_dashboard": "📈 ዳሽቦርድ ክፈት",
        "view_recovery": "የማገገሚያ እቅድ",
        "view_progress": "📊 እድገት",
        "broad_hint": "💡 ሰፊ ፍንጭ",
        "specific_hint": "💡 ዝርዝር ፍንጭ",
        "strong_hint": "💡 ጠንካራ ፍንጭ",
        "end_quiz": "🔙 ፈተናውን ጨርስ",
        "true": "✅ እውነት",
        "false": "❌ ሐሰት",
        "choose_grade": "ክፍልዎን ይምረጡ:",
        "choose_topic": "ርዕስ ይምረጡ:",
        "choose_quiz_type": "የፈተና አይነት ይምረጡ:",
    },
}

def t(key: str, lang: str = "en") -> str:
    """Translate a key to the given language. Falls back to English."""
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))
```

- [ ] **Step 2: Update keyboards.py to accept language param**

Add import and default param to each function:

```python
from src.telegram.i18n import t

def main_menu_keyboard(socratic_enabled: bool = False, language: str = "en"):
    socratic_label = t("socratic_on", language) if socratic_enabled else t("socratic_off", language)
    buttons = [
        [InlineKeyboardButton(t("ask_question", language), callback_data="tutor")],
        [InlineKeyboardButton(t("take_quiz", language), callback_data="quiz")],
        [InlineKeyboardButton(t("my_progress", language), callback_data="progress")],
        [InlineKeyboardButton(socratic_label, callback_data="socratic_toggle")],
        [InlineKeyboardButton(t("language", language), callback_data="language")],
        [InlineKeyboardButton(t("teacher_tools", language), callback_data="teacher_tools")],
        [InlineKeyboardButton(t("help", language), callback_data="help")],
    ]
    return InlineKeyboardMarkup(buttons)
```

Repeat for all keyboard functions: `teacher_tools_keyboard`, `language_keyboard`, `quiz_type_keyboard`, `grade_keyboard`, `answer_options_keyboard`, `tf_keyboard`, `quiz_next_keyboard`, `quiz_result_keyboard`, `back_keyboard`, `hint_keyboard`, `socratic_toggle_keyboard`.

All functions get `language: str = "en"` parameter. The `grade_keyboard` label changes to `t("choose_grade", language)` prefix and `f"ክፍል {grade}"` / `f"Grade {grade}"` depending on language — but since grades are numbers, keep the simple format and wrap: `t("choose_grade", language)` for the prompt.

Actually for grade_keyboard, just change the prompt text that precedes it, not the buttons themselves (grade numbers are universal). Same for answer_options_keyboard (letters A-F are universal).

Hint keyboard: use `t("broad_hint")`, `t("specific_hint")`, `t("strong_hint")`, `t("reveal_answer")`, `t("back_to_menu")`.

- [ ] **Step 3: Update bot.py to pass language to keyboards**

Every call to `main_menu_keyboard(...)` becomes `main_menu_keyboard(..., language=context.user_data.get("language", "en"))`.

Find all calls in bot.py:

```python
# Replace pattern: main_menu_keyboard(...)
# With: main_menu_keyboard(..., language=context.user_data.get("language", "en"))

# Do this for all keyboard calls in the file.
# Number of call sites: ~30
```

Use search-and-replace approach:
- `main_menu_keyboard(` → `main_menu_keyboard(language=context.user_data.get("language", "en"),` and adjust param ordering
- Actually, simpler: add `language` as keyword arg at each call site

Best approach: add a helper at the top of bot.py:

```python
def _lang(context) -> str:
    return context.user_data.get("language", "en")
```

Then replace each `main_menu_keyboard(socratic)` with `main_menu_keyboard(socratic, language=_lang(context))` and other keyboard calls similarly.

- [ ] **Step 4: Update bot.py menu messages that contain static English text**

In `start()` and other functions, replace inline English strings with `t()` calls. Examples:

```python
# start() function (line 80-84):
    await update.message.reply_text(
        t("welcome", _lang(context)),
        reply_markup=main_menu_keyboard(socratic, language=_lang(context)),
    )
```

Add these keys to TRANSLATIONS:
```python
    "en": {
        "welcome": "Welcome to EthioBio AI Assistant!\n\nI'm your biology learning assistant for Ethiopian Grades 7-12.\n\nSend me any biology question, or use the menu below:",
        # ...
    },
    "am": {
        "welcome": "እንኳን ወደ ኢትዮባዮ AI ረዳት በደህና መጡ!\n\nየባዮሎጂ ትምህርት ረዳትዎ ነኝ ለኢትዮጵያ 7-12 ክፍሎች።\n\nማንኛውንም የባዮሎጂ ጥያቄ ይላኩ፣ ወይም ከታች ያለውን ሜኑ ይጠቀሙ:",
        # ...
    },
```

Apply `t()` to other static strings: `handle_language_select` response, `language_command` response, etc.

- [ ] **Step 5: Commit**

```bash
git add src/telegram/i18n.py src/telegram/keyboards.py src/telegram/bot.py
git commit -m "feat(i18n): Telegram bot Amharic localization via i18n.py"
```

---

### Task 7: RetrievalFilter language awareness

**Files:**
- Modify: `src/retrieval/adapter.py:43-58`

- [ ] **Step 1: Add language filter to to_chroma_where()**

```python
# In src/retrieval/adapter.py, in to_chroma_where(), after the source_type filter:
        if self.language and self.language != "en":
            filters.append({"language": {"$eq": self.language}})
```

This is future-proofing — no chunks have `language` metadata yet (OCR is English-only). When `language="am"` or `"both"`, it will filter for matching chunks. With no matches, the LLM receives an empty context and will translate from general knowledge.

- [ ] **Step 2: Commit**

```bash
git add src/retrieval/adapter.py
git commit -m "feat(i18n): add language filter to RetrievalFilter.to_chroma_where()"
```

---

### Task 8: Orchestrator and API wiring

**Files:**
- Modify: `src/graph/orchestrator.py:53,75`
- Modify: `src/api/chat.py:68`
- Modify: `src/api/quiz.py:115`
- Modify: `src/api/lesson.py:25`
- Modify: `src/api/parent.py:53,180,202`

- [ ] **Step 1: Update run_graph() signature to accept LanguageEnum**

```python
# In src/graph/orchestrator.py, change:
    language: str = "en",
# to:
    language: str = "en",  # keep as str for dataclass, callers pass .value
```

Callers (like graph.py) already pass `request.language` which is now a `LanguageEnum`. Since `AgentState.language` is `str`, convert: `language=request.language.value if isinstance(request.language, LanguageEnum) else request.language`.

- [ ] **Step 2: Ensure all API endpoints pass language correctly**

All API handlers already pass `language=request.language`. Since `LanguageEnum` is a `str` enum, it serializes to `"en"`/`"am"`/`"both"` automatically in JSON. As a Python value, it compares equal to its string value (`"am" == LanguageEnum.AM` is `True`). So the existing code continues to work without changes to comparison logic.

- [ ] **Step 3: Chat endpoint defaults to DB language_preference**

```python
# In src/api/chat.py, in chat_tutor(), before calling agent.answer:
        effective_language = request.language
        if request.user_id and effective_language == LanguageEnum.EN:
            from src.database.models import User
            result = await session.execute(select(User.language_preference).where(User.id == request.user_id))
            db_lang = result.scalar_one_or_none()
            if db_lang and db_lang != "en":
                effective_language = LanguageEnum(db_lang)
```

- [ ] **Step 4: Commit**

```bash
git add src/graph/orchestrator.py src/api/chat.py
git commit -m "feat(i18n): wire language through orchestrator and API endpoints"
```

---

### Task 9: Tests

**Files:**
- Create: `tests/test_language_enum.py`
- Create: `tests/test_i18n.py`
- Modify: existing agent tests may need updates

- [ ] **Step 1: Test LanguageEnum behavior**

```python
# tests/test_language_enum.py
import pytest
from src.schemas.common import LanguageEnum

def test_enum_values():
    assert LanguageEnum.EN.value == "en"
    assert LanguageEnum.AM.value == "am"
    assert LanguageEnum.BOTH.value == "both"

def test_is_amharic():
    assert LanguageEnum.AM.is_amharic()
    assert not LanguageEnum.EN.is_amharic()
    assert not LanguageEnum.BOTH.is_amharic()

def test_is_bilingual():
    assert LanguageEnum.BOTH.is_bilingual()
    assert not LanguageEnum.EN.is_bilingual()
    assert not LanguageEnum.AM.is_bilingual()

def test_is_english():
    assert LanguageEnum.EN.is_english()
    assert not LanguageEnum.AM.is_english()
    assert not LanguageEnum.BOTH.is_english()

def test_string_comparison():
    assert LanguageEnum.EN == "en"
    assert LanguageEnum.AM == "am"
    assert LanguageEnum.BOTH == "both"
```

- [ ] **Step 2: Test i18n translations**

```python
# tests/test_i18n.py
from src.telegram.i18n import t, TRANSLATIONS

def test_t_returns_english_by_default():
    assert t("help") == "❓ Help"

def test_t_returns_amharic():
    assert t("help", "am") == "❓ እገዛ"

def test_t_falls_back_to_english():
    assert t("nonexistent_key", "am") == "nonexistent_key"

def test_t_falls_back_to_english_for_unknown_lang():
    assert t("help", "fr") == "❓ Help"

def test_all_keys_have_amharic():
    """Every English key should have an Amharic translation."""
    for key in TRANSLATIONS["en"]:
        assert key in TRANSLATIONS["am"], f"Missing Amharic translation for '{key}'"

def test_no_extra_keys_in_amharic():
    """Amharic should not have keys that English doesn't have."""
    for key in TRANSLATIONS["am"]:
        assert key in TRANSLATIONS["en"], f"Extra key in Amharic: '{key}'"
```

- [ ] **Step 3: Run tests**

Run: `./.venv/bin/pytest tests/test_language_enum.py tests/test_i18n.py -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add tests/test_language_enum.py tests/test_i18n.py
git commit -m "test(i18n): LanguageEnum and i18n translation tests"
```

---

### Task 10: Ruff + typecheck verification

- [ ] **Step 1: Run ruff**

Run: `./.venv/bin/ruff check src/schemas/common.py src/schemas/quiz.py src/schemas/lesson.py src/schemas/progress.py src/api/graph.py src/api/chat.py src/graph/orchestrator.py src/agents/tutor.py src/agents/quiz.py src/agents/lesson_planner.py src/agents/parent_summary.py src/agents/safety.py src/graph/nodes/tutor.py src/graph/nodes/safety.py src/telegram/i18n.py src/telegram/keyboards.py src/telegram/bot.py src/retrieval/adapter.py`
Expected: no new errors (existing errors like E501 in unrelated files are acceptable)

- [ ] **Step 2: Run mypy**

Run: `./.venv/bin/mypy src/`
Expected: no new type errors

- [ ] **Step 3: Run existing test suite**

Run: `./.venv/bin/pytest tests/ -v -k "not test_chat_endpoint and not test_quiz_generate_endpoint"`
Expected: all existing tests pass

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "chore(i18n): lint and typecheck fixes"
```
