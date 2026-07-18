from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.memory.event_logger import EventLogger
from src.core.memory.retrieval_orchestrator import RetrievalOrchestrator
from src.core.memory.semantic_manager import SemanticFactManager
from src.core.memory.session_manager import SessionManager
from src.core.memory.socratic_manager import SocraticManager
from src.core.memory.summarizer import Summarizer
from src.database.models import (
    ConversationTurn,
    MemoryEducationalSummary,
    MemoryEvent,
    MemorySession,
)
from src.database.session import get_session
from src.schemas.memory import (
    MemoryEventListResponse,
    MemoryEventRequest,
    MemoryEventResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemorySearchResult,
    SemanticFactCreateRequest,
    SemanticFactListResponse,
    SemanticFactResponse,
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
    TimelineEntryResponse,
    TimelineResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/memory", tags=["Memory"])

session_manager = SessionManager()
socratic_manager = SocraticManager()
event_logger = EventLogger()
retrieval_orchestrator = RetrievalOrchestrator()
semantic_manager = SemanticFactManager()


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
            request.user_id,
            "session_started",
            topic=request.topic,
            db=db,
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
            session.user_id,
            "session_closed",
            topic=session.active_topic,
            db=db,
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
            request.user_id,
            request.event_type,
            topic=request.topic,
            metadata=request.event_metadata,
            db=db,
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


@router.get("/timeline/{user_id}", response_model=TimelineResponse)
async def get_timeline(
    user_id: UUID,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    try:
        events_query = select(
            MemoryEvent.id.label("entry_id"),
            MemoryEvent.event_type.label("entry_type"),
            MemoryEvent.created_at.label("timestamp"),
        ).where(MemoryEvent.user_id == user_id)
        from sqlalchemy import case, literal

        events_query = events_query.add_columns(
            literal("memory_event").label("source"),
            MemoryEvent.event_metadata,
            MemoryEvent.topic,
            case(
                (MemoryEvent.event_type == "quiz_completed", "Completed a quiz"),
                (MemoryEvent.event_type == "session_started", "Started a tutoring session"),
                (MemoryEvent.event_type == "lesson_viewed", "Viewed a lesson"),
                (MemoryEvent.event_type == "recovery_task_done", "Completed a recovery task"),
                else_=MemoryEvent.event_type,
            ).label("summary"),
        )

        turns_query = (
            select(
                ConversationTurn.id.label("entry_id"),
                literal("conversation_turn").label("entry_type"),
                ConversationTurn.created_at.label("timestamp"),
                literal("conversation_turn").label("source"),
                literal({}).label("event_metadata"),
                ConversationTurn.topic,
                ConversationTurn.content.label("summary"),
            )
            .where(ConversationTurn.user_id == user_id)
            .where(ConversationTurn.role == "student")
        )

        if start_date:
            from datetime import datetime

            parsed_start = datetime.fromisoformat(start_date)
            events_query = events_query.where(MemoryEvent.created_at >= parsed_start)
            turns_query = turns_query.where(ConversationTurn.created_at >= parsed_start)

        if end_date:
            from datetime import datetime

            parsed_end = datetime.fromisoformat(end_date)
            events_query = events_query.where(MemoryEvent.created_at <= parsed_end)
            turns_query = turns_query.where(ConversationTurn.created_at <= parsed_end)

        events_query = events_query.order_by(MemoryEvent.created_at.desc())
        turns_query = turns_query.order_by(ConversationTurn.created_at.desc())

        events_result = await db.execute(events_query.limit(limit))
        turns_result = await db.execute(turns_query.limit(limit))

        def row_to_entry(row) -> TimelineEntryResponse:
            return TimelineEntryResponse(
                entry_id=row.entry_id,
                entry_type=row.entry_type,
                summary=str(row.summary or "")[:200],
                topic=row.topic,
                metadata=dict(row.event_metadata) if row.event_metadata else {},
                timestamp=row.timestamp,
            )

        event_entries = [row_to_entry(r) for r in events_result]
        turn_entries = [row_to_entry(r) for r in turns_result]

        combined = sorted(
            event_entries + turn_entries,
            key=lambda e: e.timestamp,
            reverse=True,
        )[:limit]

        return TimelineResponse(entries=combined, total=len(combined))
    except Exception as e:
        logger.error("timeline_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facts/{user_id}", response_model=SemanticFactListResponse)
async def list_semantic_facts(
    user_id: UUID,
    category: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_session),
):
    try:
        facts = await semantic_manager.list_by_user(
            db=db,
            user_id=user_id,
            category=category,
            limit=limit,
        )
        return SemanticFactListResponse(
            facts=[
                SemanticFactResponse(
                    id=f.id,
                    user_id=f.user_id,
                    fact_key=f.fact_key,
                    fact_value=f.fact_value,
                    category=f.category,
                    confidence=f.confidence,
                    source_event_id=f.source_event_id,
                    is_active=f.is_active,
                    consolidated_at=f.consolidated_at,
                    created_at=f.created_at,
                    updated_at=f.updated_at,
                )
                for f in facts
            ],
            total=len(facts),
        )
    except Exception as e:
        logger.error("semantic_facts_list_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/facts/{user_id}", response_model=SemanticFactResponse)
async def create_semantic_fact(
    user_id: UUID,
    request: SemanticFactCreateRequest,
    db: AsyncSession = Depends(get_session),
):
    try:
        fact = await semantic_manager.upsert(
            db=db,
            user_id=user_id,
            fact_key=request.fact_key,
            fact_value=request.fact_value,
            category=request.category,
            confidence=request.confidence,
            source_event_id=request.source_event_id,
        )
        await db.commit()
        return SemanticFactResponse(
            id=fact.id,
            user_id=fact.user_id,
            fact_key=fact.fact_key,
            fact_value=fact.fact_value,
            category=fact.category,
            confidence=fact.confidence,
            source_event_id=fact.source_event_id,
            is_active=fact.is_active,
            consolidated_at=fact.consolidated_at,
            created_at=fact.created_at,
            updated_at=fact.updated_at,
        )
    except Exception as e:
        await db.rollback()
        logger.error("semantic_fact_create_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facts/{user_id}/{fact_key}", response_model=SemanticFactResponse)
async def get_semantic_fact(
    user_id: UUID,
    fact_key: str,
    db: AsyncSession = Depends(get_session),
):
    try:
        fact = await semantic_manager.get(user_id=user_id, fact_key=fact_key, db=db)
        if not fact:
            raise HTTPException(status_code=404, detail="Semantic fact not found")
        return SemanticFactResponse(
            id=fact.id,
            user_id=fact.user_id,
            fact_key=fact.fact_key,
            fact_value=fact.fact_value,
            category=fact.category,
            confidence=fact.confidence,
            source_event_id=fact.source_event_id,
            is_active=fact.is_active,
            consolidated_at=fact.consolidated_at,
            created_at=fact.created_at,
            updated_at=fact.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("semantic_fact_get_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/facts/{user_id}/{fact_key}")
async def delete_semantic_fact(
    user_id: UUID,
    fact_key: str,
    db: AsyncSession = Depends(get_session),
):
    try:
        success = await semantic_manager.deactivate(user_id=user_id, fact_key=fact_key, db=db)
        await db.commit()
        if not success:
            raise HTTPException(status_code=404, detail="Semantic fact not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("semantic_fact_delete_error", error=str(e))
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
        summary_count_result = await db.execute(select(func.count(MemoryEducationalSummary.id)))
        session_count_result = await db.execute(
            select(func.count(MemorySession.session_id)).where(MemorySession.summary.is_(None))
        )
        event_count_result = await db.execute(select(func.count(MemoryEvent.id)))
        fact_count = await semantic_manager.get_count(db=db)

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
            "semantic_facts": fact_count,
            "chromadb_embeddings": chroma_count,
        }
    except Exception as e:
        logger.error("memory_health_error", error=str(e))
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": str(e),
        }
