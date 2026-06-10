from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import structlog
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AgentTrace

logger = structlog.get_logger()


class TraceRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def _get_session(self) -> AsyncSession:
        return self._session_factory()

    async def save_trace(
        self,
        trace_id: str,
        start_time: datetime,
        status: str,
        user_message: str,
        response: Optional[str] = None,
        end_time: Optional[datetime] = None,
        error: Optional[str] = None,
        user_id: Optional[UUID] = None,
        grade_level: Optional[int] = None,
        language: Optional[str] = None,
        intent: Optional[str] = None,
        nodes_visited: Optional[list] = None,
        node_timings: Optional[dict] = None,
        metadata: Optional[dict] = None,
        duration_ms: float = 0.0,
    ) -> None:
        session = await self._get_session()
        try:
            trace = AgentTrace(
                trace_id=trace_id,
                start_time=start_time,
                end_time=end_time,
                status=status,
                error=error,
                user_message=user_message,
                response=response,
                user_id=user_id,
                grade_level=grade_level,
                language=language,
                intent=intent,
                nodes_visited=nodes_visited or [],
                node_timings=node_timings or {},
                event_metadata=metadata or {},
                duration_ms=duration_ms,
            )
            session.add(trace)
            await session.flush()
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("save_trace_failed", trace_id=trace_id)
        finally:
            await session.close()

    async def get_trace(self, trace_id: str) -> Optional[dict]:
        session = await self._get_session()
        try:
            result = await session.execute(
                select(AgentTrace).where(AgentTrace.trace_id == trace_id)
            )
            trace = result.scalar_one_or_none()
            if trace is None:
                return None
            return self._to_dict(trace)
        finally:
            await session.close()

    async def list_traces(
        self,
        status: Optional[str] = None,
        user_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        intent: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        session = await self._get_session()
        try:
            query = select(AgentTrace)
            count_query = select(func.count(AgentTrace.trace_id))

            if status:
                query = query.where(AgentTrace.status == status)
                count_query = count_query.where(AgentTrace.status == status)
            if user_id:
                query = query.where(AgentTrace.user_id == user_id)
                count_query = count_query.where(AgentTrace.user_id == user_id)
            if date_from:
                query = query.where(AgentTrace.start_time >= date_from)
                count_query = count_query.where(AgentTrace.start_time >= date_from)
            if date_to:
                query = query.where(AgentTrace.start_time <= date_to)
                count_query = count_query.where(AgentTrace.start_time <= date_to)
            if intent:
                query = query.where(AgentTrace.intent == intent)
                count_query = count_query.where(AgentTrace.intent == intent)

            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0

            query = query.order_by(AgentTrace.start_time.desc())
            query = query.offset(offset).limit(limit)

            result = await session.execute(query)
            traces = result.scalars().all()

            return [self._to_dict(t) for t in traces], total
        finally:
            await session.close()

    async def delete_trace(self, trace_id: str) -> bool:
        session = await self._get_session()
        try:
            result = await session.execute(
                select(AgentTrace).where(AgentTrace.trace_id == trace_id)
            )
            trace = result.scalar_one_or_none()
            if trace is None:
                return False
            await session.delete(trace)
            await session.flush()
            await session.commit()
            return True
        except Exception:
            await session.rollback()
            logger.exception("delete_trace_failed", trace_id=trace_id)
            return False
        finally:
            await session.close()

    async def cleanup_old(self, max_age_days: int = 30) -> int:
        session = await self._get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            result = await session.execute(
                select(AgentTrace).where(AgentTrace.start_time < cutoff)
            )
            old_traces = result.scalars().all()
            count = len(old_traces)
            for t in old_traces:
                await session.delete(t)
            await session.flush()
            await session.commit()
            logger.info("cleanup_old_traces", count=count, max_age_days=max_age_days)
            return count
        except Exception:
            await session.rollback()
            logger.exception("cleanup_traces_failed")
            return 0
        finally:
            await session.close()

    @staticmethod
    def _to_dict(trace: AgentTrace) -> dict:
        return {
            "trace_id": trace.trace_id,
            "start_time": trace.start_time.isoformat() if trace.start_time else None,
            "end_time": trace.end_time.isoformat() if trace.end_time else None,
            "status": trace.status,
            "error": trace.error,
            "user_message": trace.user_message,
            "response": trace.response,
            "user_id": str(trace.user_id) if trace.user_id else None,
            "grade_level": trace.grade_level,
            "language": trace.language,
            "intent": trace.intent,
            "nodes_visited": trace.nodes_visited,
            "node_timings": trace.node_timings,
            "metadata": trace.event_metadata,
            "duration_ms": trace.duration_ms,
        }
