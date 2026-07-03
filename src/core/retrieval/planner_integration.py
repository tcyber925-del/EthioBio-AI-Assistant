from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from src.core.retrieval.evidence_package import EvidencePackageBuilder
from src.core.retrieval.gateway import RetrievalGateway
from src.core.retrieval.models import EvidencePackage

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


class PlannerIntegrationService:
    """Bridge between AgentOrchestrator and the KML retrieval pipeline.

    Opt-in by the caller — existing graph nodes (SearchFanoutNode,
    RetrievalNode, TutorNode) continue using VectorStoreAdapter.search()
    directly.
    """

    def __init__(
        self,
        gateway: RetrievalGateway | None = None,
        builder: EvidencePackageBuilder | None = None,
    ):
        self._gateway = gateway
        self._builder = builder or EvidencePackageBuilder()

    async def get_evidence(
        self,
        query: str,
        workspace_id: str | None = None,
        user_id: str | None = None,
        limit: int = 10,
    ) -> EvidencePackage:
        """Convenience: route query through KML gateway and wrap in EvidencePackage."""
        logger.info(
            "planner_integration.get_evidence",
            query=query,
            workspace_id=workspace_id,
            user_id=user_id,
            limit=limit,
        )
        if not self._gateway:
            return EvidencePackage(
                query=query,
                sources=[],
                total_results=0,
                degraded=True,
            )
        results = await self._gateway.search(
            q=query,
            workspace_id=workspace_id,
            limit=limit,
        )
        return self._builder.build(query=query, results=results)
