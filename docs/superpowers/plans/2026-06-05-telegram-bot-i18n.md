# Telegram Bot Amharic Localization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Translate Telegram bot user-facing strings to Amharic using namespaced JSON message files, Phase 1 (core flows).

**Architecture:** Two JSON message files (`en.json`, `am.json`) sourced as data by an enhanced `t()` function. Replace hardcoded English strings in `bot.py` with `t("namespace.key", lang, **kwargs)` calls. Existing keyboard `t()` already imports from `i18n.py` — no migration needed.

**Tech Stack:** Python 3.12+, python-telegram-bot, JSON

---

### Task 1: Create message JSON files

**Files:**
- Create: `src/telegram/messages/en.json`
- Create: `src/telegram/messages/am.json`

- [ ] **Step 1: Create `src/telegram/messages/` directory and `en.json`**

```bash
mkdir -p src/telegram/messages
```

- [ ] **Step 2: Write `src/telegram/messages/en.json` with all Phase 1 keys**

```json
{
  "start": {
    "dashboard_login": "Your dashboard login code: <b>{code}</b>\n\nThis code expires in 5 minutes. Enter it on the login page.",
    "welcome": "Welcome to EthioSci AI Assistant!\n\nI'm your science learning assistant for Ethiopian Grades 7-12.\n\nSend me any science question, or use the menu below:"
  },
  "common": {
    "error": "Sorry, I encountered an error. Please try again.",
    "cancelled": "Cancelled.",
    "usage_ask": "Usage: /ask <your science question>",
    "thinking": "Thinking...",
    "generating": "Generating..."
  },
  "help": {
    "text": "EthioSci AI Assistant — Help\n\nCommands:\n/start — Show menu\n/help — This message\n/ask <question> — Ask a science question\n/quiz [grade] [topic] — Take a quiz\n/lesson [grade] [topic] — Get a lesson plan\n/language <en|am|both> — Set language\n/grade <7-12> — Set grade level\n/model — Choose AI model\n/socratic — Toggle Socratic mode\n/reveal — Reveal answer\n/recovery — View recovery plans\n/progress — View mastery progress\n/dashboard_login — Get dashboard login code\n/settings — Notification settings\n/cancel — Cancel current operation"
  },
  "tutor": {
    "grade_prompt": "Grade {grade} selected. Send me your science question. I'll help you understand it!",
    "no_question": "No active question. Ask a question first with /ask or select Tutor from the menu.",
    "socratic_on": "Socratic Mode is now ON.\n\nIn Socratic mode, I'll guide you through questions rather than giving direct answers — helping you discover the answer yourself!",
    "socratic_off": "Socratic Mode is now OFF.\n\nI'll give you direct answers with explanations.",
    "revealing_answer": "🔍 Revealing the full answer...",
    "hint_level": "💡 Hint level {level}/3...",
    "hint_revealed": "The answer has already been revealed! Ask a new question to continue.",
    "hint_exhausted": "You've used all hint levels. Tap 'Reveal Answer' to see the full explanation.",
    "hint_usage": "\n\n📊 You used {count} hint(s) before revealing the answer.",
    "misconception": "\n\n💡 I noticed a misunderstanding — gently corrected above.",
    "sources": "\n\n---\nSources: {sources}"
  },
  "gamification": {
    "xp_earned": "\n\n⭐ +{xp} XP for this session",
    "level_up": "\n🎉 LEVEL UP! You are now Level {level}!",
    "xp_quiz": "\n\n⭐ +{xp} XP",
    "level_up_quiz": "\n🎉 LEVEL UP! Now Level {level}!"
  },
  "quiz": {
    "grade_prompt": "Select your grade level:",
    "topic_prompt": "Grade {grade} selected. What topic should the quiz cover?\n(e.g., Cell Biology, Genetics, Ecology)",
    "quiz_type_prompt": "Select quiz type:",
    "generating": "Generating your quiz...",
    "error": "Error generating quiz.",
    "question": "📝 {title}\n\nQuestion {current}/{total}\n<i>{qtype}</i>\n\n{qtext}",
    "correct": "✅ Correct!",
    "wrong": "❌ Wrong. The answer was: {answer}",
    "short_answer": "\n\n✏️ Type your answer below, then tap Next.",
    "complete": "📊 Quiz Complete!\nScore: {correct}/{total} ({pct}%)",
    "score": "⭐ XP earned this quiz: {xp}",
    "cancelled": "Quiz cancelled."
  },
  "lesson": {
    "grade_prompt": "Select grade level:",
    "generating": "Creating lesson plan...",
    "error": "Error creating lesson plan."
  },
  "settings": {
    "text": "⚙️ Notification Settings\n\nMilestone Alerts: {milestone}\nReview Reminders: {reminder}\nDigest Frequency: {digest}\n\nTap to toggle or change settings."
  },
  "language": {
    "choose": "Choose your language:",
    "set": "Language set to {name}!",
    "usage": "Usage: /language <en|am|both>",
    "set_cmd": "Language set to {name}."
  },
  "grade": {
    "set": "Default grade set to Grade {grade}.",
    "usage": "Usage: /grade <7-12>"
  },
  "model": {
    "no_models": "Failed to fetch models. Is the API server running?",
    "no_providers": "Failed to fetch providers.",
    "refresh_failed": "Failed to refresh models.",
    "set_failed": "Failed to set model: {model}",
    "refresh": "🔄 Refresh Models",
    "back_providers": "← Back to Providers"
  },
  "progress": {
    "no_weak": "📊 *Mastery Progress*\n\nNo weak topics detected! You're doing great across all subjects.",
    "need_start": "Please /start first to register."
  },
  "recovery": {
    "no_plans": "📋 *No Active Recovery Plans*\n\nComplete quizzes to identify weak areas. Recovery plans help you strengthen your understanding of challenging topics.",
    "user_not_found": "❌ User not found. Please /start first.",
    "task_not_found": "❌ Task not found.",
    "task_done": "✅ Task *{title}* was already completed!"
  },
  "parent": {
    "usage": "Usage: <code>/parent_register your@email.com</code>\n\nYou need a parent account on the dashboard first. Register at the dashboard, then link your Telegram here.",
    "no_account": "No parent account found with that email. Make sure you registered as a parent on the dashboard first.",
    "already_linked": "This account is already linked to another Telegram user. Contact support if you need to relink.",
    "linked": "Telegram linked! Use /children to view your children's progress.",
    "need_register": "Please register first with /parent_register",
    "no_child": "Child not found.",
    "no_parent": "Parent account not found.",
    "no_student": "Student not found."
  }
}
```

- [ ] **Step 3: Write `src/telegram/messages/am.json` with Amharic translations**

```json
{
  "start": {
    "dashboard_login": "የዳሽቦርድ መግቢያ ኮድዎ፦ <b>{code}</b>\n\nይህ ኮድ በ5 ደቂቃ ውስጥ ያበቃል። በመግቢያ ገፁ ላይ ያስገቡት።",
    "welcome": "እንኳን ወደ ኢትዮባዮ AI ረዳት በደህና መጡ!\n\nየባዮሎጂ ትምህርት ረዳትዎ ነኝ ለኢትዮጵያ 7-12 ክፍሎች።\n\nማንኛውንም የባዮሎጂ ጥያቄ ይላኩ፣ ወይም ከታች ያለውን ሜኑ ይጠቀሙ፦"
  },
  "common": {
    "error": "ይቅርታ፣ ስህተት ተፈጥሯል። እባክዎ እንደገና ይሞክሩ።",
    "cancelled": "ተሰርዟል።",
    "usage_ask": "አጠቃቀም፦ /ask <የባዮሎጂ ጥያቄዎ>",
    "thinking": "በማሰብ ላይ...",
    "generating": "በማዘጋጀት ላይ..."
  },
  "help": {
    "text": "ኢትዮባዮ AI ረዳት — እገዛ\n\nትዕዛዞች፦\n/start — ሜኑ አሳይ\n/help — ይህ መልእክት\n/ask <ጥያቄ> — የባዮሎጂ ጥያቄ ጠይቅ\n/quiz [ክፍል] [ርዕስ] — ፈተና ውሰድ\n/lesson [ክፍል] [ርዕስ] — የትምህርት እቅድ አግኝ\n/language <en|am|both> — ቋንቋ አዘጋጅ\n/grade <7-12> — የክፍል ደረጃ አዘጋጅ\n/model — AI ሞዴል ምረጥ\n/socratic — የሶክራቲክ ሁነታን ቀይር\n/reveal — መልሱን ግለጽ\n/recovery — የማገገሚያ እቅዶችን ተመልከት\n/progress — የእድገት ደረጃ ተመልከት\n/dashboard_login — የዳሽቦርድ መግቢያ ኮድ አግኝ\n/settings — የማሳወቂያ ቅንብሮች\n/cancel — ሂደቱን ሰርዝ"
  },
  "tutor": {
    "grade_prompt": "{grade}ኛ ክፍል ተመርጧል። የባዮሎጂ ጥያቄዎን ይላኩ። እንዲረዱት እረዳዎታለሁ!",
    "no_question": "ምንም ንቁ ጥያቄ የለም። በመጀመሪያ በ /ask ወይም በሜኑ ውስጥ Tutor ን ይምረጡ።",
    "socratic_on": "የሶክራቲክ ሁነታ አሁን በርቷል።\n\nበሶክራቲክ ሁነታ፣ ቀጥተኛ መልስ ከመስጠት ይልቅ በጥያቄዎች እመራለሁ — መልሱን በራስዎ እንዲያገኙ እረዳዎታለሁ!",
    "socratic_off": "የሶክራቲክ ሁነታ አሁን ጠፍቷል።\n\nቀጥተኛ መልሶች ከማብራሪያ ጋር እሰጣለሁ።",
    "revealing_answer": "🔍 ሙሉ መልሱን በመግለጽ ላይ...",
    "hint_level": "💡 የፍንጭ ደረጃ {level}/3...",
    "hint_revealed": "መልሱ አስቀድሞ ተገልጿል! ለመቀጠል አዲስ ጥያቄ ይጠይቁ።",
    "hint_exhausted": "ሁሉንም የፍንጭ ደረጃዎች ተጠቅመዋል። ሙሉ ማብራሪያ ለማየት 'መልሱን ግለጽ' የሚለውን ይንኩ።",
    "hint_usage": "\n\n📊 መልሱን ከመግለጽዎ በፊት {count} ፍንጭ(ች) ተጠቅመዋል።",
    "misconception": "\n\n💡 የተሳሳተ ግንዛቤ አስተውያለሁ — ከላይ በትክክል ተስተካክሏል።",
    "sources": "\n\n---\nምንጮች፦ {sources}"
  },
  "gamification": {
    "xp_earned": "\n\n⭐ +{xp} XP ለዚህ ክፍለ ጊዜ",
    "level_up": "\n🎉 ደረጃ ጨመሩ! አሁን ደረጃ {level}!",
    "xp_quiz": "\n\n⭐ +{xp} XP",
    "level_up_quiz": "\n🎉 ደረጃ ጨመሩ! አሁን ደረጃ {level}!"
  },
  "quiz": {
    "grade_prompt": "የክፍል ደረጃዎን ይምረጡ:",
    "topic_prompt": "{grade}ኛ ክፍል ተመርጧል። ፈተናው ምን ርዕስ ይሸፍን?\n(ለምሳሌ፦ ሴል ባዮሎጂ፣ ዘረመል፣ ኢኮሎጂ)",
    "quiz_type_prompt": "የፈተና አይነት ይምረጡ:",
    "generating": "ፈተናዎን በማዘጋጀት ላይ...",
    "error": "ፈተና በማዘጋጀት ላይ ስህተት ተፈጥሯል።",
    "question": "📝 {title}\n\nጥያቄ {current}/{total}\n<i>{qtype}</i>\n\n{qtext}",
    "correct": "✅ ትክክል!",
    "wrong": "❌ ስህተት። ትክክለኛው መልስ፦ {answer}",
    "short_answer": "\n\n✏️ መልስዎን ከታች ይተይቡ፣ ከዚያ ቀጣይ የሚለውን ይንኩ።",
    "complete": "📊 ፈተና ተጠናቋል!\nውጤት፦ {correct}/{total} ({pct}%)",
    "score": "⭐ በዚህ ፈተና ያገኙት XP፦ {xp}",
    "cancelled": "ፈተና ተሰርዟል።"
  },
  "lesson": {
    "grade_prompt": "የክፍል ደረጃ ይምረጡ:",
    "generating": "የትምህርት እቅድ በማዘጋጀት ላይ...",
    "error": "የትምህርት እቅድ በማዘጋጀት ላይ ስህተት ተፈጥሯል።"
  },
  "settings": {
    "text": "⚙️ የማሳወቂያ ቅንብሮች\n\nየምዕራፍ ማንቂያዎች፦ {milestone}\nየመገምገሚያ አስታዋሾች፦ {reminder}\nየማጠቃለያ ድግግሞሽ፦ {digest}\n\nለመቀየር ይንኩ።"
  },
  "language": {
    "choose": "ቋንቋዎን ይምረጡ:",
    "set": "ቋንቋ ወደ {name} ተቀይሯል!",
    "usage": "አጠቃቀም፦ /language <en|am|both>",
    "set_cmd": "ቋንቋ ወደ {name} ተቀይሯል።"
  },
  "grade": {
    "set": "ነባሪ ክፍል ወደ {grade}ኛ ክፍል ተቀይሯል።",
    "usage": "አጠቃቀም፦ /grade <7-12>"
  },
  "model": {
    "no_models": "ሞዴሎችን ማምጣት አልተቻለም። የ API አገልጋይ እየሰራ ነው?",
    "no_providers": "አቅራቢዎችን ማምጣት አልተቻለም።",
    "refresh_failed": "ሞዴሎችን ማደስ አልተቻለም።",
    "set_failed": "ሞዴል {model} ማዘጋጀት አልተቻለም።",
    "refresh": "🔄 ሞዴሎችን አድስ",
    "back_providers": "← ወደ አቅራቢዎች ተመለስ"
  },
  "progress": {
    "no_weak": "📊 *የእድገት ደረጃ*\n\nምንም ደካማ ርዕሶች አልተገኙም! በሁሉም የትምህርት ዘርፎች ጥሩ እየሰሩ ነው።",
    "need_start": "በመጀመሪያ ለመመዝገብ /start ይጫኑ።"
  },
  "recovery": {
    "no_plans": "📋 *ምንም ንቁ የማገገሚያ እቅዶች የሉም*\n\nደካማ ቦታዎችን ለመለየት ፈተናዎችን ይውሰዱ። የማገገሚያ እቅዶች ፈታኝ ርዕሶችን በደንብ እንዲረዱ ይረዱዎታል።",
    "user_not_found": "❌ ተጠቃሚ አልተገኘም። እባክዎ /start ይጫኑ።",
    "task_not_found": "❌ ተግባር አልተገኘም።",
    "task_done": "✅ ተግባር *{title}* አስቀድሞ ተጠናቋል!"
  },
  "parent": {
    "usage": "አጠቃቀም፦ <code>/parent_register your@email.com</code>\n\nመጀመሪያ በዳሽቦርዱ ላይ የወላጅ አካውንት ያስፈልግዎታል። በዳሽቦርዱ ይመዝገቡ፣ ከዚያ ቴሌግራምዎን እዚህ ያገናኙ።",
    "no_account": "በዚህ ኢሜይል ምንም የወላጅ አካውንት አልተገኘም። በመጀመሪያ በዳሽቦርዱ ላይ እንደ ወላጅ መመዝገብዎን ያረጋግጡ።",
    "already_linked": "ይህ አካውንት አስቀድሞ ከሌላ ቴሌግራም ተጠቃሚ ጋር ተገናኝቷል። እንደገና ማገናኘት ከፈለጉ ድጋፍን ያግኙ።",
    "linked": "ቴሌግራም ተገናኝቷል! የልጆችን እድገት ለማየት /children ይጠቀሙ።",
    "need_register": "በመጀመሪያ በ /parent_register ይመዝገቡ",
    "no_child": "ልጅ አልተገኘም።",
    "no_parent": "የወላጅ አካውንት አልተገኘም።",
    "no_student": "ተማሪ አልተገኘም።"
  }
}
```

- [ ] **Step 4: Add flat keyboard keys from the old TRANSLATIONS dict**

The old `src/telegram/i18n.py` had ~43 flat keys used by `keyboards.py` (e.g., `"ask_question"`, `"take_quiz"`, `"welcome"`, `"back_to_menu"`). These must exist as root-level keys in both JSON files so `keyboards.py` continues to work without changes. Copy ALL keys from the old `TRANSLATIONS["en"]` into `en.json` at root level, and `TRANSLATIONS["am"]` into `am.json`.

The `start.welcome` namespaced key duplicates the existing `"welcome"` flat key — this is intentional. The `start()` handler will migrate to use `t("start.welcome", ...)` while `keyboards.py` still uses `t("welcome", ...)`.

- [ ] **Step 5: Verify both files have identical key structure**

```bash
python3 -c "
import json
with open('src/telegram/messages/en.json') as f:
    en = json.load(f)
with open('src/telegram/messages/am.json') as f:
    am = json.load(f)
def keys(d, prefix=''):
    ks = set()
    for k, v in d.items():
        if isinstance(v, dict):
            ks |= keys(v, f'{prefix}{k}.')
        else:
            ks.add(f'{prefix}{k}')
    return ks
en_keys = keys(en)
am_keys = keys(am)
missing = en_keys - am_keys
extra = am_keys - en_keys
if missing or extra:
    print('MISMATCH:')
    if missing: print(f'  Missing in am: {missing}')
    if extra: print(f'  Extra in am: {extra}')
else:
    print('OK - keys match')
"
```

- [ ] **Step 5: Commit**

```bash
git add src/telegram/messages/
git commit -m "feat(telegram): add i18n message JSON files for bot localization"
```

---

### Task 2: Enhance `i18n.py` for JSON loading + interpolation

**Files:**
- Modify: `src/telegram/i18n.py` (full rewrite — replace TRANSLATIONS dict with JSON loader)
- Create: `tests/test_telegram_i18n.py`

- [ ] **Step 1: Write `src/telegram/i18n.py`**

```python
import json
from pathlib import Path


_messages: dict[str, dict[str, str]] = {}


def _load_messages():
    base = Path(__file__).parent / "messages"
    for lang in ["en", "am"]:
        with open(base / f"{lang}.json") as f:
            _messages[lang] = json.load(f)


def _get(msg: dict, key: str) -> str | None:
    parts = key.split(".")
    for part in parts:
        if not isinstance(msg, dict):
            return None
        msg = msg.get(part)
    return msg if isinstance(msg, str) else None


def t(key: str, lang: str = "en", **kwargs) -> str:
    if not _messages:
        _load_messages()
    val = _get(_messages.get(lang, {}), key)
    if val is None:
        val = _get(_messages.get("en", {}), key)
    if val is None:
        return key
    return val.format(**kwargs) if kwargs else val
```

- [ ] **Step 2: Run tests to verify i18n.py doesn't crash on import**

```bash
cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio\ AI\ Assistant
python3 -c "from src.telegram.i18n import t; print('Import OK')"
```

Expected: `Import OK`

- [ ] **Step 3: Test t() returns correct values**

```bash
cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio\ AI\ Assistant
python3 -c "
from src.telegram.i18n import t
# Backward compatibility with flat keys
assert t('ask_question') == '🧬 Ask a Question', f'Got: {t(\"ask_question\")}'
assert t('ask_question', 'am') == '🧬 ጥያቄ ጠይቅ', f'Got: {t(\"ask_question\", \"am\")}'
# Namespaced keys
assert 'EthioSci AI Assistant' in t('help.text'), f'Got: {t("help.text")}'
assert 'ባዮሎጂ' in t('help.text', 'am'), f'Got: {t(\"help.text\", \"am\")}'
# Interpolation
assert 'Grade 10' in t('tutor.grade_prompt', 'en', grade=10), f'Got: {t(\"tutor.grade_prompt\", \"en\", grade=10)}'
assert '10ኛ' in t('tutor.grade_prompt', 'am', grade=10), f'Got: {t(\"tutor.grade_prompt\", \"am\", grade=10)}'
# Missing key fallback
assert t('nonexistent.key') == 'nonexistent.key'
# Missing lang fallback to English
assert 'Ask a Question' in t('ask_question', 'fr')
print('All assertions passed')
"
```

- [ ] **Step 4: Write unit test file `tests/test_telegram_i18n.py`**

```python
import json
from pathlib import Path

import pytest

from src.telegram.i18n import t, _messages, _get


def _clear_cache():
    _messages.clear()


def test_en_and_am_have_same_keys():
    base = Path(__file__).parent.parent / "src" / "telegram" / "messages"
    with open(base / "en.json") as f:
        en = json.load(f)
    with open(base / "am.json") as f:
        am = json.load(f)

    def extract_keys(d, prefix=""):
        ks = set()
        for k, v in d.items():
            if isinstance(v, dict):
                ks |= extract_keys(v, f"{prefix}{k}.")
            else:
                ks.add(f"{prefix}{k}")
        return ks

    en_keys = extract_keys(en)
    am_keys = extract_keys(am)
    assert en_keys == am_keys, f"Key mismatch. Missing in am: {en_keys - am_keys}. Extra in am: {am_keys - en_keys}"


def test_t_returns_flat_key():
    _clear_cache()
    result = t("ask_question")
    assert "Ask a Question" in result


def test_t_returns_amharic():
    _clear_cache()
    result = t("ask_question", "am")
    assert "ጥያቄ" in result


def test_t_returns_namespaced():
    _clear_cache()
    result = t("help.text")
    assert "EthioSci" in result


def test_t_interpolation():
    _clear_cache()
    result = t("tutor.grade_prompt", "en", grade=7)
    assert "Grade 7" in result


def test_t_missing_key_returns_key():
    _clear_cache()
    result = t("completely.bogus.key")
    assert result == "completely.bogus.key"


def test_t_missing_lang_falls_back_to_english():
    _clear_cache()
    result = t("help.text", "xx")
    assert "EthioSci" in result


def test_get_flat_key():
    d = {"foo": "bar"}
    assert _get(d, "foo") == "bar"


def test_get_nested_key():
    d = {"a": {"b": {"c": "val"}}}
    assert _get(d, "a.b.c") == "val"


def test_get_missing():
    assert _get({}, "x.y") is None
    assert _get({"a": "str"}, "a.b") is None
```

- [ ] **Step 5: Run tests**

```bash
cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio\ AI\ Assistant
python3 -m pytest tests/test_telegram_i18n.py -v
```

Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add src/telegram/i18n.py tests/test_telegram_i18n.py
git commit -m "feat(telegram): enhance i18n with JSON loading, namespaced keys, interpolation"
```

---

### Task 3: Wire translated strings into bot.py — Core & common

**Files:**
- Modify: `src/telegram/bot.py` (replace strings in start, help, cancel, dashboard_login, error handlers)

- [ ] **Step 1: Update `start()` welcome key (line 113)**

Change `t("welcome", _lang(context))` to `t("start.welcome", _lang(context))`:

```python
    await update.message.reply_text(
        t("start.welcome", _lang(context)),
        reply_markup=main_menu_keyboard(socratic, language=_lang(context)),
    )
```

- [ ] **Step 3: Replace `dashboard_login_command` strings (lines 124-127)**

Change:
```python
    await update.message.reply_text(
        f"Your dashboard login code: <b>{code}</b>\n\n"
        "This code expires in 5 minutes. Enter it on the login page.",
        parse_mode="HTML",
    )
```
To:
```python
    await update.message.reply_text(
        t("start.dashboard_login", _lang(context), code=code),
        parse_mode="HTML",
    )
```

- [ ] **Step 4: Replace `help_command` (lines 462-477)**

Replace the entire multi-line string in `help_command` with:
```python
    await update.message.reply_text(
        t("help.text", _lang(context)),
        reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False), language=_lang(context)),
    )
```

- [ ] **Step 5: Replace `cancel` (line 482)**

Change:
```python
    await update.message.reply_text("Cancelled.", ...)
```
To:
```python
    await update.message.reply_text(t("common.cancelled", _lang(context)), ...)
```

- [ ] **Step 6: Replace error strings (lines 751, 753, 571)**

Change:
```python
# line 571 & 751
    await update.message.reply_text("Sorry, I encountered an error.", ...)
```
To:
```python
    await update.message.reply_text(t("common.error", _lang(context)), ...)
```

Change line 753:
```python
    await update.message.reply_text("Usage: /ask <your science question>", ...)
```
To:
```python
    await update.message.reply_text(t("common.usage_ask", _lang(context)), ...)
```

- [ ] **Step 7: Replace "Thinking..." strings (lines 682, 910)**

Change `"Thinking..."` to `t("common.thinking", _lang(context))`

- [ ] **Step 8: Commit**

```bash
git add src/telegram/bot.py
git commit -m "feat(telegram): wire i18n into core handlers (start, help, cancel, errors)"
```

---

### Task 4: Wire translated strings into bot.py — Tutor handler

**Files:**
- Modify: `src/telegram/bot.py` (replace strings in tutor conversation handler)

- [ ] **Step 1: Replace tutor grade_prompt (search for tutor_grade handler)**

Replace the string `f"Grade {grade} selected. Send me your science question..."` with:
```python
t("tutor.grade_prompt", _lang(context), grade=grade)
```

- [ ] **Step 2: Replace no_question error (search for tutor no active question)**

Replace `"No active question. Ask a question first with /ask or select Tutor from the menu."` with:
```python
t("tutor.no_question", _lang(context))
```

- [ ] **Step 3: Replace socratic toggle messages (search for socratic command)**

Replace both socratic on/off messages with:
```python
t("tutor.socratic_on", _lang(context))
t("tutor.socratic_off", _lang(context))
```

- [ ] **Step 4: Replace hint/reveal strings (lines 517, 611, and search for hint_related)**

Replace:
- `"🔍 Revealing the full answer..."` → `t("tutor.revealing_answer", _lang(context))`
- `f"💡 Hint level {next_level}/3..."` → `t("tutor.hint_level", _lang(context), level=next_level)`
- `"The answer has already been revealed..."` → `t("tutor.hint_revealed", _lang(context))`
- `"You've used all hint levels..."` → `t("tutor.hint_exhausted", _lang(context))`

- [ ] **Step 5: Replace misconception and sources strings**

Replace:
- `"\n\n💡 I noticed a misunderstanding..."` → `t("tutor.misconception", _lang(context))`
- `"\n\n---\nSources: " + ", ".join(...)` → format with `t("tutor.sources", _lang(context), sources=", ".join(result["sources"][:3]))`

- [ ] **Step 6: Commit**

```bash
git add src/telegram/bot.py
git commit -m "feat(telegram): wire i18n into tutor handler"
```

---

### Task 5: Wire translated strings into bot.py — Quiz and Lesson handlers

**Files:**
- Modify: `src/telegram/bot.py` (replace strings in quiz and lesson conversation handlers)

- [ ] **Step 1: Replace quiz prompt strings**

Replace:
- `"Select quiz type:"` → `t("quiz.quiz_type_prompt", _lang(context))`
- `"Select your grade level:"` → `t("quiz.grade_prompt", _lang(context))`
- `f"Grade {grade} selected. What topic should the quiz cover?\n(e.g., Cell Biology, Genetics, Ecology)"` → `t("quiz.topic_prompt", _lang(context), grade=grade)`
- `"Generating your quiz..."` → `t("quiz.generating", _lang(context))`
- `"Error generating quiz."` → `t("quiz.error", _lang(context))`

- [ ] **Step 2: Replace quiz question display and feedback (search lines 1127-1148, 1338-1391)**

Replace the quiz question template, correct/wrong feedback, short answer prompt:
```python
# Question display
t("quiz.question", _lang(context), title=title, current=idx+1, total=total, qtype=..., qtext=...)

# Feedback
t("quiz.correct", _lang(context))
t("quiz.wrong", _lang(context), answer=correct_answer)

# Short answer
t("quiz.short_answer", _lang(context))
```

- [ ] **Step 3: Replace quiz complete results and gamification (search lines 1257-1270)**

Replace:
```python
# Complete message
t("quiz.complete", _lang(context), correct=correct, total=total, pct=pct)

# XP feedback
t("gamification.xp_quiz", _lang(context), xp=xp)
t("gamification.level_up_quiz", _lang(context), level=new_level)
```

- [ ] **Step 4: Replace lesson handler strings**

Replace:
- `"Select grade level:"` → `t("lesson.grade_prompt", _lang(context))`
- `"Creating lesson plan..."` → `t("lesson.generating", _lang(context))`
- `"Error creating lesson plan."` → `t("lesson.error", _lang(context))`

- [ ] **Step 5: Commit**

```bash
git add src/telegram/bot.py
git commit -m "feat(telegram): wire i18n into quiz and lesson handlers"
```

---

### Task 6: Wire translated strings into bot.py — Settings, Language, Grade, Model, Recovery, Progress, Parent

**Files:**
- Modify: `src/telegram/bot.py` (replace remaining Phase 1 handler strings)

- [ ] **Step 1: Replace language handler strings**

Replace:
- `"Choose your language:"` → `t("language.choose", _lang(context))`
- `f"Language set to {lang_map[args[0]]}."` → `t("language.set_cmd", _lang(context), name=lang_map[args[0]])`
- `"Usage: /language <en|am|both>"` → `t("language.usage", _lang(context))`

Also replace the callback handler language set:
```python
# Line 1526: .format() → t() with kwargs
t("language.set", _lang(context), name=name)
```

- [ ] **Step 2: Replace grade handler strings**

Replace:
- `f"Default grade set to Grade {grade}."` → `t("grade.set", _lang(context), grade=grade)`
- `"Usage: /grade <7-12>"` → `t("grade.usage", _lang(context))`

- [ ] **Step 3: Replace model handler strings (search lines 1560-1660)**

Replace all error/success messages in model handlers:
```python
t("model.no_models", _lang(context))
t("model.no_providers", _lang(context))
t("model.refresh_failed", _lang(context))
t("model.set_failed", _lang(context), model=model_id)
```

- [ ] **Step 4: Replace settings handler strings (search lines 2034-2097)**

Replace settings display text with:
```python
t("settings.text", _lang(context), milestone=..., reminder=..., digest=...)
```

- [ ] **Step 5: Replace progress and recovery handler strings**

Replace:
- Progress empty state → `t("progress.no_weak", _lang(context))`
- Recovery empty state → `t("recovery.no_plans", _lang(context))`
- Recovery errors → `t("recovery.user_not_found", _lang(context))`, `t("recovery.task_not_found", _lang(context))`, `t("recovery.task_done", _lang(context), title=...)`

- [ ] **Step 6: Replace parent handler strings**

Replace all parent registration/management strings:
```python
t("parent.usage", _lang(context))
t("parent.no_account", _lang(context))
t("parent.already_linked", _lang(context))
t("parent.linked", _lang(context))
t("parent.need_register", _lang(context))
t("parent.no_child", _lang(context))
t("parent.no_parent", _lang(context))
t("parent.no_student", _lang(context))
```

- [ ] **Step 7: Replace gamification feedback strings (search for XP, LEVEL UP patterns)**

Replace the reward feedback in tutor and quiz handlers:
```python
t("gamification.xp_earned", _lang(context), xp=xp_awarded)
t("gamification.level_up", _lang(context), level=new_level)
```

- [ ] **Step 8: Commit**

```bash
git add src/telegram/bot.py
git commit -m "feat(telegram): wire i18n into settings, language, grade, model, recovery, progress, parent handlers"
```

---

### Task 7: Run all tests and verify

**Files:**
- Test: `tests/test_telegram_i18n.py`

- [ ] **Step 1: Run i18n unit tests**

```bash
cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio\ AI\ Assistant
python3 -m pytest tests/test_telegram_i18n.py -v
```

Expected: All tests pass

- [ ] **Step 2: Run lint/typecheck on changed files**

```bash
cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio\ AI\ Assistant
ruff check src/telegram/i18n.py src/telegram/bot.py tests/test_telegram_i18n.py
mypy src/telegram/i18n.py --ignore-missing-imports
```

- [ ] **Step 3: Quick bot import smoke test**

```bash
cd /mnt/data/tcyber/Projects/Tcyberobs/1-Projects/p000-Active/EthioBio\ AI\ Assistant
python3 -c "
from src.telegram.i18n import t
# Test common Phase 1 keys
assert 'እንኳን' in t('start.welcome', 'am')
assert '🔄' in t('model.refresh', 'en')
assert 'ሞዴሎችን' in t('model.refresh', 'am')
assert '⚙️' in t('settings.text', 'en', milestone='ON', reminder='OFF', digest='daily')
assert 'ክፍል' in t('tutor.grade_prompt', 'am', grade=7)
print('All smoke tests passed')
"
```

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "chore: address review feedback on telegram i18n"
```

---

### Task 8: Self-review

- [ ] **Step 1: Verify all keys in `en.json` exist in `am.json`**

Run the key comparison script from Task 1, Step 4.

- [ ] **Step 2: Spot-check 4-5 Phase 1 handlers in bot.py**

For each of `start_command`, `help_command`, tutor grade prompt, quiz complete, and settings display, verify the hardcoded string has been replaced with a `t()` call.

- [ ] **Step 3: Verify the existing keyboard t() still works**

Confirm `src/telegram/keyboards.py` still imports `t` from `i18n.py` and that flat keyboard keys like `"ask_question"` still resolve via the JSON files (they should — they're flat keys at the JSON root from the old TRANSLATIONS dict, which needs to be migrated into JSON too).

**Important check:** The old `TRANSLATIONS` dict in `i18n.py` contained ~43 flat keys used by `keyboards.py` (like `"ask_question"`, `"take_quiz"`, etc.). These keys MUST exist in `en.json` and `am.json` as root-level keys. Verify:

```bash
python3 -c "
import json
with open('src/telegram/messages/en.json') as f:
    en = json.load(f)
# Keys used by keyboards.py
kbd_keys = ['ask_question', 'take_quiz', 'my_progress', 'socratic_on', 'socratic_off',
    'language', 'teacher_tools', 'help', 'next_question', 'reveal_answer',
    'retry_quiz', 'new_quiz', 'main_menu', 'back', 'back_to_menu',
    'create_lesson_plan', 'review_quizzes', 'open_dashboard',
    'broad_hint', 'specific_hint', 'strong_hint', 'end_quiz', 'true', 'false',
    'choose_grade', 'choose_topic', 'choose_quiz_type', 'welcome',
    'loading', 'error_generic', 'choose_language', 'language_set',
    'view_recovery', 'view_progress', 'start_quiz', 'show_hint', 'grade_quiz',
    'cancel', 'confirm', 'yes', 'no']
missing = [k for k in kbd_keys if k not in en]
if missing:
    print(f'MISSING keyboard keys in JSON: {missing}')
else:
    print('All keyboard keys present in JSON')
"
```

If any are missing, add them to both `en.json` and `am.json` as root-level keys.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix(telegram): ensure all keyboard translation keys present in JSON"
```
