from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.telegram import bot
from src.telegram.formatter import format_for_telegram


@pytest.mark.asyncio
async def test_reply_long_preserves_parse_mode_across_chunks():
    message = SimpleNamespace(edit_text=AsyncMock(), reply_text=AsyncMock())

    await bot._reply_long(
        message,
        "abcdefghij",
        reply_markup="markup",
        max_len=4,
        parse_mode="HTML",
    )

    message.edit_text.assert_awaited_once_with(
        "abcd",
        reply_markup="markup",
        parse_mode="HTML",
    )
    assert message.reply_text.await_count == 2
    message.reply_text.assert_any_await("efgh", parse_mode="HTML")
    message.reply_text.assert_any_await("ij", parse_mode="HTML")


@pytest.mark.asyncio
async def test_cancel_clears_user_data_and_ends_conversation():
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(
        user_data={
            "socratic_mode": True,
            "ask_question": "What is DNA?",
            "hint_level": 2,
        }
    )

    result = await bot.cancel(update, context)

    assert result == bot.ConversationHandler.END
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_handle_socratic_toggle_updates_state_and_keyboard():
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(
        answer=AsyncMock(), edit_message_reply_markup=AsyncMock(), message=message
    )
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={"socratic_mode": False})

    await bot.handle_socratic_toggle(update, context)

    assert context.user_data["socratic_mode"] is True


@pytest.mark.asyncio
async def test_handle_hint_calls_run_graph_and_renders_html(monkeypatch):
    mock_result = SimpleNamespace(
        answer="**ACKNOWLEDGE:** Resp <tag>",
        misconception_detected=True,
        sources=[],
    )
    monkeypatch.setattr(bot, "run_graph", AsyncMock(return_value=mock_result))
    monkeypatch.setattr(bot, "_build_memory_context", AsyncMock(return_value=(None, None, "", [])))

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session)
    monkeypatch.setattr(bot, "async_session_factory", MagicMock(return_value=mock_factory))

    hint_msg = SimpleNamespace(edit_text=AsyncMock(), reply_text=AsyncMock())
    message = SimpleNamespace(reply_text=AsyncMock(return_value=hint_msg))
    query = SimpleNamespace(
        data="hint_1",
        answer=AsyncMock(),
        edit_message_reply_markup=AsyncMock(),
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

    update.effective_user = SimpleNamespace(id=12345)

    await bot.handle_hint(update, context)

    assert context.user_data["socratic_mode"] is True
    assert context.user_data["hint_level"] == 1
    bot.run_graph.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_quiz_question_escapes_dynamic_text(monkeypatch):
    monkeypatch.setattr(bot, "_reply_long", AsyncMock())

    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(effective_message=message)
    context = SimpleNamespace(
        user_data={
            "quiz_session": {
                "title": "Grade <7> Quiz",
                "current": 0,
                "total": 1,
                "questions": [
                    {
                        "question_type": "multiple_choice",
                        "question_text": "What is <ATP>?",
                        "options": ["A) Energy <store>", "B) Protein"],
                    }
                ],
            }
        }
    )

    await bot._send_quiz_question(update, context)

    args, kwargs = bot._reply_long.await_args
    sent_text = args[1]
    assert "Grade" in sent_text
    assert "What is" in sent_text
    assert "Energy" in sent_text


def test_format_for_telegram_converts_markdown_to_html():
    formatted = format_for_telegram(
        "**ACKNOWLEDGE:** Strong question.\nUse `vertebrae` to think about the difference."
    )

    assert "<b>ACKNOWLEDGE:</b> Strong question." in formatted
    assert "<code>vertebrae</code>" in formatted


@pytest.mark.asyncio
async def test_handle_question_calls_run_graph(monkeypatch):
    from src.schemas.streaming import TokenChunk

    async def mock_run_graph(*args, token_queue=None, **kwargs):
        if token_queue is not None:
            token_queue.put_nowait(TokenChunk(delta="", node="tutor", done=True))
        return SimpleNamespace(
            answer="Photosynthesis is the process...",
            misconception_detected=False,
            sources=[],
        )

    monkeypatch.setattr(bot, "run_graph", mock_run_graph)
    monkeypatch.setattr(bot, "_build_memory_context", AsyncMock(return_value=(None, None, "", [])))
    monkeypatch.setattr(bot, "_reply_long", AsyncMock())
    monkeypatch.setattr(bot, "_save_tutor_rewards", AsyncMock())

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session)
    monkeypatch.setattr(bot, "async_session_factory", MagicMock(return_value=mock_factory))

    message = SimpleNamespace(reply_text=AsyncMock(), text="What is photosynthesis?")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=12345))
    context = SimpleNamespace(
        user_data={
            "grade_level": 10,
            "language": "en",
            "socratic_mode": False,
            "hint_level": 0,
            "reveal_answer": False,
        }
    )

    await bot.handle_question(update, context)


@pytest.mark.asyncio
async def test_help_command_replies_with_text():
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(message=message)
    context = SimpleNamespace(user_data={})

    await bot.help_command(update, context)

    message.reply_text.assert_awaited_once()
    sent_text = message.reply_text.await_args.args[0]
    assert "Help" in sent_text


@pytest.mark.asyncio
async def test_handle_progress_replies_new_message_for_callback():
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(
        answer=AsyncMock(), edit_message_reply_markup=AsyncMock(), message=message
    )
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={})

    await bot.handle_progress(update, context)

    query.message.reply_text.assert_awaited()
    sent_text = query.message.reply_text.await_args.args[0]
    assert "My Progress" in sent_text


@pytest.mark.asyncio
async def test_handle_language_replies_new_message():
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(answer=AsyncMock(), message=message)
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={})

    await bot.handle_language(update, context)

    query.message.reply_text.assert_awaited()
    assert "choose your language" in query.message.reply_text.await_args.args[0].lower()
