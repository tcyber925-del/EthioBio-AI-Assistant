import httpx
import structlog
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.agents.lesson_planner import LessonPlannerAgent
from src.agents.quiz import QuizAgent
from src.agents.tutor import TutorAgent
from src.api.gamification import award_xp, update_streak
from src.config import settings
from src.database.models import StudentProfile, User, UserRole
from src.database.session import async_session_factory
from src.llm.router import ModelRouter
from src.telegram.formatter import format_for_telegram, sanitize_for_telegram, strip_markdown
from src.telegram.keyboards import (
    answer_options_keyboard,
    back_keyboard,
    grade_keyboard,
    hint_keyboard,
    language_keyboard,
    main_menu_keyboard,
    model_selection_keyboard,
    quiz_next_keyboard,
    quiz_result_keyboard,
    quiz_type_keyboard,
    teacher_tools_keyboard,
    tf_keyboard,
)
from telegram import InlineKeyboardMarkup, Update

logger = structlog.get_logger()

TUTOR, QUIZ_TYPE, QUIZ_GRADE, QUIZ_TOPIC, QUIZ_ANSWERING, LESSON_GRADE, LESSON_TOPIC, TUTOR_GRADE = range(8)


async def _db_try(action, fallback=None):
    import asyncio
    try:
        return await asyncio.wait_for(action(), timeout=5.0)
    except Exception as e:
        logger.warning("db_skipped", error=str(e))
        return fallback


async def _try_register_user(telegram_id: int):
    from sqlalchemy import select
    async def _register():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if not user:
                user = User(telegram_id=telegram_id, role=UserRole.student, language_preference="en")
                session.add(user)
                await session.flush()
                profile = StudentProfile(user_id=user.id)
                session.add(profile)
                await session.commit()
    await _db_try(_register)


async def start(update: Update, context):
    await _try_register_user(update.effective_user.id)
    socratic = context.user_data.get("socratic_mode", False)
    await update.message.reply_text(
        "Welcome to EthioBio AI Assistant!\n\n"
        "I'm your biology learning assistant for Ethiopian Grades 7-12.\n\n"
        "Send me any biology question, or use the menu below:",
        reply_markup=main_menu_keyboard(socratic),
    )


async def help_command(update: Update, context):
    await update.message.reply_text(
        "EthioBio AI Assistant — Help\n\n"
        "Commands:\n"
        "/start — Show menu\n"
        "/help — This message\n"
        "/ask <question> — Ask a biology question\n"
        "/quiz [grade] [topic] — Generate a quiz\n"
        "/grade <7-12> — Set your default grade\n"
        "/language <en|am|both> — Set language\n"
        "/socratic — Toggle Socratic tutoring mode\n"
        "/hint — Get the next hint level (1-3) in Socratic mode\n"
        "/cancel — Cancel current operation\n\n"
        "Or just type any biology question to get started!",
        reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
    )


async def cancel(update: Update, context):
    context.user_data.clear()
    await update.message.reply_text("Cancelled.", reply_markup=main_menu_keyboard())
    return ConversationHandler.END


async def grade_command(update: Update, context):
    args = context.args
    if args and args[0].isdigit():
        grade = int(args[0])
        if 7 <= grade <= 12:
            context.user_data["grade_level"] = grade
            await update.message.reply_text(f"Default grade set to Grade {grade}.")
            return
    await update.message.reply_text("Usage: /grade <7-12>", reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)))


async def language_command(update: Update, context):
    args = context.args
    lang_map = {"en": "English", "am": "Amharic", "both": "Bilingual"}
    if args and args[0] in lang_map:
        context.user_data["language"] = args[0]
        await update.message.reply_text(f"Language set to {lang_map[args[0]]}.")
    else:
        await update.message.reply_text("Usage: /language <en|am|both>", reply_markup=language_keyboard())


async def reveal_command(update: Update, context):
    question = context.user_data.get("ask_question", "")
    if not question:
        await update.message.reply_text(
            "No active question. Ask a question first with /ask or select Tutor from the menu.",
            reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
        )
        return
    hint_level = context.user_data.get("hint_level", 0)
    context.user_data["reveal_answer"] = True
    await update.message.reply_text("🔍 Revealing the full answer...")
    try:
        router_llm = ModelRouter()
        agent = TutorAgent(llm_router=router_llm, retriever=None)
        result = await agent.answer(
            question=question, user_id=None, use_rag=True,
            grade_level=context.user_data.get("grade_level"),
            language=context.user_data.get("language", "en"),
            socratic_mode=False,
            hint_level=hint_level,
            reveal_answer=True,
        )
        attempt_msg = f"\n\n📊 You used {hint_level} hint(s) before revealing the answer." if hint_level > 0 else "\n\n📊 You revealed the answer without using hints."
        response = result["answer"] + attempt_msg
        await _reply_long(
            update.message, response,
            reply_markup=hint_keyboard(hint_level, True),
            parse_mode="HTML",
        )
        await router_llm.close()
    except Exception as e:
        logger.error("reveal_command_error", error=str(e))
        await update.message.reply_text(
            "Sorry, I encountered an error.",
            reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
        )


async def socratic_command(update: Update, context):
    current = context.user_data.get("socratic_mode", False)
    context.user_data["socratic_mode"] = not current
    status = "ON 🧠" if context.user_data["socratic_mode"] else "OFF"
    await update.message.reply_text(
        f"Socratic Mode is now {status}.\n\n"
        "In Socratic mode, I'll guide you with questions rather than giving direct answers.",
        reply_markup=main_menu_keyboard(context.user_data["socratic_mode"]),
    )


async def hint_command(update: Update, context):
    hint_level = context.user_data.get("hint_level", 0)
    reveal = context.user_data.get("reveal_answer", False)
    if reveal:
        await update.message.reply_text(
            "The answer has already been revealed! Ask a new question to continue.",
            reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
        )
        return
    next_level = hint_level + 1
    if next_level > 3:
        await update.message.reply_text(
            "You've used all hint levels. Tap 'Reveal Answer' to see the full explanation.",
            reply_markup=hint_keyboard(hint_level, reveal),
        )
        return
    context.user_data["hint_level"] = next_level
    question = context.user_data.get("ask_question", "")
    if not question:
        await update.message.reply_text(
            "No active question. Ask a question first with /ask or select Tutor from the menu.",
            reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
        )
        return
    await update.message.reply_text(f"💡 Hint level {next_level}/3...")
    try:
        router_llm = ModelRouter()
        agent = TutorAgent(llm_router=router_llm, retriever=None)
        result = await agent.answer(
            question=question, user_id=None, use_rag=True,
            grade_level=context.user_data.get("grade_level"),
            language=context.user_data.get("language", "en"),
            socratic_mode=context.user_data.get("socratic_mode", True),
            hint_level=next_level,
            reveal_answer=False,
        )
        response = result["answer"]
        if result.get("misconception_detected"):
            response += "\n\n💡 I noticed a misunderstanding — gently corrected above."
        await _reply_long(
            update.message, response,
            reply_markup=hint_keyboard(next_level, False),
            parse_mode="HTML",
        )
        await router_llm.close()
    except Exception as e:
        logger.error("hint_command_error", error=str(e))
        await update.message.reply_text(
            "Sorry, I encountered an error.",
            reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
        )


async def ask_command(update: Update, context):
    question = " ".join(context.args) if context.args else ""
    if question:
        context.user_data["ask_question"] = question
        context.user_data["hint_level"] = 0
        context.user_data["reveal_answer"] = False
        await update.message.reply_text("Thinking...")
        try:
            router_llm = ModelRouter()
            agent = TutorAgent(llm_router=router_llm, retriever=None)
            socratic = context.user_data.get("socratic_mode", False)
            result = await agent.answer(
                question=question, user_id=None, use_rag=True,
                grade_level=context.user_data.get("grade_level"),
                language=context.user_data.get("language", "en"),
                socratic_mode=socratic,
            )
            response = result["answer"]
            if result.get("misconception_detected"):
                response += "\n\n💡 I noticed a misunderstanding — gently corrected above."
            if result.get("sources"):
                response += "\n\n---\nSources: " + ", ".join(result["sources"][:3])
            reply_markup = hint_keyboard(0, False) if socratic else main_menu_keyboard(socratic)
            await _reply_long(update.message, response, reply_markup=reply_markup, parse_mode="HTML")
            await router_llm.close()
        except Exception as e:
            logger.error("ask_command_error", error=str(e))
            await update.message.reply_text("Sorry, I encountered an error.", reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)))
    else:
        await update.message.reply_text("Usage: /ask <your biology question>", reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)))


async def quiz_command(update: Update, context):
    args = context.args
    grade = context.user_data.get("grade_level", 10)
    topic = "Biology"
    if args:
        if args[0].isdigit():
            grade = int(args[0])
            topic = " ".join(args[1:]) if args[1:] else topic
        else:
            topic = " ".join(args)
    if 7 <= grade <= 12:
        context.user_data["quiz_grade"] = grade
        await update.message.reply_text("Select quiz type:", reply_markup=quiz_type_keyboard())
        return QUIZ_TYPE
    else:
        await update.message.reply_text("Usage: /quiz [grade] [topic]", reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)))
        return ConversationHandler.END


async def menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await query.message.reply_text("Choose an option:", reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)))


async def handle_teacher_tools(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Teacher Tools:", reply_markup=teacher_tools_keyboard())


async def handle_open_quizzes(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📄 Review Quizzes\n\n"
        "Open the Teacher Dashboard in your browser:\n"
        "http://localhost:3000/quizzes\n\n"
        "The dashboard shows all generated quizzes for review and approval.",
        reply_markup=teacher_tools_keyboard(),
    )


async def handle_open_dashboard(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📈 Teacher Dashboard\n\n"
        "Open in your browser:\n"
        "http://localhost:3000\n\n"
        "Features:\n"
        "• 📊 Stats overview\n"
        "• 📝 Quiz management\n"
        "• 📋 Lesson plans\n"
        "• 📈 Monitoring\n"
        "• 🧬 Test Q&A",
        reply_markup=teacher_tools_keyboard(),
    )


async def handle_tutor(update: Update, context):
    if update.callback_query:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass
        await query.message.reply_text(
            "Select your grade level:",
            reply_markup=grade_keyboard("tutor_grade"),
        )
    else:
        await update.message.reply_text(
            "Select your grade level:",
            reply_markup=grade_keyboard("tutor_grade"),
        )
    return TUTOR_GRADE


async def handle_tutor_grade(update: Update, context):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    grade = int(query.data.split("_")[-1])
    context.user_data["tutor_grade"] = grade
    await query.edit_message_text(
        f"Grade {grade} selected. Send me your biology question. I'll help you understand it!",
        reply_markup=back_keyboard(),
    )
    return TUTOR


async def end_conversation(update: Update, context):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await query.message.reply_text("Choose an option:", reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)))
    return ConversationHandler.END


async def handle_question(update: Update, context):
    question = update.message.text
    context.user_data["ask_question"] = question
    context.user_data["hint_level"] = 0
    context.user_data["reveal_answer"] = False
    thinking_msg = await update.message.reply_text("Thinking...")

    result = None
    try:
        router_llm = ModelRouter()
        agent = TutorAgent(llm_router=router_llm, retriever=None)
        socratic = context.user_data.get("socratic_mode", False)
        hint_level = context.user_data.get("hint_level", 0)
        reveal = context.user_data.get("reveal_answer", False)
        result = await agent.answer(
            question=question, user_id=None, use_rag=True,
            grade_level=context.user_data.pop("tutor_grade", None) or context.user_data.get("grade_level"),
            language=context.user_data.get("language", "en"),
            socratic_mode=socratic,
            hint_level=hint_level,
            reveal_answer=reveal,
        )
        response = result["answer"]
        if result.get("misconception_detected"):
            response += "\n\n💡 I noticed a misunderstanding — gently corrected above."
        if result.get("sources"):
            response += "\n\n---\nSources: " + ", ".join(result["sources"][:3])
        reply_markup = hint_keyboard(hint_level, reveal) if socratic else main_menu_keyboard(socratic)
        await _reply_long(thinking_msg, response, reply_markup=reply_markup, parse_mode="HTML")
        await router_llm.close()
    except Exception as e:
        logger.error("tutor_error", error=str(e))
        try:
            await thinking_msg.edit_text(
                "Sorry, I encountered an error. Please try again.",
                reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
            )
        except Exception:
            pass
        return ConversationHandler.END

    from src.database.models import MessageThread
    async def _save():
        factory = async_session_factory()
        async with factory() as session:
            session.add(MessageThread(
                user_id=None, channel="telegram",
                messages=[{"role": "user", "content": question}, {"role": "assistant", "content": result["answer"]}],
                topic="biology_question",
            ))
            await session.commit()
    await _db_try(_save)

    return ConversationHandler.END


async def handle_quiz_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Select quiz type:", reply_markup=quiz_type_keyboard())
    return QUIZ_TYPE


async def handle_quiz_type(update: Update, context):
    query = update.callback_query
    await query.answer()
    type_map = {"quiztype_mc": "multiple_choice", "quiztype_tf": "true_false", "quiztype_mixed": "mixed"}
    context.user_data["quiz_type"] = type_map.get(query.data, "multiple_choice")
    await query.edit_message_text("Select your grade level:", reply_markup=grade_keyboard("quiz_grade"))
    return QUIZ_GRADE


async def handle_quiz_grade(update: Update, context):
    query = update.callback_query
    await query.answer()
    grade = int(query.data.split("_")[-1])
    context.user_data["quiz_grade"] = grade
    await query.edit_message_text(
        f"Grade {grade} selected. What topic should the quiz cover?\n"
        "(e.g., Cell Biology, Genetics, Ecology)",
        reply_markup=back_keyboard(),
    )
    return QUIZ_TOPIC


async def handle_quiz_topic(update: Update, context):
    topic = update.message.text
    grade = context.user_data.get("quiz_grade", 10)
    qtype = context.user_data.get("quiz_type", "multiple_choice")
    types = qtype.split("_") if qtype == "mixed" else [qtype]
    msg = await update.message.reply_text("Generating your quiz...")

    try:
        router_llm = ModelRouter()
        agent = QuizAgent(llm_router=router_llm)
        result = await agent.generate(grade_level=grade, topic=topic, question_count=5, types=types)

        if not result.get("questions"):
            await msg.edit_text("Sorry, couldn't generate the quiz. Try a different topic.")
            await router_llm.close()
            return ConversationHandler.END

        context.user_data["quiz_session"] = {
            "questions": result["questions"],
            "current": 0,
            "answers": [],
            "correct": 0,
            "total": len(result["questions"]),
            "grade": grade,
            "topic": topic,
            "title": result.get("title", f"Grade {grade} - {topic}"),
        }
        await router_llm.close()
        await _send_quiz_question(update, context, msg)

    except Exception as e:
        logger.error("quiz_error", error=str(e))
        await update.message.reply_text("Error generating quiz.", reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    return QUIZ_ANSWERING


async def _reply_long(update_or_msg_or_query, text: str, reply_markup=None, parse_mode=None, max_len: int = 4096, force_new=False):
    """Split text into chunks and send as multiple messages if needed."""
    html_text = sanitize_for_telegram(format_for_telegram(text)) if parse_mode == "HTML" else text
    plain_text = strip_markdown(text) if parse_mode == "HTML" else text

    for i in range(0, len(html_text), max_len):
        chunk = html_text[i:i + max_len]
        plain_chunk = plain_text[i:i + max_len] if parse_mode == "HTML" else chunk
        if i == 0:
            if not force_new and hasattr(update_or_msg_or_query, 'edit_text'):
                try:
                    await update_or_msg_or_query.edit_text(chunk, reply_markup=reply_markup, parse_mode=parse_mode)
                    continue
                except Exception:
                    pass
            try:
                await update_or_msg_or_query.reply_text(chunk, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception as e:
                if "parse" in str(e).lower():
                    logger.warning("html_parse_failed", error=str(e))
                    await update_or_msg_or_query.reply_text(plain_chunk, reply_markup=reply_markup)
                else:
                    raise
        else:
            try:
                await update_or_msg_or_query.reply_text(chunk, parse_mode=parse_mode)
            except Exception as e:
                if "parse" in str(e).lower():
                    logger.warning("html_parse_failed", error=str(e))
                    await update_or_msg_or_query.reply_text(plain_chunk)
                else:
                    raise


async def _send_quiz_question(update: Update, context, msg=None, new_message=False):
    session = context.user_data.get("quiz_session", {})
    qs = session.get("questions", [])
    idx = session.get("current", 0)
    if idx >= len(qs):
        await _show_quiz_result(update, context)
        return

    q = qs[idx]
    qtype = q.get("question_type", "multiple_choice")
    text = (
        f"📝 {session.get('title', 'Quiz')}\n\n"
        f"Question {idx + 1}/{session.get('total', len(qs))}\n"
        f"<i>{qtype.replace('_', ' ')}</i>\n\n"
        f"{q['question_text']}"
    )

    if qtype == "multiple_choice" and q.get("options"):
        letters = ["A", "B", "C", "D", "E", "F"]
        opt_lines = []
        for i, opt in enumerate(q["options"]):
            if i < len(letters):
                opt_lines.append(f"{letters[i]}) {opt.split(') ')[-1]}")
        text += "\n\n" + "\n".join(opt_lines)

    reply_markup = None
    if qtype == "true_false" or qtype == "true/false":
        reply_markup = tf_keyboard()
    elif q.get("options"):
        reply_markup = answer_options_keyboard(q["options"])
    elif qtype == "short_answer":
        text += "\n\n✏️ Type your answer below, then tap Next."
        reply_markup = quiz_next_keyboard()
    else:
        reply_markup = quiz_next_keyboard()

    if msg:
        await _reply_long(msg, text, reply_markup=reply_markup, parse_mode="HTML", force_new=new_message)
    else:
        await _reply_long(update.effective_message, text, reply_markup=reply_markup, parse_mode="HTML")


def _calculate_quiz_xp(pct: int) -> int:
    xp = 10
    if pct >= 80:
        xp += 10
    if pct >= 100:
        xp += 15
    return xp


async def _save_quiz_rewards(telegram_id, correct, total, context):
    from sqlalchemy import select
    async def _save():
        factory = async_session_factory()
        async with factory() as session:
            result = await session.execute(select(User).where(User.telegram_id == telegram_id))
            user = result.scalar_one_or_none()
            if not user:
                return
            pct = round(correct / max(total, 1) * 100)
            xp_amount = _calculate_quiz_xp(pct)
            meta = {"correct": correct, "total": total, "source": "telegram_bot"}
            await award_xp(user.id, "quiz_completion", xp_amount, meta, session)
            await update_streak(user.id, session)
            await session.commit()
            context.user_data["last_xp_awarded"] = xp_amount
    await _db_try(_save)


async def _show_quiz_result(update: Update, context, msg=None):
    session = context.user_data.get("quiz_session", {})
    correct = session.get("correct", 0)
    total = session.get("total", 0)
    pct = round(correct / max(total, 1) * 100)
    qs = session.get("questions", [])
    ans = session.get("answers", [])

    telegram_id = update.effective_user.id if update.effective_user else None
    if telegram_id:
        await _save_quiz_rewards(telegram_id, correct, total, context)

    xp_awarded = context.user_data.get("last_xp_awarded", _calculate_quiz_xp(pct))
    lines = [f"📊 Quiz Complete!\nScore: {correct}/{total} ({pct}%)"]
    if xp_awarded:
        lines.append(f"⭐ XP Earned: +{xp_awarded} XP\n")
    for i, q in enumerate(qs):
        icon = "✅" if i < len(ans) and ans[i] == q.get("correct_answer", "") else "❌"
        lines.append(f"{icon} Q{i+1}: {q.get('question_text', '')[:50]}")
    text = "\n".join(lines)

    dest = msg or update.effective_message
    await dest.reply_text(text, reply_markup=quiz_result_keyboard(), parse_mode="HTML")


async def handle_quiz_answer(update: Update, context):
    query = update.callback_query
    await query.answer()
    session = context.user_data.get("quiz_session", {})
    qs = session.get("questions", [])
    idx = session.get("current", 0)

    if idx >= len(qs):
        await _show_quiz_result(update, context)
        return ConversationHandler.END

    q = qs[idx]
    selected = query.data.replace("ans_", "")
    correct_answer = q.get("correct_answer", "")

    is_correct = False
    if q.get("question_type") == "multiple_choice" and q.get("options"):
        letters = ["A", "B", "C", "D", "E", "F"]
        try:
            opt_idx = letters.index(selected)
            chosen = q["options"][opt_idx]
            chosen_text = chosen.split(") ")[-1] if ") " in chosen else chosen
            correct_text = correct_answer.split(") ")[-1] if ") " in correct_answer else correct_answer
            is_correct = chosen_text.strip().lower() == correct_text.strip().lower()
        except (ValueError, IndexError):
            is_correct = False
    else:
        is_correct = selected.strip().lower() == correct_answer.strip().lower()

    session["answers"].append(selected)
    if is_correct:
        session["correct"] += 1
    session["current"] += 1

    feedback = "✅ Correct!" if is_correct else f"❌ Wrong. The answer was: {correct_answer}"
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await query.message.reply_text(
        f"{feedback}\n\n{_get_explanation(q)}",
        reply_markup=quiz_next_keyboard(),
        parse_mode="HTML",
    )
    return QUIZ_ANSWERING


def _get_explanation(q: dict) -> str:
    exp = q.get("explanation", "")
    if exp:
        return f"<i>{exp[:200]}</i>"
    return ""


async def handle_quiz_short_answer(update: Update, context):
    session = context.user_data.get("quiz_session", {})
    qs = session.get("questions", [])
    idx = session.get("current", 0)

    if idx >= len(qs):
        await _show_quiz_result(update, context)
        return ConversationHandler.END

    q = qs[idx]
    qtype = q.get("question_type", "")

    if qtype != "short_answer":
        msg = "Please use the buttons below to answer."
        if q.get("options"):
            await update.message.reply_text(msg, reply_markup=answer_options_keyboard(q["options"]))
        else:
            await update.message.reply_text(msg)
        return QUIZ_ANSWERING

    user_answer = update.message.text.strip()
    correct_answer = q.get("correct_answer", "").strip()
    is_correct = user_answer.lower() == correct_answer.lower()

    session["answers"].append(user_answer)
    if is_correct:
        session["correct"] += 1
    session["current"] += 1

    feedback = "✅ Correct!" if is_correct else f"❌ Wrong. The answer was: {correct_answer}"
    if q.get("explanation"):
        feedback += f"\n\n<i>{q['explanation'][:200]}</i>"

    await update.message.reply_text(feedback, reply_markup=quiz_next_keyboard(), parse_mode="HTML")
    return QUIZ_ANSWERING


async def handle_quiz_next(update: Update, context):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _send_quiz_question(update, context, query.message, new_message=True)
    return QUIZ_ANSWERING


async def handle_quiz_end(update: Update, context):
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _show_quiz_result(update, context, query.message)
    context.user_data.pop("quiz_session", None)
    return ConversationHandler.END


async def handle_quiz_retry(update: Update, context):
    query = update.callback_query
    await query.answer()
    session = context.user_data.get("quiz_session", {})
    session["current"] = 0
    session["answers"] = []
    session["correct"] = 0
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _send_quiz_question(update, context, query.message, new_message=True)
    return QUIZ_ANSWERING


async def handle_lesson_start(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Select grade level:", reply_markup=grade_keyboard("lesson_grade"))
    return LESSON_GRADE


async def handle_lesson_grade(update: Update, context):
    query = update.callback_query
    await query.answer()
    grade = int(query.data.split("_")[-1])
    context.user_data["lesson_grade"] = grade
    await query.edit_message_text(
        f"Grade {grade} selected. What biology topic?",
        reply_markup=back_keyboard(),
    )
    return LESSON_TOPIC


async def handle_lesson_topic(update: Update, context):
    topic = update.message.text
    grade = context.user_data.get("lesson_grade", 10)
    await update.message.reply_text("Creating lesson plan...")

    try:
        router_llm = ModelRouter()
        agent = LessonPlannerAgent(llm_router=router_llm)
        result = await agent.generate(grade_level=grade, topic=topic)
        response = (
            f"Lesson Plan: {topic} (Grade {grade})\n\n"
            f"Objective:\n{result['objective']}\n\n"
            f"Explanation:\n{result['explanation'][:1000]}...\n\n"
        )
        if result.get("activities"):
            response += "Activities:\n"
            for a in result["activities"]:
                response += f"  * {a.get('name', '')} ({a.get('duration_minutes', '')}min)\n"
        if result.get("assessment"):
            response += f"\nAssessment:\n{result['assessment'][:500]}"
        if result.get("homework"):
            response += f"\n\nHomework:\n{result['homework'][:500]}"
        await _reply_long(update.message, response, reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)), parse_mode="HTML")
        await router_llm.close()
    except Exception as e:
        logger.error("lesson_error", error=str(e))
        await update.message.reply_text("Error creating lesson plan.", reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)))

    return ConversationHandler.END


async def handle_progress(update: Update, context):
    query = update.callback_query
    if query:
        await query.answer()
    text = (
        "📊 My Progress\n\n"
        "Feature requires PostgreSQL. Set up the database to track:\n"
        "• Quiz scores and attempts\n"
        "• Weak areas by topic\n"
        "• Overall performance trends\n\n"
        "In the meantime, keep practicing with quizzes!"
    )
    if query:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(text, reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)))
    else:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)))


async def handle_language(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Choose your language:", reply_markup=language_keyboard())


async def handle_language_select(update: Update, context):
    query = update.callback_query
    await query.answer()
    lang_map = {"lang_en": ("en", "English"), "lang_am": ("am", "Amharic"), "lang_both": ("both", "Bilingual")}
    code, name = lang_map.get(query.data, ("en", "English"))
    context.user_data["language"] = code
    await query.message.reply_text(
        f"Language set to {name}!\n\nYou can now ask biology questions in {name}.",
        reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
    )


async def handle_socratic_toggle(update: Update, context):
    query = update.callback_query
    await query.answer()
    current = context.user_data.get("socratic_mode", False)
    context.user_data["socratic_mode"] = not current
    status = "ON 🧠" if context.user_data["socratic_mode"] else "OFF"
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await query.message.reply_text(
        f"Socratic Mode is now {status}.\n\n"
        "In Socratic mode, I'll guide you with questions rather than giving direct answers.",
        reply_markup=main_menu_keyboard(not current),
    )


async def model_command(update: Update, context):
    api_base = settings.api_base_url
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{api_base}/models")
            models = resp.json()
            resp2 = await client.get(f"{api_base}/models/active")
            active = resp2.json()["model"]
        await update.message.reply_text(
            "Select a model:",
            reply_markup=InlineKeyboardMarkup(model_selection_keyboard(models, active)),
        )
    except Exception as e:
        logger.error("model_command_error", error=str(e))
        await update.message.reply_text("Failed to fetch models. Is the API server running?", reply_markup=main_menu_keyboard())


async def handle_model_selection(update: Update, context):
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    api_base = settings.api_base_url

    if action == "back":
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text("Main menu:", reply_markup=main_menu_keyboard())
        return

    if action == "refresh":
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{api_base}/models/refresh")
                resp = await client.get(f"{api_base}/models")
                models = resp.json()
                resp2 = await client.get(f"{api_base}/models/active")
                active = resp2.json()["model"]
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            await query.message.reply_text(
                "Select a model:",
                reply_markup=InlineKeyboardMarkup(model_selection_keyboard(models, active)),
            )
        except Exception as e:
            logger.error("model_refresh_error", error=str(e))
            await query.message.reply_text("Failed to refresh models.", reply_markup=main_menu_keyboard())
        return

    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{api_base}/models/active", json={"model": action})
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(
            f"✅ Active model is now: {action}",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as e:
        logger.error("model_set_error", error=str(e))
        await query.message.reply_text(f"Failed to set model: {action}", reply_markup=main_menu_keyboard())


async def handle_hint(update: Update, context):
    query = update.callback_query
    await query.answer()
    hint_level = int(query.data.split("_")[-1])
    reveal = context.user_data.get("reveal_answer", False)
    if reveal:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(
            "The answer has already been revealed! Ask a new question.",
            reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
        )
        return
    question = context.user_data.get("ask_question", "")
    if not question:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(
            "No active question. Ask a question first.",
            reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
        )
        return
    context.user_data["hint_level"] = hint_level
    hint_msg = await query.message.reply_text(f"💡 Hint level {hint_level}/3...")
    try:
        router_llm = ModelRouter()
        agent = TutorAgent(llm_router=router_llm, retriever=None)
        result = await agent.answer(
            question=question, user_id=None, use_rag=True,
            grade_level=context.user_data.get("grade_level"),
            language=context.user_data.get("language", "en"),
            socratic_mode=context.user_data.get("socratic_mode", True),
            hint_level=hint_level,
            reveal_answer=False,
        )
        response = result["answer"]
        if result.get("misconception_detected"):
            response += "\n\n💡 I noticed a misunderstanding — gently corrected above."
        await _reply_long(
            hint_msg, response,
            reply_markup=hint_keyboard(hint_level, False),
            parse_mode="HTML",
        )
        await router_llm.close()
    except Exception as e:
        logger.error("hint_callback_error", error=str(e))
        await hint_msg.edit_text(
            "Sorry, I encountered an error.",
            reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
        )


async def handle_reveal_answer(update: Update, context):
    query = update.callback_query
    await query.answer()
    question = context.user_data.get("ask_question", "")
    if not question:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        await query.message.reply_text(
            "No active question. Ask a question first.",
            reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
        )
        return
    hint_level = context.user_data.get("hint_level", 0)
    context.user_data["reveal_answer"] = True
    reveal_msg = await query.message.reply_text("🔍 Revealing the full answer...")
    try:
        router_llm = ModelRouter()
        agent = TutorAgent(llm_router=router_llm, retriever=None)
        result = await agent.answer(
            question=question, user_id=None, use_rag=True,
            grade_level=context.user_data.get("grade_level"),
            language=context.user_data.get("language", "en"),
            socratic_mode=False,
            hint_level=hint_level,
            reveal_answer=True,
        )
        attempt_msg = f"\n\n📊 You used {hint_level} hint(s) before revealing the answer." if hint_level > 0 else "\n\n📊 You revealed the answer without using hints."
        response = result["answer"] + attempt_msg
        await _reply_long(
            reveal_msg, response,
            reply_markup=hint_keyboard(hint_level, True),
            parse_mode="HTML",
        )
        await router_llm.close()
    except Exception as e:
        logger.error("reveal_answer_error", error=str(e))
        await reveal_msg.edit_text(
            "Sorry, I encountered an error.",
            reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
        )


async def handle_general_message(update: Update, context):
    message_text = update.message.text
    try:
        router = ModelRouter()
        from src.agents.orchestrator import OrchestratorAgent
        orchestrator = OrchestratorAgent(llm_router=router)
        intent = await orchestrator.classify_intent(message_text)
        await router.close()

        if intent["intent"] in ("tutor", "general"):
            return await handle_question(update, context)
        elif intent["intent"] in ("quiz", "lesson_plan"):
            await update.message.reply_text(
                f"I understood: \"{intent['intent']}\" (confidence: {intent['confidence']:.0%})\n\n"
                f"Use the 📝 Quiz or 📋 Lesson Plan buttons in the menu.",
                reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                f"I understood: \"{intent['intent']}\" (confidence: {intent['confidence']:.0%})\n\n"
                f"Use the menu buttons to access specific features.",
                reply_markup=main_menu_keyboard(context.user_data.get("socratic_mode", False)),
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error("general_message_error", error=str(e))
        return await handle_question(update, context)


async def error_handler(update: Update, context):
    logger.error("telegram_error", error=str(context.error))
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Sorry, something went wrong. Please try again or use /help.",
            )
    except Exception as e:
        logger.error("error_handler_failed", error=str(e))


def build_app() -> Application:
    from telegram.request import HTTPXRequest
    _request = HTTPXRequest(
        read_timeout=60.0, write_timeout=60.0,
        connect_timeout=30.0, pool_timeout=5.0,
    )
    app = Application.builder().token(settings.telegram_bot_token).request(_request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("grade", grade_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("socratic", socratic_command))
    app.add_handler(CommandHandler("hint", hint_command))
    app.add_handler(CommandHandler("reveal", reveal_command))

    quiz_handler = ConversationHandler(
        entry_points=[
            CommandHandler("quiz", quiz_command),
            CallbackQueryHandler(handle_quiz_start, pattern="^quiz$"),
        ],
        states={
            QUIZ_TYPE: [
                CallbackQueryHandler(handle_quiz_type, pattern="^quiztype_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            QUIZ_GRADE: [
                CallbackQueryHandler(handle_quiz_grade, pattern="^quiz_grade_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            QUIZ_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz_topic),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            QUIZ_ANSWERING: [
                CallbackQueryHandler(handle_quiz_answer, pattern="^ans_"),
                CallbackQueryHandler(handle_quiz_next, pattern="^quiz_next$"),
                CallbackQueryHandler(handle_quiz_end, pattern="^quiz_end$"),
                CallbackQueryHandler(handle_quiz_retry, pattern="^quiz_retry$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz_short_answer),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("menu", menu),
            CallbackQueryHandler(end_conversation, pattern="^menu$"),
        ],
        per_user=True,
    )
    app.add_handler(quiz_handler)

    lesson_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_lesson_start, pattern="^lesson_plan$")],
        states={
            LESSON_GRADE: [
                CallbackQueryHandler(handle_lesson_grade, pattern="^lesson_grade_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            LESSON_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lesson_topic),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("menu", menu),
            CallbackQueryHandler(end_conversation, pattern="^menu$"),
        ],
        per_user=True,
    )
    app.add_handler(lesson_handler)

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_tutor, pattern="^tutor$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_general_message),
        ],
        states={
            TUTOR_GRADE: [
                CallbackQueryHandler(handle_tutor_grade, pattern="^tutor_grade_"),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
            TUTOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question),
                CallbackQueryHandler(end_conversation, pattern="^menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("menu", menu),
            CallbackQueryHandler(end_conversation, pattern="^menu$"),
            CallbackQueryHandler(handle_tutor, pattern="^tutor$"),
            CallbackQueryHandler(handle_tutor_grade, pattern="^tutor_grade_"),
        ],
        per_user=True,
    )
    app.add_handler(conv_handler)

    app.add_handler(CallbackQueryHandler(handle_model_selection, pattern="^model:"))
    app.add_handler(CallbackQueryHandler(handle_socratic_toggle, pattern="^socratic_toggle$"))
    app.add_handler(CallbackQueryHandler(handle_hint, pattern="^hint_"))
    app.add_handler(CallbackQueryHandler(handle_reveal_answer, pattern="^reveal_answer$"))
    app.add_handler(CallbackQueryHandler(handle_teacher_tools, pattern="^teacher_tools$"))
    app.add_handler(CallbackQueryHandler(handle_open_quizzes, pattern="^open_quizzes$"))
    app.add_handler(CallbackQueryHandler(handle_open_dashboard, pattern="^open_dashboard$"))
    app.add_handler(CallbackQueryHandler(handle_progress, pattern="^progress$"))
    app.add_handler(CallbackQueryHandler(handle_language, pattern="^language$"))
    app.add_handler(CallbackQueryHandler(handle_language_select, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(menu, pattern="^menu$"))
    app.add_error_handler(error_handler)

    return app


async def main():
    app = build_app()
    if settings.telegram_webhook_url:
        await app.initialize()
        await app.bot.set_webhook(
            url=settings.telegram_webhook_url,
            secret_token=settings.telegram_webhook_secret,
        )
        await app.start()
        logger.info("webhook_set", url=settings.telegram_webhook_url)
    else:
        logger.info("starting_polling")
        await app.initialize()
        await app.updater.start_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=True)
        await app.start()
        logger.info("bot_polling_started")
        try:
            import asyncio
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            await app.shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
