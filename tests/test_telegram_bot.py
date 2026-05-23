from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.constants import ParseMode

from src.telegram import bot


class DummyRouter:
    def __init__(self):
        self.close = AsyncMock()


class DummyTutorAgent:
    def __init__(self, llm_router, retriever=None):
        self.answer = AsyncMock(
            return_value={
                "answer": "**ACKNOWLEDGE:** Resp <tag>",
                "sources": ["Cell <Bio>"],
                "misconception_detected": True,
            }
        )


@pytest.mark.asyncio
async def test_reply_long_preserves_parse_mode_across_chunks():
    message = SimpleNamespace(edit_text=AsyncMock(), reply_text=AsyncMock())

    await bot._reply_long(
        message,
        "abcdefghij",
        reply_markup="markup",
        max_len=4,
        parse_mode=ParseMode.HTML,
    )

    message.edit_text.assert_awaited_once_with(
        "abcd",
        reply_markup="markup",
        parse_mode=ParseMode.HTML,
    )
    assert message.reply_text.await_count == 2
    message.reply_text.assert_any_await("efgh", parse_mode=ParseMode.HTML)
    message.reply_text.assert_any_await("ij", parse_mode=ParseMode.HTML)


@pytest.mark.asyncio
async def test_cancel_preserves_socratic_mode_but_clears_transient_state():
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(
        user_data={
            "socratic_mode": True,
            "ask_question": "What is DNA?",
            "hint_level": 2,
            "reveal_answer": True,
            "tutor_grade": 9,
        }
    )

    result = await bot.cancel(update, context)

    assert result == bot.ConversationHandler.END
    assert context.user_data == {"socratic_mode": True}
    markup = message.reply_text.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[3][0].text == "🧠 Socratic: ON"


@pytest.mark.asyncio
async def test_handle_socratic_toggle_updates_state_and_keyboard():
    query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock())
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={"socratic_mode": False})

    await bot.handle_socratic_toggle(update, context)

    assert context.user_data["socratic_mode"] is True
    markup = query.edit_message_text.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[3][0].text == "🧠 Socratic: ON"


@pytest.mark.asyncio
async def test_handle_hint_keeps_socratic_mode_and_renders_html(monkeypatch):
    monkeypatch.setattr(bot, "ModelRouter", DummyRouter)
    monkeypatch.setattr(bot, "TutorAgent", DummyTutorAgent)

    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(
        data="hint_1",
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
        message=message,
    )
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(
        user_data={
            "socratic_mode": True,
            "ask_question": "What is photosynthesis?",
            "hint_level": 0,
            "reveal_answer": False,
            "grade_level": 7,
            "language": "en",
        }
    )

    await bot.handle_hint(update, context)

    assert context.user_data["socratic_mode"] is True
    assert context.user_data["hint_level"] == 1
    message.reply_text.assert_awaited()
    assert message.reply_text.await_args.kwargs["parse_mode"] == ParseMode.HTML
    sent_text = message.reply_text.await_args.args[0]
    assert "<b>ACKNOWLEDGE:</b> Resp &lt;tag&gt;" in sent_text
    assert "<b>Sources:</b> Cell &lt;Bio&gt;" in sent_text


def test_format_quiz_question_escapes_dynamic_text():
    session = {"title": "Grade <7> Quiz", "current": 0, "total": 1}
    question = {
        "question_type": "multiple_choice",
        "question_text": "What is <ATP>?",
        "options": ["A) Energy <store>", "B) Protein"],
    }

    formatted = bot._format_quiz_question(session, question)

    assert "<b>Grade &lt;7&gt; Quiz</b>" in formatted
    assert "What is &lt;ATP&gt;?" in formatted
    assert "A) Energy &lt;store&gt;" in formatted


def test_render_llm_html_converts_basic_markdown_to_html():
    formatted = bot._render_llm_html(
        "**ACKNOWLEDGE:** Strong question.\nUse `vertebrae` to think about the difference."
    )

    assert "<b>ACKNOWLEDGE:</b> Strong question." in formatted
    assert "<code>vertebrae</code>" in formatted


@pytest.mark.asyncio
async def test_handle_text_input_routes_by_input_mode(monkeypatch):
    routed = []

    async def fake_quiz_topic(update, context):
        routed.append("quiz_topic")

    monkeypatch.setattr(bot, "handle_quiz_topic", fake_quiz_topic)

    update = SimpleNamespace(message=SimpleNamespace(text="Cell Biology"))
    context = SimpleNamespace(user_data={"input_mode": "quiz_topic"})

    await bot.handle_text_input(update, context)

    assert routed == ["quiz_topic"]


@pytest.mark.asyncio
async def test_help_command_uses_html_formatting():
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(user_data={})

    await bot.help_command(update, context)

    assert message.reply_text.await_args.kwargs["parse_mode"] == ParseMode.HTML
    sent_text = message.reply_text.await_args.args[0]
    assert "<b>EthioBio AI Assistant Help</b>" in sent_text
    assert "<b>Commands</b>" in sent_text


@pytest.mark.asyncio
async def test_handle_progress_uses_html_formatting_for_callback():
    query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock())
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={})

    await bot.handle_progress(update, context)

    assert query.edit_message_text.await_args.kwargs["parse_mode"] == ParseMode.HTML
    sent_text = query.edit_message_text.await_args.args[0]
    assert "<b>📊 My Progress</b>" in sent_text


@pytest.mark.asyncio
async def test_handle_language_uses_html_formatting():
    query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock())
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={})

    await bot.handle_language(update, context)

    assert query.edit_message_text.await_args.kwargs["parse_mode"] == ParseMode.HTML
    assert "<b>Choose Your Language</b>" in query.edit_message_text.await_args.args[0]
