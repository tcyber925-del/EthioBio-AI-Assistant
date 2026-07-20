import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.diagnostic_assessment import DiagnosticAgent
from src.database.models import Question, Quiz
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.diagnostic import DiagnosticRequest, DiagnosticResponse, TopicBaseline
from src.schemas.quiz import QuestionSchema
from src.schemas.streaming import TokenChunk

logger = structlog.get_logger()
router = APIRouter(prefix="/quiz", tags=["Diagnostic"])


async def _stream_events(
    queue: asyncio.Queue[TokenChunk | None],
    task: asyncio.Task,
) -> AsyncGenerator[str, None]:
    try:
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            if chunk.error:
                yield f"data: {chunk.model_dump_json()}\n\n"
                break
            yield f"data: {chunk.model_dump_json()}\n\n"
            if chunk.done:
                break
        if task.done() and (exc := task.exception()):
            yield f"data: {TokenChunk(delta='', done=True, error=str(exc)).model_dump_json()}\n\n"
    except Exception as e:
        yield f"data: {TokenChunk(delta='', done=True, error=str(e)).model_dump_json()}\n\n"


@router.post("/diagnostic", response_model=DiagnosticResponse)
async def run_diagnostic(request: DiagnosticRequest, session: AsyncSession = Depends(get_session)):
    if request.stream:
        return await _handle_diagnostic_stream(request)
    router_llm = ModelRouter(preferred_model=request.model)
    agent = DiagnosticAgent(llm_router=router_llm)

    try:
        result = await agent.generate(
            grade_level=request.grade_level,
            topics=request.topics,
            questions_per_topic=request.questions_per_topic,
            language=request.language,
            session=session,
        )

        topic_baselines: list[TopicBaseline] = []
        all_questions: list[Question] = []

        for assessment in result.get("assessments", []):
            topic = assessment["topic"]
            questions = assessment.get("questions", [])

            db_quiz = Quiz(
                title=f"Diagnostic — {topic}",
                grade_level=request.grade_level,
                topic=topic,
                question_count=len(questions),
                model_used=result.get("model_used", ""),
            )
            session.add(db_quiz)
            await session.flush()

            _difficulty_map = {"easy": -1.0, "medium": 0.0, "hard": 1.0}
            topic_questions: list[Question] = []
            for q in questions:
                diff_str = q.get("difficulty", "easy")
                db_q = Question(
                    quiz_id=db_quiz.id,
                    question_type=q["question_type"],
                    question_text=q["question_text"],
                    options=q.get("options"),
                    correct_answer=q["correct_answer"],
                    explanation=q.get("explanation"),
                    grade_level=request.grade_level,
                    topic=topic,
                    difficulty=diff_str,
                    difficulty_score=_difficulty_map.get(diff_str, 0.0),
                )
                session.add(db_q)
                topic_questions.append(db_q)

            all_questions.extend(topic_questions)

        await session.commit()

        for assessment in result.get("assessments", []):
            topic = assessment["topic"]
            topic_qs = [q for q in all_questions if q.topic == topic]
            topic_baselines.append(
                TopicBaseline(
                    topic=topic,
                    score=0.0,
                    total=len(topic_qs),
                    correct=0,
                    severity="pending",
                    questions=[
                        QuestionSchema(
                            question_type=q.question_type,
                            question_text=q.question_text,
                            options=cast(list[str] | None, q.options),
                            correct_answer=q.correct_answer,
                            explanation=q.explanation,
                            difficulty=q.difficulty,
                        )
                        for q in topic_qs
                    ],
                )
            )

        diagnostic_id = uuid4()
        overall_score = 0.0
        overall_severity = "pending"
        weakest_topics: list[str] = []
        strongest_topics: list[str] = []

        return DiagnosticResponse(
            diagnostic_id=diagnostic_id,
            user_id=request.user_id,
            grade_level=request.grade_level,
            overall_score=overall_score,
            overall_severity=overall_severity,
            topic_baselines=topic_baselines,
            weakest_topics=weakest_topics,
            strongest_topics=strongest_topics,
            generated_at=datetime.now(timezone.utc),
            model_used=result.get("model_used", ""),
        )
    except Exception as e:
        await session.rollback()
        logger.error("diagnostic_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_diagnostic_stream(
    request: DiagnosticRequest,
) -> StreamingResponse:
    router_llm = ModelRouter(preferred_model=request.model)
    agent = DiagnosticAgent(llm_router=router_llm)

    queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()
    task = asyncio.create_task(
        agent.generate(
            grade_level=request.grade_level,
            topics=request.topics,
            questions_per_topic=request.questions_per_topic,
            language=request.language,
            token_queue=queue,
        )
    )

    return StreamingResponse(
        _stream_events(queue, task),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
