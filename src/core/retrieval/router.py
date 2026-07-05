from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.retrieval.models import RoutingPlan

if TYPE_CHECKING:
    from src.core.retrieval.gateway import RetrievalGateway


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
            results = await self._gateway.search(
                q=query, workspace_id=workspace_id, limit=limit
            )
            return results
        return []
