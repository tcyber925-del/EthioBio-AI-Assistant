from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.session import get_session
from src.schemas.chat import TutorRequest, TutorResponse
from src.agents.tutor import TutorAgent
from src.rag.retriever import Retriever
from src.llm.router import ModelRouter
import structlog

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
        )
        return TutorResponse(
            answer=result["answer"],
            language=result.get("language", request.language),
            sources=result.get("sources", []),
            model_used=result.get("model_used", ""),
            confidence=result.get("confidence", 0.0),
            socratic_mode=result.get("socratic_mode", False),
        )
    except Exception as e:
        logger.error("chat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
