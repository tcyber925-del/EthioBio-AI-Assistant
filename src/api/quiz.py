import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.quiz import QuizAgent
from src.agents.weak_topic_detection import analyze_quiz_attempt, get_weak_topics
from src.api.auth import get_current_user
from src.api.gamification import award_xp, check_achievements, update_streak
from src.database.models import MisconceptionPattern, Question, Quiz, QuizAttempt, User
from src.database.session import async_session_factory, get_session
from src.llm.router import ModelRouter
from src.schemas.quiz import (
    QuizGenerateRequest,
    QuizRecommendation,
    QuizRecommendResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
)

_task_store: dict[str, dict] = {}
_task_lock = None


def _get_lock():
    global _task_lock
    if _task_lock is None:
        import asyncio
        _task_lock = asyncio.Lock()
    return _task_lock


async def _create_task() -> str:
    task_id = str(uuid.uuid4())
    lock = _get_lock()
    async with lock:
        _task_store[task_id] = {"status": "pending", "created_at": datetime.now(timezone.utc)}
    return task_id


async def _update_task(task_id: str, **kwargs):
    lock = _get_lock()
    async with lock:
        if task_id in _task_store:
            _task_store[task_id].update(kwargs)


async def _get_task(task_id: str) -> dict | None:
    lock = _get_lock()
    async with lock:
        return _task_store.get(task_id)

logger = structlog.get_logger()
router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.get("/recommend/{user_id}", response_model=QuizRecommendResponse)
async def get_quiz_recommendations(user_id, session: AsyncSession = Depends(get_session)):
    try:
        weak_topics = await get_weak_topics(user_id, session)
        recommendations: list[QuizRecommendation] = []
        for i, wt in enumerate(weak_topics):
            severity = wt["severity"]
            avg = wt["average_score"]
            if severity == "critical":
                recommended_difficulty = "easy"
                priority = 1
            elif severity == "moderate":
                recommended_difficulty = "medium"
                priority = 2
            else:
                recommended_difficulty = "hard"
                priority = 3

            misconceptions = wt.get("misconceptions", [])
            recommendations.append(
                QuizRecommendation(
                    topic=wt["topic"],
                    unit=wt.get("unit", ""),
                    grade_level=wt.get("grade_level", 0),
                    current_mastery=avg,
                    severity=severity,
                    recommended_difficulty=recommended_difficulty,
                    priority=priority,
                    has_misconceptions=len(misconceptions) > 0,
                    misconception_count=len(misconceptions),
                )
            )

        recommendations.sort(key=lambda r: r.priority)
        return QuizRecommendResponse(
            user_id=user_id,
            recommendations=recommendations,
            total_recommendations=len(recommendations),
        )
    except Exception as e:
        logger.error("quiz_recommend_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_quiz(
    request: QuizGenerateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    teacher_id = request.teacher_id or current_user.id
    task_id = await _create_task()

    import asyncio as _asyncio

    _asyncio.ensure_future(_run_quiz_generation(task_id, request, teacher_id))

    return {"task_id": task_id, "status": "pending"}


@router.get("/generate/status/{task_id}")
async def generate_quiz_status(task_id: str):
    task = await _get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def _run_quiz_generation(task_id: str, request: QuizGenerateRequest, teacher_id: uuid.UUID):
    try:
        router_llm = ModelRouter(preferred_model=request.model)
        agent = QuizAgent(llm_router=router_llm)

        factory = async_session_factory()
        async with factory() as session:
            weak_topics = None
            target_difficulty = None
            if request.user_id:
                all_weak = await get_weak_topics(request.user_id, session)
                if all_weak:
                    topic_lower = request.topic.lower()
                    matching = [wt for wt in all_weak if wt["topic"].lower() == topic_lower]
                    if matching:
                        weak_topics = matching
                        top_severity = matching[0]["severity"]
                        if top_severity == "critical":
                            target_difficulty = "easy"
                        elif top_severity == "moderate":
                            target_difficulty = "medium"
                    else:
                        weak_topics = all_weak

            if request.adaptive and request.user_id:
                from src.agents.adaptive_quiz import select_adaptive_questions

                selected = await select_adaptive_questions(
                    session=session,
                    user_id=request.user_id,
                    topic=request.topic,
                    count=request.question_count,
                )
                if selected:
                    avg_difficulty = sum(q.difficulty_score for q in selected) / len(selected)
                    if avg_difficulty < -0.3:
                        target_difficulty = "easy"
                    elif avg_difficulty > 0.3:
                        target_difficulty = "hard"
                    else:
                        target_difficulty = "medium"

            result = await agent.generate(
                grade_level=request.grade_level,
                topic=request.topic,
                question_count=request.question_count,
                types=request.types,
                language=request.language,
                session=session,
                weak_topics=weak_topics,
                target_difficulty=target_difficulty,
            )

            db_quiz = Quiz(
                teacher_id=teacher_id,
                title=f"Grade {request.grade_level} - {request.topic}",
                grade_level=request.grade_level,
                topic=request.topic,
                question_count=request.question_count,
                model_used=result.get("model_used", ""),
            )
            session.add(db_quiz)
            await session.flush()

            _difficulty_map = {"easy": -1.0, "medium": 0.0, "hard": 1.0}
            for q in result["questions"]:
                diff_str = q.get("difficulty", "medium")
                db_q = Question(
                    quiz_id=db_quiz.id,
                    question_type=q["question_type"],
                    question_text=q["question_text"],
                    options=q.get("options"),
                    correct_answer=q["correct_answer"],
                    explanation=q.get("explanation"),
                    grade_level=request.grade_level,
                    topic=request.topic,
                    difficulty=diff_str,
                    difficulty_score=_difficulty_map.get(diff_str, 0.0),
                )
                session.add(db_q)

            await session.commit()

            await _update_task(
                task_id,
                status="completed",
                quiz_id=str(db_quiz.id),
            )
    except Exception as e:
        logger.error("quiz_generate_background_error", error=str(e))
        await _update_task(task_id, status="failed", error=str(e))


@router.get("")
async def list_quizzes(
    teacher_id: uuid.UUID | None = None,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if teacher_id is None:
        teacher_id = current_user.id
    stmt = (
        select(Quiz)
        .where(Quiz.teacher_id == teacher_id)
        .order_by(Quiz.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    quizzes = result.scalars().all()
    return {
        "items": [
            {
                "id": str(q.id),
                "title": q.title,
                "topic": q.topic,
                "grade_level": q.grade_level,
                "question_count": q.question_count,
                "status": q.status,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            }
            for q in quizzes
        ]
    }


@router.post("/submit", response_model=QuizSubmitResponse)
async def submit_quiz(request: QuizSubmitRequest, session: AsyncSession = Depends(get_session)):
    try:
        quiz = await session.get(Quiz, request.quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        questions = await session.execute(
            Question.__table__.select().where(Question.quiz_id == request.quiz_id)
        )
        question_map = {str(q.id): q for q in questions.scalars().all()}

        correct_count = 0
        feedback = []
        for answer in request.answers:
            q_id = answer.get("question_id")
            user_answer = answer.get("answer", "")
            question = question_map.get(q_id) if q_id is not None else None
            if question:
                is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
                if is_correct:
                    correct_count += 1
                feedback.append(
                    {
                        "question_id": q_id,
                        "correct": is_correct,
                        "correct_answer": question.correct_answer,
                        "explanation": question.explanation,
                    }
                )
                from src.agents.adaptive_quiz import record_attempt

                await record_attempt(
                    session=session,
                    user_id=request.user_id,
                    question_id=question.id,
                    quiz_id=request.quiz_id,
                    correct=is_correct,
                )

        total = len(request.answers)
        score = (correct_count / total * 100) if total > 0 else 0

        # Update student ability estimates per topic
        if quiz.topic:
            from src.agents.adaptive_quiz import update_ability

            await update_ability(
                session=session,
                user_id=request.user_id,
                topic=quiz.topic,
                correct_count=correct_count,
                total_count=total,
            )

        attempt = QuizAttempt(
            user_id=request.user_id,
            quiz_id=request.quiz_id,
            score=score,
            total=total,
            answers=request.answers,
            completed=True,
        )
        session.add(attempt)
        await session.flush()

        xp_awarded = 10
        if score >= 80:
            xp_awarded += 10
        if score >= 100:
            xp_awarded += 15
        gam_result, _, _ = await award_xp(
            request.user_id,
            "quiz_completion",
            xp_awarded,
            {"quiz_id": str(request.quiz_id), "score": score, "total": total},
            session,
        )
        await update_streak(request.user_id, session)
        await check_achievements(request.user_id, gam_result, session)

        await analyze_quiz_attempt(attempt, session)

        misconceptions_detected: list[dict] = []
        try:
            from datetime import datetime, timezone

            cutoff = attempt.completed_at or attempt.started_at or datetime.now(timezone.utc)
            mc_result = await session.execute(
                select(MisconceptionPattern)
                .where(
                    MisconceptionPattern.user_id == request.user_id,
                    MisconceptionPattern.last_detected_at >= cutoff,
                )
                .order_by(MisconceptionPattern.last_detected_at.desc())
                .limit(10)
            )
            for mc in mc_result.scalars().all():
                misconceptions_detected.append(
                    {
                        "topic": mc.topic,
                        "pattern_description": mc.pattern_description,
                        "severity": mc.severity,
                        "frequency": mc.frequency,
                        "confidence": mc.confidence,
                        "common_wrong_answer": mc.common_wrong_answer,
                        "last_detected_at": str(mc.last_detected_at)
                        if mc.last_detected_at
                        else None,
                    }
                )
        except Exception:
            logger.warning("quiz_misconception_fetch_error", exc_info=True)

        recommendations: list[QuizRecommendation] = []
        try:
            fresh_weak = await get_weak_topics(request.user_id, session)
            for i, wt in enumerate(fresh_weak):
                sev = wt["severity"]
                if sev == "critical":
                    rec_diff = "easy"
                    pri = 1
                elif sev == "moderate":
                    rec_diff = "medium"
                    pri = 2
                else:
                    rec_diff = "hard"
                    pri = 3
                mc_list = wt.get("misconceptions", [])
                recommendations.append(
                    QuizRecommendation(
                        topic=wt["topic"],
                        unit=wt.get("unit", ""),
                        grade_level=wt.get("grade_level", 0),
                        current_mastery=wt["average_score"],
                        severity=sev,
                        recommended_difficulty=rec_diff,
                        priority=pri,
                        has_misconceptions=len(mc_list) > 0,
                        misconception_count=len(mc_list),
                    )
                )
            recommendations.sort(key=lambda r: r.priority)
        except Exception:
            logger.warning("quiz_recommend_after_submit_error", exc_info=True)

        await session.commit()

        return QuizSubmitResponse(
            score=score,
            total=total,
            correct=correct_count,
            feedback=feedback,
            xp_awarded=xp_awarded,
            recommendations=recommendations or None,
            misconceptions_detected=misconceptions_detected,
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("quiz_submit_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from uuid import UUID
    try:
        item_uuid = UUID(quiz_id)
        quiz = await session.get(Quiz, item_uuid)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        questions_result = await session.execute(
            select(Question).where(Question.quiz_id == item_uuid).order_by(Question.created_at)
        )
        questions = questions_result.scalars().all()

        return {
            "id": str(quiz.id),
            "title": quiz.title,
            "grade_level": quiz.grade_level,
            "topic": quiz.topic,
            "question_count": quiz.question_count,
            "status": quiz.status,
            "model_used": quiz.model_used,
            "created_at": quiz.created_at.isoformat() if quiz.created_at else None,
            "questions": [
                {
                    "id": str(q.id),
                    "question_type": q.question_type,
                    "question_text": q.question_text,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                    "difficulty": q.difficulty,
                }
                for q in questions
            ],
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("quiz_detail_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
