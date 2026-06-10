from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.tracing import TraceRepository
from src.database.session import async_session_factory
from src.schemas.tracing import TraceDeleteResponse, TraceListResponse, TraceResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/traces", tags=["Tracing"])


def get_trace_repository() -> TraceRepository:
    maker = async_session_factory()
    return TraceRepository(maker)


@router.get("", response_model=TraceListResponse)
async def list_traces(
    status: Optional[str] = Query(None, description="Filter by status"),
    user_id: Optional[UUID] = Query(None, description="Filter by user UUID"),
    intent: Optional[str] = Query(None, description="Filter by intent"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: TraceRepository = Depends(get_trace_repository),
):
    try:
        traces, total = await repo.list_traces(
            status=status,
            user_id=user_id,
            intent=intent,
            limit=limit,
            offset=offset,
        )
        return TraceListResponse(
            traces=[TraceResponse(**t) for t in traces],
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error("list_traces_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    repo: TraceRepository = Depends(get_trace_repository),
):
    try:
        trace = await repo.get_trace(trace_id)
        if trace is None:
            raise HTTPException(status_code=404, detail="Trace not found")
        return TraceResponse(**trace)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_trace_error", trace_id=trace_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{trace_id}", response_model=TraceDeleteResponse)
async def delete_trace(
    trace_id: str,
    repo: TraceRepository = Depends(get_trace_repository),
):
    try:
        deleted = await repo.delete_trace(trace_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Trace not found")
        return TraceDeleteResponse(deleted=True, trace_id=trace_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_trace_error", trace_id=trace_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
