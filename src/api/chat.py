import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.tutor import TutorAgent
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.rag.retriever import Retriever
from src.schemas.chat import TutorRequest, TutorResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=TutorResponse)
async def chat_tutor(request: TutorRequest, session: AsyncSession = Depends(get_session)):
    router_llm = ModelRouter()
    retriever = Retriever()
    agent = TutorAgent(llm_router=router_llm, retriever=retriever)

    try:
        result = await agent.answer(
            question=request.question,
            user_id=request.user_id,
            grade_level=request.grade_level,
            topic=request.topic,
            language=request.language,
            use_rag=request.use_rag,
            session=session,
            socratic_mode=request.socratic_mode,
            hint_level=request.hint_level,
            reveal_answer=request.reveal_answer,
        )
        return TutorResponse(
            answer=result["answer"],
            language=result.get("language", request.language),
            sources=result.get("sources", []),
            model_used=result.get("model_used", ""),
            confidence=result.get("confidence", 0.0),
            socratic_mode=result.get("socratic_mode", False),
            hint_level=result.get("hint_level", 0),
            reveal_answer=result.get("reveal_answer", False),
            misconception_detected=result.get("misconception_detected", False),
            misconception_correction=result.get("misconception_correction", ""),
        )
    except Exception as e:
        logger.error("chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
