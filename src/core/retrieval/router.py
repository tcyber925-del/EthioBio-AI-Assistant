from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.retrieval.models import RoutingPlan

if TYPE_CHECKING:
    from src.core.retrieval.gateway import RetrievalGateway


def create_knowledge_router() -> "KnowledgeRouter":
    """Build a workspace-capable router (KML gateway) for AI components."""
    from src.config import settings
    from src.core.knowledge_registry import KnowledgeRegistry
    from src.core.retrieval.gateway import RetrievalGateway
    from src.database.session import async_session_factory
    from src.rag.embedder import Embedder
    from src.rag.vector_store import VectorStore

    gateway = RetrievalGateway(
        embedder=Embedder(),
        vector_store=VectorStore(
            persist_directory=settings.vector_store_path,
            collection_name=settings.collection_name,
        ),
        registry=KnowledgeRegistry(async_session_factory()),
    )
    return KnowledgeRouter(gateway)


class KnowledgeRouter:
    """Thin routing facade that selects between KML pipeline and legacy path.

    - workspace_id present → KML path (gateway)
    - no workspace_id → legacy path (strangler fig — current default)
    """

    def __init__(self, gateway: RetrievalGateway | None = None):
        self._gateway = gateway

    def route(
        self,
        query: str,
        workspace_id: str | None = None,
        user_id: str | None = None,
    ) -> RoutingPlan:
        if workspace_id:
            layers = ["workspace"]
            primary_source = "kml"
        else:
            layers = ["curriculum"]
            primary_source = "legacy"
        return RoutingPlan(
            layers=layers,
            primary_source=primary_source,
            strategy="vector_only",
        )

    async def route_and_search(
        self,
        query: str,
        workspace_id: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
    ) -> list:
        plan = self.route(query, workspace_id, user_id)
        if plan.primary_source == "kml" and self._gateway:
            results = await self._gateway.search(q=query, workspace_id=workspace_id, limit=limit)
            return results
        return []
