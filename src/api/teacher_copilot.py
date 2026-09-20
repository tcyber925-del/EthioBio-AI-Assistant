import asyncio
from collections.abc import AsyncGenerator
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import get_current_user
from src.core.teacher_copilot.evidence_engine import EvidenceEngine
from src.core.teacher_copilot.intent_router import IntentRouter
from src.core.teacher_copilot.pipeline import build_teacher_pipeline
from src.core.teacher_copilot.reasoning_engine import ReasoningEngine
from src.core.teacher_copilot.state import TeacherCopilotState
from src.database.models import User
from src.database.session import get_session
from src.llm.router import ModelRouter
from src.schemas.streaming import TokenChunk

logger = structlog.get_logger()
router = APIRouter(prefix="/copilot", tags=["Teacher Copilot"])


class CopilotQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str
    classroom_id: UUID | None = None
    student_id: UUID | None = None
    workspace_id: UUID | None = None
    stream: bool = False


class CopilotResponse(BaseModel):
    response: str
    intent: str
    intent_confidence: float
    reasoning: str
    evidence: list[dict]
    confidence: float


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


@router.post("/query")
async def copilot_query(
    body: CopilotQuery,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    x_workspace_id: str | None = Header(default=None),
):
    from src.core.workspace.dependencies import resolve_workspace_access

    workspace_id = await resolve_workspace_access(
        str(body.workspace_id) if body.workspace_id else x_workspace_id,
        current_user,
        session,
    )

    if body.stream:
        return await _handle_copilot_stream(body, current_user, session, workspace_id)

    router = ModelRouter()

    initial_state = TeacherCopilotState(
        user_message=body.message,
        user_id=body.student_id,
        teacher_id=current_user.id,
        classroom_id=body.classroom_id,
        workspace_id=UUID(workspace_id) if workspace_id else None,
    )

    pipeline = build_teacher_pipeline(router=router, session=session)
    try:
        final_state = await pipeline.ainvoke(initial_state)
    except Exception as e:
        logger.error("copilot_pipeline_error", error=str(e))

    if final_state.error:
        raise HTTPException(status_code=500, detail=final_state.error)

    return CopilotResponse(
        response=final_state.response_text,
        intent=final_state.intent,
        intent_confidence=final_state.intent_confidence,
        reasoning=final_state.reasoning,
        evidence=final_state.evidence,
        confidence=final_state.confidence,
    )


async def _handle_copilot_stream(
    body: CopilotQuery,
    current_user: User,
    session: AsyncSession,
    workspace_id: str | None = None,
) -> StreamingResponse:
    router = ModelRouter()
    queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()

    initial_state = TeacherCopilotState(
        user_message=body.message,
        user_id=body.student_id,
        teacher_id=current_user.id,
        classroom_id=body.classroom_id,
        workspace_id=UUID(workspace_id) if workspace_id else None,
        token_queue=queue,
    )

    pipeline = build_teacher_pipeline(router=router, session=session)
    task = asyncio.create_task(pipeline.ainvoke(initial_state))

    return StreamingResponse(
        _stream_events(queue, task),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/classify")
async def classify_intent(
    body: CopilotQuery,
    current_user: User = Depends(get_current_user),
):
    intent_router = IntentRouter()
    intent, confidence, reasoning = await intent_router.classify(body.message)
    return {"intent": intent, "confidence": confidence, "reasoning": reasoning}


@router.post("/reason")
async def reason(
    body: CopilotQuery,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    x_workspace_id: str | None = Header(default=None),
):
    from src.core.workspace.dependencies import resolve_workspace_access

    workspace_id = await resolve_workspace_access(
        str(body.workspace_id) if body.workspace_id else x_workspace_id,
        current_user,
        session,
    )

    intent_router = IntentRouter()
    intent, _, _ = await intent_router.classify(body.message)

    evidence_engine = EvidenceEngine()
    evidence = await evidence_engine.gather_evidence(
        intent=intent,
        user_id=body.student_id,
        session=session,
        workspace_id=UUID(workspace_id) if workspace_id else None,
    )
    citations = EvidenceEngine.format_citations(evidence)

    reasoning_engine = ReasoningEngine(router=ModelRouter())
    reasoning, confidence = await reasoning_engine.reason(intent=intent)

    return {
        "intent": intent,
        "reasoning": reasoning,
        "evidence": evidence,
        "citations": citations,
        "confidence": confidence,
    }
