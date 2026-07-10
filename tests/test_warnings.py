import importlib
import warnings

from src.api import graph
from src.config import settings
from src.schemas import chat
from src.telegram import bot


def _warning_messages(captured):
    return [str(item.message) for item in captured]


def test_schema_modules_do_not_emit_protected_namespace_warnings():
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        importlib.reload(chat)
        importlib.reload(graph)

    messages = _warning_messages(captured)
    assert not any("protected namespace" in message for message in messages)


def test_build_app_does_not_emit_unexpected_warnings(monkeypatch):
    monkeypatch.setattr(settings, "telegram_bot_token", "123456:TESTTOKEN")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        app = bot.build_app()

    messages = _warning_messages(captured)
    unexpected = [m for m in messages if "per_message" not in m]
    assert not unexpected, f"Unexpected warnings: {unexpected}"

    handler_types = {
        type(handler).__name__ for handlers in app.handlers.values() for handler in handlers
    }
    assert "CommandHandler" in handler_types
    assert "ConversationHandler" in handler_types
