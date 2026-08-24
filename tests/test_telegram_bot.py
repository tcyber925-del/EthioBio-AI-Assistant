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


def test_format_progress_overview_renders_stats_and_bars():
    gam = SimpleNamespace(total_xp=1250, level=3, current_streak=4, longest_streak=9)
    quizzes = [SimpleNamespace(score=70.0), SimpleNamespace(score=80.0)]
    masteries = [
        SimpleNamespace(topic="Cell Biology", average_score=82.0),
        SimpleNamespace(topic="Evolution", average_score=30.0),
    ]
    text = bot._format_progress_overview(
        {"gam": gam, "recent_quizzes": quizzes, "mastery_records": masteries}
    )
    assert "75%" in text
    assert "Cell Biology" in text
    assert "82%" in text
    assert "Focus next" in text
    assert "Evolution" in text
    assert "<b>" in text


def test_format_progress_overview_escapes_topics_and_defaults_gamification():
    masteries = [SimpleNamespace(topic="Cells <&> DNA", average_score=50.0)]
    text = bot._format_progress_overview(
        {"gam": None, "recent_quizzes": [], "mastery_records": masteries}
    )
    assert "Cells &lt;&amp;&gt; DNA" in text
    assert "Level 1" in text
    assert "0 XP" in text


def test_format_progress_overview_empty_data_renders_zeroed_header():
    text = bot._format_progress_overview({"gam": None, "recent_quizzes": [], "mastery_records": []})
    assert "Readiness" in text
    assert "0%" in text
    assert "Focus next" not in text


def test_format_progress_overview_clamps_out_of_range_scores():
    masteries = [
        SimpleNamespace(topic="Too Low", average_score=-20.0),
        SimpleNamespace(topic="Too High", average_score=150.0),
    ]
    text = bot._format_progress_overview(
        {"gam": None, "recent_quizzes": [], "mastery_records": masteries}
    )
    assert "0%" in text
    assert "100%" in text


def test_format_progress_overview_treats_null_score_as_zero():
    quizzes = [SimpleNamespace(score=None)]
    text = bot._format_progress_overview(
        {"gam": None, "recent_quizzes": quizzes, "mastery_records": []}
    )
    assert "0%" in text


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
async def test_handle_language_replies_new_message():
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(answer=AsyncMock(), message=message)
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={})

    await bot.handle_language(update, context)

    query.message.reply_text.assert_awaited()
    assert "choose your language" in query.message.reply_text.await_args.args[0].lower()


def _db_result(scalar=None, scalars=None):
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar
    inner = MagicMock()
    inner.all.return_value = scalars or []
    r.scalars.return_value = inner
    return r


def _progress_session_mock(side_effects):
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.execute = AsyncMock(side_effect=side_effects)
    return MagicMock(return_value=mock_session)


@pytest.mark.asyncio
async def test_handle_progress_shows_onboarding_for_zero_data_user(monkeypatch):
    user = SimpleNamespace(id="u1")
    monkeypatch.setattr(
        bot,
        "async_session_factory",
        MagicMock(
            return_value=_progress_session_mock(
                [
                    _db_result(scalar=user),
                    _db_result(scalar=None),
                    _db_result(scalars=[]),
                    _db_result(scalars=[]),
                ]
            )
        ),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock(), message=message)
    update = SimpleNamespace(callback_query=query)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.handle_progress(update, context)

    kwargs = query.edit_message_text.await_args.kwargs
    assert "first quiz" in query.edit_message_text.await_args.args[0]
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_handle_progress_shows_overview_for_returning_user(monkeypatch):
    user = SimpleNamespace(id="u1")
    gam = SimpleNamespace(total_xp=500, level=2, current_streak=2, longest_streak=5)
    monkeypatch.setattr(
        bot,
        "async_session_factory",
        MagicMock(
            return_value=_progress_session_mock(
                [
                    _db_result(scalar=user),
                    _db_result(scalar=gam),
                    _db_result(scalars=[SimpleNamespace(score=60.0)]),
                    _db_result(scalars=[SimpleNamespace(topic="Genetics", average_score=55.0)]),
                ]
            )
        ),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock(), message=message)
    update = SimpleNamespace(callback_query=query)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.handle_progress(update, context)

    assert "Readiness" in query.edit_message_text.await_args.args[0]


@pytest.mark.asyncio
async def test_handle_progress_falls_back_to_reply_when_edit_fails(monkeypatch):
    user = SimpleNamespace(id="u1")
    gam = SimpleNamespace(total_xp=500, level=2, current_streak=2, longest_streak=5)
    monkeypatch.setattr(
        bot,
        "async_session_factory",
        MagicMock(
            return_value=_progress_session_mock(
                [
                    _db_result(scalar=user),
                    _db_result(scalar=gam),
                    _db_result(scalars=[SimpleNamespace(score=60.0)]),
                    _db_result(scalars=[SimpleNamespace(topic="Genetics", average_score=55.0)]),
                ]
            )
        ),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(
        answer=AsyncMock(),
        edit_message_text=AsyncMock(side_effect=Exception("message not modified")),
        message=message,
    )
    update = SimpleNamespace(callback_query=query)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.handle_progress(update, context)

    kwargs = message.reply_text.await_args.kwargs
    assert "Readiness" in message.reply_text.await_args.args[0]
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_handle_progress_onboarding_offers_take_quiz_button(monkeypatch):
    user = SimpleNamespace(id="u1")
    monkeypatch.setattr(
        bot,
        "async_session_factory",
        MagicMock(
            return_value=_progress_session_mock(
                [
                    _db_result(scalar=user),
                    _db_result(scalar=None),
                    _db_result(scalars=[]),
                    _db_result(scalars=[]),
                ]
            )
        ),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock(), message=message)
    update = SimpleNamespace(callback_query=query)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.handle_progress(update, context)

    markup = query.edit_message_text.await_args.kwargs["reply_markup"]
    callbacks = [btn.callback_data for row in markup.inline_keyboard for btn in row]
    assert callbacks == ["quiz"]


@pytest.mark.asyncio
async def test_handle_progress_need_start_when_unregistered(monkeypatch):
    monkeypatch.setattr(
        bot,
        "async_session_factory",
        MagicMock(return_value=_progress_session_mock([_db_result(scalar=None)])),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock(), message=message)
    update = SimpleNamespace(callback_query=query)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.handle_progress(update, context)

    assert "/start" in query.edit_message_text.await_args.args[0]


@pytest.mark.asyncio
async def test_progress_command_sends_overview(monkeypatch):
    user = SimpleNamespace(id="u1")
    gam = SimpleNamespace(total_xp=100, level=1, current_streak=1, longest_streak=1)
    monkeypatch.setattr(
        bot,
        "async_session_factory",
        MagicMock(
            return_value=_progress_session_mock(
                [
                    _db_result(scalar=user),
                    _db_result(scalar=gam),
                    _db_result(scalars=[SimpleNamespace(score=50.0)]),
                    _db_result(scalars=[SimpleNamespace(topic="Genetics", average_score=55.0)]),
                ]
            )
        ),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(message=message)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.progress_command(update, context)

    kwargs = message.reply_text.await_args.kwargs
    assert "Readiness" in message.reply_text.await_args.args[0]
    assert kwargs["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_progress_command_empty_state_for_zero_data_user(monkeypatch):
    user = SimpleNamespace(id="u1")
    monkeypatch.setattr(
        bot,
        "async_session_factory",
        MagicMock(
            return_value=_progress_session_mock(
                [
                    _db_result(scalar=user),
                    _db_result(scalar=None),
                    _db_result(scalars=[]),
                    _db_result(scalars=[]),
                ]
            )
        ),
    )
    message = SimpleNamespace(reply_text=AsyncMock())
    update = SimpleNamespace(message=message)
    update.effective_user = SimpleNamespace(id=12345)
    context = SimpleNamespace(user_data={})

    await bot.progress_command(update, context)

    assert "first quiz" in message.reply_text.await_args.args[0]
