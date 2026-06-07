# Telegram Bot Amharic Localization — Design

## Status: Approved

## Problem

The Telegram bot (`src/telegram/bot.py`) has hardcoded English strings across all ~40 handler functions. While the `User` model already stores `language_preference` (`en`/`am`/`both`) and keyboard labels are already i18n'd, response text (help, tutor output, quiz, settings, gamification, errors, etc.) is untranslated.

Phased approach:
- **Phase 1** (~120 keys): Core flows — start, help, tutor, quiz, settings, language, errors, gamification
- **Phase 2** (~50 keys): Progress, recovery, socratic, models
- **Phase 3** (~30 keys): Admin/teacher/parent features, edge cases

## Architecture

### Message Files

`src/telegram/messages/en.json` and `src/telegram/messages/am.json` — namespaced JSON with dot-notation keys:

```json
{
  "common": {
    "error": "Sorry, I encountered an error. Please try again.",
    "cancelled": "Cancelled."
  },
  "start": {
    "welcome": "...",
    "returning": "..."
  },
  "help": {
    "title": "..."
  },
  "tutor": {
    "grade_prompt": "Grade {grade} selected. Send me your biology question.",
    "no_question": "No active question..."
  },
  "quiz": {
    "correct": "✅ Correct!",
    "wrong": "❌ Wrong. The answer was: {answer}",
    "complete": "📊 Quiz Complete!\nScore: {correct}/{total} ({pct}%)"
  },
  "gamification": {
    "xp_earned": "\n\n⭐ +{xp} XP for this session",
    "level_up": "\n🎉 LEVEL UP! You are now Level {level}!"
  }
}
```

### Translation Function (`src/telegram/i18n.py`)

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

**Fallback chain**: requested language → English → raw key name (debug-friendly).

### Keyboard Labels Migration

Existing keyboard labels in `keyboards.py` use a separate `t()` from `i18n.py`. Migrate them to import and use the enhanced `t()` from `i18n.py` so there's one source of truth.

## Handler Changes (Mechanical Pattern)

**Before:**
```python
await update.message.reply_text(f"Grade {grade} selected. Send me your biology question.")
```

**After:**
```python
await update.message.reply_text(
    t("tutor.grade_prompt", _lang(context), grade=grade)
)
```

Each string replacement is 1-3 lines. Phase 1 touches ~15 handlers.

## Language Retrieval

Already exists: `_lang(context)` returns `context.user_data.get("language", "en")`. No change needed.

## Files Changed

| File | Change |
|------|--------|
| `src/telegram/i18n.py` | Add JSON loading, namespaced `_get()`, interpolation |
| `src/telegram/messages/en.json` | New — all Phase 1 English strings |
| `src/telegram/messages/am.json` | New — Amharic translations |
| `src/telegram/keyboards.py` | No change needed — already imports `t` from `i18n.py` |
| `src/telegram/bot.py` | ~15 handlers, replace hardcoded strings with `t()` calls |

## Testing

- Unit test: verify `en.json` and `am.json` have identical key sets
- Unit test: `t("start.welcome", "en")` returns string, `t("start.welcome", "am")` returns Amharic string
- Unit test: `t("nonexistent.key", "en")` returns key name
- Unit test: `t("tutor.grade_prompt", "en", grade=10)` returns string with grade interpolated
- No handler-level integration tests needed (pure string replacement)
