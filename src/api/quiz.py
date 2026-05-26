
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.quiz import QuizAgent
from src.agents.weak_topic_detection import analyze_quiz_attempt, get_weak_topics
from src.api.gamification import award_xp, check_achievements, update_streak
from src.database.models import Question, Quiz, QuizAttempt
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.quiz import (
    QuestionSchema,
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizRecommendResponse,
    QuizRecommendation,
    QuizSubmitRequest,
    QuizSubmitResponse,
)

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
            recommendations.append(QuizRecommendation(
                topic=wt["topic"],
                unit=wt.get("unit", ""),
                grade_level=wt.get("grade_level", 0),
                current_mastery=avg,
                severity=severity,
                recommended_difficulty=recommended_difficulty,
                priority=priority,
                has_misconceptions=len(misconceptions) > 0,
                misconception_count=len(misconceptions),
            ))

        recommendations.sort(key=lambda r: r.priority)
        return QuizRecommendResponse(
            user_id=user_id,
            recommendations=recommendations,
            total_recommendations=len(recommendations),
        )
    except Exception as e:
        logger.error("quiz_recommend_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=QuizGenerateResponse)
async def generate_quiz(request: QuizGenerateRequest, session: AsyncSession = Depends(get_session)):
    router_llm = ModelRouter(preferred_model=request.model)
    agent = QuizAgent(llm_router=router_llm)

    try:
        weak_topics = None
        target_difficulty = None
        if request.user_id:
            all_weak = await get_weak_topics(request.user_id, session)
            if all_weak:
                # Pick the weakest matching topic for difficulty adaptation
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
                    # No exact match - use all weak topics for focus
                    weak_topics = all_weak

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

        await analyze_quiz_attempt(attempt, session)

        recommendations: list[dict] = []
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
                recommendations.append({
                    "topic": wt["topic"],
                    "unit": wt.get("unit", ""),
                    "grade_level": wt.get("grade_level", 0),
                    "current_mastery": wt["average_score"],
                    "severity": sev,
                    "recommended_difficulty": rec_diff,
                    "priority": pri,
                    "has_misconceptions": len(mc_list) > 0,
                    "misconception_count": len(mc_list),
                })
            recommendations.sort(key=lambda r: r["priority"])
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
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error("quiz_submit_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
