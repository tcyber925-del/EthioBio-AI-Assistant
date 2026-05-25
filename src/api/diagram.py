import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.diagram import DiagramAgent
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.diagram import DiagramGenerateRequest, DiagramGenerateResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/diagram", tags=["Diagram"])


@router.post("/generate", response_model=DiagramGenerateResponse)
async def generate_diagram(
    request: DiagramGenerateRequest,
    session: AsyncSession = Depends(get_session),
):
    router_llm = ModelRouter()
    agent = DiagramAgent(llm_router=router_llm)

    try:
        result = await agent.generate(
            prompt=request.prompt,
            topic=request.topic,
            difficulty=request.difficulty,
            session=session,
        )

        return DiagramGenerateResponse(
            diagram_svg=result["diagram_svg"],
            labels=result["labels"],
            title=result["title"],
            topic=result["topic"],
            difficulty=result["difficulty"],
            model_used=result.get("model_used", ""),
        )
    except Exception as e:
        logger.error("diagram_generate_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
