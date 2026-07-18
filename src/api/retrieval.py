from __future__ import annotations

import structlog
from fastapi import APIRouter, Query

from src.core.knowledge_registry.service import KnowledgeRegistry
from src.core.retrieval.evidence_package import EvidencePackageBuilder
from src.core.retrieval.gateway import RetrievalGateway
from src.core.retrieval.models import EvidencePackage

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])

_registry: KnowledgeRegistry | None = None
_gateway: RetrievalGateway | None = None
_package_builder: EvidencePackageBuilder | None = None


def _get_registry() -> KnowledgeRegistry:
    global _registry
    if _registry is None:
        from src.database.session import async_session_factory

        _registry = KnowledgeRegistry(async_session_factory())
    return _registry


def _get_gateway() -> RetrievalGateway:
    global _gateway
    if _gateway is None:
        from src.config import settings
        from src.rag.embedder import Embedder
        from src.rag.vector_store import VectorStore

        _gateway = RetrievalGateway(
            embedder=Embedder(),
            vector_store=VectorStore(
                persist_directory=settings.vector_store_path,
                collection_name=settings.collection_name,
            ),
            registry=_get_registry(),
        )
    return _gateway


def _get_builder() -> EvidencePackageBuilder:
    global _package_builder
    if _package_builder is None:
        from src.core.retrieval.citation import CitationFormatter

        _package_builder = EvidencePackageBuilder(CitationFormatter())
    return _package_builder


@router.get("/search", response_model=EvidencePackage)
async def search(
    q: str = Query(..., min_length=1),
    workspace_id: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    results = await _get_gateway().search(q=q, workspace_id=workspace_id, limit=limit)
    pkg = _get_builder().build(query=q, results=results)
    return pkg
