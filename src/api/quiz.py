
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.quiz import QuizAgent
from src.api.gamification import award_xp, check_achievements, update_streak
from src.database.models import Question, Quiz, QuizAttempt
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.quiz import (
    QuestionSchema,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.post("/generate", response_model=QuizGenerateResponse)
async def generate_quiz(request: QuizGenerateRequest, session: AsyncSession = Depends(get_session)):
    router_llm = ModelRouter(preferred_model=request.model)
    agent = QuizAgent(llm_router=router_llm)

    try:
        result = await agent.generate(
            grade_level=request.grade_level,
            topic=request.topic,
            question_count=request.question_count,
            types=request.types,
            language=request.language,
            session=session,
        )

        db_quiz = Quiz(
            teacher_id=request.teacher_id,
            title=f"Grade {request.grade_level} - {request.topic}",
            grade_level=request.grade_level,
            topic=request.topic,
            question_count=request.question_count,
            model_used=result.get("model_used", ""),
        )
        session.add(db_quiz)
        await session.flush()

        for q in result["questions"]:
            db_q = Question(
                quiz_id=db_quiz.id,
                question_type=q["question_type"],
                question_text=q["question_text"],
                options=q.get("options"),
                correct_answer=q["correct_answer"],
                explanation=q.get("explanation"),
                grade_level=request.grade_level,
                topic=request.topic,
                difficulty=q.get("difficulty", "medium"),
            )
            session.add(db_q)

        await session.commit()

        return QuizGenerateResponse(
            title=db_quiz.title,
            grade_level=request.grade_level,
            topic=request.topic,
            questions=[QuestionSchema(**q) for q in result["questions"]],
            answer_key=result.get("answer_key", ""),
            model_used=result.get("model_used", ""),
        )
    except Exception as e:
        await session.rollback()
        logger.error("quiz_generate_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


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
            question = question_map.get(q_id)
            if question:
                is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()
                if is_correct:
                    correct_count += 1
                feedback.append({
                    "question_id": q_id,
                    "correct": is_correct,
                    "correct_answer": question.correct_answer,
                    "explanation": question.explanation,
                })

        total = len(request.answers)
        score = (correct_count / total * 100) if total > 0 else 0

        attempt = QuizAttempt(
            user_id=request.user_id,
            quiz_id=request.quiz_id,
            score=score,
            total=total,
            answers=[a.model_dump() for a in request.answers],
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
        await session.commit()

        return QuizSubmitResponse(
            score=score,
            total=total,
            correct=correct_count,
            feedback=feedback,
            xp_awarded=xp_awarded,
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("quiz_submit_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
