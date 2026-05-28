from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.memory.event_logger import EventLogger
from src.core.memory.retrieval_orchestrator import RetrievalOrchestrator
from src.core.memory.session_manager import SessionManager
from src.core.memory.socratic_manager import SocraticManager
from src.core.memory.summarizer import Summarizer
from src.database.models import MemoryEducationalSummary, MemoryEvent, MemorySession
from src.database.session import get_session
from src.schemas.memory import (
    MemoryEventListResponse,
    MemoryEventRequest,
    MemoryEventResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResult,
    SessionCloseResponse,
    SessionHeartbeatResponse,
    SessionResponse,
    SessionStartRequest,
    SessionStartResponse,
    SocraticStateResponse,
    SocraticStateUpdateRequest,
    SummarizeRequest,
    SummarizeResponse,
    SummaryListResponse,
    SummaryResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/memory", tags=["Memory"])

session_manager = SessionManager()
socratic_manager = SocraticManager()
event_logger = EventLogger()
retrieval_orchestrator = RetrievalOrchestrator()


@router.post("/session/start", response_model=SessionStartResponse)
async def start_session(
    request: SessionStartRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        session = await session_manager.get_or_create_active_session(
            user_id=request.user_id,
            topic=request.topic,
            tutoring_mode=request.tutoring_mode,
            db=db,
        )
        await event_logger.log(
            request.user_id, "session_started",
            topic=request.topic, db=db,
        )
        await db.commit()
        return SessionStartResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            active_topic=session.active_topic,
            tutoring_mode=session.tutoring_mode,
            started_at=session.started_at,
            last_active_at=session.last_active_at,
        )
    except Exception as e:
        await db.rollback()
        logger.error("session_start_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{user_id}/active", response_model=SessionResponse | None)
async def get_active_session(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    try:
        session = await session_manager.get_active_session_for_user(user_id, db)
        if not session:
            return None
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            active_topic=session.active_topic,
            tutoring_mode=session.tutoring_mode,
            educational_context=session.educational_context,
            unresolved_questions=session.unresolved_questions or [],
            started_at=session.started_at,
            last_active_at=session.last_active_at,
            summary=session.summary,
        )
    except Exception as e:
        logger.error("active_session_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/session/{session_id}/heartbeat", response_model=SessionHeartbeatResponse)
async def heartbeat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    try:
        session = await session_manager.heartbeat(session_id, db)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        await db.commit()
        return SessionHeartbeatResponse(
            session_id=session.session_id,
            last_active_at=session.last_active_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("session_heartbeat_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/{session_id}/close", response_model=SessionCloseResponse)
async def close_session(
    session_id: UUID,
    request: SummarizeRequest | None = None,
    db: AsyncSession = Depends(get_session),
):
    try:
        ctx = request.conversation_context if request else None
        session = await session_manager.close_session(session_id, db, conversation_context=ctx)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        await event_logger.log(
            session.user_id, "session_closed",
            topic=session.active_topic, db=db,
        )
        await db.commit()

        summary_detail = None
        if session.summary:
            from sqlalchemy import select
            result = await db.execute(
                select(MemoryEducationalSummary)
                .where(MemoryEducationalSummary.embedding_id == str(session_id))
                .order_by(MemoryEducationalSummary.created_at.desc())
                .limit(1)
            )
            db_summary = result.scalar_one_or_none()
            if db_summary:
                summary_detail = SummarizeResponse(
                    summary_id=db_summary.id,
                    topic=db_summary.topic,
                    understanding_level=db_summary.understanding_level,
                    key_misconceptions=db_summary.key_misconceptions or [],
                    confidence=db_summary.confidence,
                    next_learning_goal=db_summary.next_learning_goal,
                    created_at=db_summary.created_at,
                )

        return SessionCloseResponse(
            session_id=session.session_id,
            summary=session.summary,
            summary_detail=summary_detail,
            closed=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("session_close_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize/{session_id}", response_model=SummarizeResponse)
async def summarize_session(
    session_id: UUID,
    request: SummarizeRequest | None = None,
    db: AsyncSession = Depends(get_session),
):
    try:
        from sqlalchemy import select
        result = await db.execute(
            select(MemoryEducationalSummary)
            .where(MemoryEducationalSummary.embedding_id == str(session_id))
            .order_by(MemoryEducationalSummary.created_at.desc())
            .limit(1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return SummarizeResponse(
                summary_id=existing.id,
                topic=existing.topic,
                understanding_level=existing.understanding_level,
                key_misconceptions=existing.key_misconceptions or [],
                confidence=existing.confidence,
                next_learning_goal=existing.next_learning_goal,
                created_at=existing.created_at,
            )

        session_result = await db.execute(
            select(MemorySession).where(MemorySession.session_id == session_id)
        )
        session = session_result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        ctx = request.conversation_context if request else None
        summarizer = Summarizer()
        summary = await summarizer.summarize_session(session, conversation_context=ctx, db=db)
        if not summary:
            raise HTTPException(status_code=500, detail="Summarization failed")

        await db.commit()
        return SummarizeResponse(
            summary_id=summary.id,
            topic=summary.topic,
            understanding_level=summary.understanding_level,
            key_misconceptions=summary.key_misconceptions or [],
            confidence=summary.confidence,
            next_learning_goal=summary.next_learning_goal,
            created_at=summary.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("summarize_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/socratic/{user_id}/{topic}", response_model=SocraticStateResponse | None)
async def get_socratic_state(
    user_id: UUID,
    topic: str,
    db: AsyncSession = Depends(get_session),
):
    try:
        state = await socratic_manager.get_state(user_id, topic, db)
        if not state:
            return None
        return SocraticStateResponse(
            user_id=state.user_id,
            topic=state.topic,
            socratic_stage=state.socratic_stage,
            current_focus=state.current_focus,
            student_understanding=state.student_understanding,
            next_question=state.next_question,
            conceptual_gaps=state.conceptual_gaps or [],
            updated_at=state.updated_at,
        )
    except Exception as e:
        logger.error("socratic_state_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/socratic/{user_id}/{topic}", response_model=SocraticStateResponse)
async def update_socratic_state(
    user_id: UUID,
    topic: str,
    request: SocraticStateUpdateRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        updates = request.model_dump(exclude_none=True)
        updates.pop("user_id", None)
        updates.pop("topic", None)
        state = await socratic_manager.update_state(user_id, topic, updates, db)
        await db.commit()
        return SocraticStateResponse(
            user_id=state.user_id,
            topic=state.topic,
            socratic_stage=state.socratic_stage,
            current_focus=state.current_focus,
            student_understanding=state.student_understanding,
            next_question=state.next_question,
            conceptual_gaps=state.conceptual_gaps or [],
            updated_at=state.updated_at,
        )
    except Exception as e:
        await db.rollback()
        logger.error("socratic_state_update_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events", response_model=MemoryEventResponse)
async def log_memory_event(
    request: MemoryEventRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        event = await event_logger.log(
            request.user_id, request.event_type,
            topic=request.topic, metadata=request.event_metadata, db=db,
        )
        await db.commit()
        if event is None:
            raise HTTPException(status_code=500, detail="Failed to log event")
        return MemoryEventResponse(
            id=event.id,
            user_id=event.user_id,
            event_type=event.event_type,
            topic=event.topic,
            event_metadata=event.event_metadata,
            created_at=event.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("memory_event_log_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/{user_id}", response_model=MemoryEventListResponse)
async def get_memory_events(
    user_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    try:
        result = await db.execute(
            select(MemoryEvent)
            .where(MemoryEvent.user_id == user_id)
            .order_by(MemoryEvent.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()
        return MemoryEventListResponse(
            events=[
                MemoryEventResponse(
                    id=e.id,
                    user_id=e.user_id,
                    event_type=e.event_type,
                    topic=e.topic,
                    event_metadata=e.event_metadata,
                    created_at=e.created_at,
                )
                for e in events
            ],
            total=len(events),
        )
    except Exception as e:
        logger.error("memory_events_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summaries/{user_id}", response_model=SummaryListResponse)
async def get_educational_summaries(
    user_id: UUID,
    topic: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_session),
):
    try:
        stmt = select(MemoryEducationalSummary).where(
            MemoryEducationalSummary.user_id == user_id,
        )
        if topic:
            stmt = stmt.where(MemoryEducationalSummary.topic == topic)
        stmt = stmt.order_by(MemoryEducationalSummary.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        summaries = result.scalars().all()
        return SummaryListResponse(
            summaries=[
                SummaryResponse(
                    id=s.id,
                    user_id=s.user_id,
                    topic=s.topic,
                    understanding_level=s.understanding_level,
                    key_misconceptions=s.key_misconceptions or [],
                    confidence=s.confidence,
                    next_learning_goal=s.next_learning_goal,
                    created_at=s.created_at,
                )
                for s in summaries
            ],
            total=len(summaries),
        )
    except Exception as e:
        logger.error("summaries_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(request: MemorySearchRequest):
    try:
        results = await retrieval_orchestrator.search(
            query=request.query,
            n_results=request.n_results,
            topic=request.topic,
            user_id=request.user_id,
        )
        return MemorySearchResponse(
            results=[
                MemorySearchResult(
                    memory_id=r.memory_id,
                    content=r.content,
                    metadata=r.metadata,
                    score=r.score,
                    similarity=r.similarity,
                )
                for r in results
            ],
            total=len(results),
        )
    except Exception as e:
        logger.error("memory_search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def memory_health(db: AsyncSession = Depends(get_session)):
    try:
        summary_count_result = await db.execute(
            select(func.count(MemoryEducationalSummary.id))
        )
        session_count_result = await db.execute(
            select(func.count(MemorySession.session_id))
            .where(MemorySession.summary.is_(None))
        )
        event_count_result = await db.execute(
            select(func.count(MemoryEvent.id))
        )

        summary_count = summary_count_result.scalar() or 0
        active_sessions = session_count_result.scalar() or 0
        event_count = event_count_result.scalar() or 0

        chroma_count = 0
        try:
            from src.core.memory.vector_store import MemoryVectorStore
            store = MemoryVectorStore()
            chroma_count = store.count()
        except Exception as e:
            logger.warning("memory_health_chroma_error", error=str(e))

        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "educational_summaries": summary_count,
            "active_sessions": active_sessions,
            "memory_events": event_count,
            "chromadb_embeddings": chroma_count,
        }
    except Exception as e:
        logger.error("memory_health_error", error=str(e))
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": str(e),
        }
