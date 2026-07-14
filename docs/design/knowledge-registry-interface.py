"""Knowledge Registry — 4-method interface.

All complexity (versions, lifecycle transitions, storage, indexing) is hidden
inside the implementation. Every update snapshots the previous KO state as a
version automatically — callers never think about versioning.
"""

import enum
from datetime import datetime
from uuid import UUID

from src.schemas.base import SchemaModel

# ─── Enums ───────────────────────────────────────────────────────────────

class LifecycleState(str, enum.Enum):
    pending = "pending"           # uploaded, not yet processed
    processing = "processing"     # in pipeline
    enriched = "enriched"         # metadata pipeline complete
    failed = "failed"             # pipeline error
    archived = "archived"         # soft-deleted / deprecated


class KOType(str, enum.Enum):
    document = "document"
    quiz = "quiz"
    lesson = "lesson"
    concept = "concept"
    video = "video"


# ─── Models (what goes in / what comes out) ─────────────────────────────

class RegisterKnowledge(SchemaModel):
    """Payload for registering a new Knowledge Object."""
    type: KOType
    workspace_id: UUID
    owner_id: UUID
    title: str
    source_uri: str | None = None          # original file / external URL
    collection_id: UUID | None = None      # folder/collection grouping
    metadata: dict = {}                     # caller-specific blobs


class KnowledgeObject(SchemaModel):
    """Full read model — returned by get() and list()."""

    id: UUID
    version: int = 1
    type: KOType
    workspace_id: UUID
    owner_id: UUID
    title: str
    state: LifecycleState = LifecycleState.pending
    collection_id: UUID | None = None
    source_uri: str | None = None
    metadata: dict = {}
    deleted: bool = False
    created_at: datetime
    updated_at: datetime


class KnowledgeFilter(SchemaModel):
    """All filter dimensions in one model — passed only to list()."""
    workspace_id: UUID | None = None
    collection_id: UUID | None = None
    owner_id: UUID | None = None
    state: LifecycleState | None = None
    type: KOType | None = None
    include_deleted: bool = False


class KnowledgeUpdate(SchemaModel):
    """Single model for *any* mutation — state, metadata, or delete.

    Only set the fields you want to change. None = no change.
    Hidden internally: every update creates a version snapshot.
    """
    state: LifecycleState | None = None
    metadata: dict | None = None            # deep-merge into existing
    title: str | None = None
    collection_id: UUID | None = None
    deleted: bool | None = None             # set True → soft delete


class VersionRecord(SchemaModel):
    """Lightweight history entry — returned by get(include_versions=True)."""
    version: int
    state: LifecycleState
    snapshot: dict                          # frozen KO state at that version
    created_at: datetime


# ─── Interface (4 methods) ──────────────────────────────────────────────

class KnowledgeRegistry:
    """System of record for Knowledge Objects — 4-method surface."""

    async def register(self, cmd: RegisterKnowledge) -> KnowledgeObject:
        """Create a new Knowledge Object. Returns the created record."""
        ...

    async def get(
        self,
        ko_id: UUID,
        *,
        version: int | None = None,
        include_versions: bool = False,
    ) -> tuple[KnowledgeObject, list[VersionRecord] | None]:
        """Retrieve KO by ID. Optionally pin a specific version.

        Returns (ko, versions | None).
        """
        ...

    async def list(
        self,
        filter: KnowledgeFilter | None = None,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[KnowledgeObject], int]:
        """Filtered listing with total count. Omit filter → scan all."""
        ...

    async def update(self, ko_id: UUID, cmd: KnowledgeUpdate) -> KnowledgeObject:
        """Single entry point for ALL mutations.

        Handles: state transitions, metadata enrichment, title changes,
        re-parenting (collection_id), and soft delete.

        Hidden internally:
        - Auto-snapshots the previous version before applying changes
        - Validates lifecycle state transitions
        - Deep-merges metadata dict (not replace)
        - Raises on conflict (e.g. update on deleted KO)
        """
        ...


# ─── Usage examples ─────────────────────────────────────────────────────

async def usage_upload_service(registry: KnowledgeRegistry) -> KnowledgeObject:
    """Upload Service calls one method."""
    return await registry.register(
        RegisterKnowledge(
            type=KOType.document,
            workspace_id=UUID("..."),
            owner_id=UUID("..."),
            title="Cell Biology Chapter 3",
            source_uri="s3://uploads/cell-bio-ch3.pdf",
        )
    )


async def usage_processing_service(registry: KnowledgeRegistry, ko_id: UUID) -> KnowledgeObject:
    """Processing Service calls one method with different payloads."""
    # Pipeline: pending → processing → enriched (or → failed)
    await registry.update(ko_id, KnowledgeUpdate(state=LifecycleState.processing))
    # ... do OCR / chunking / embedding ...
    return await registry.update(
        ko_id,
        KnowledgeUpdate(
            state=LifecycleState.enriched,
            metadata={"chunk_count": 42, "embedding_model": "gte-small"},
        ),
    )


async def usage_retrieval_gateway(registry: KnowledgeRegistry, ko_id: UUID) -> KnowledgeObject:
    """Retrieval Gateway calls two methods."""
    ko, _ = await registry.get(ko_id)
    if ko.state != LifecycleState.enriched:
        raise ValueError("Not ready for retrieval")
    return ko


async def usage_frontend_api(registry: KnowledgeRegistry) -> list[KnowledgeObject]:
    """Frontend delegates HTTP params → KnowledgeFilter, then list()."""
    results, total = await registry.list(
        KnowledgeFilter(
            workspace_id=UUID("..."),
            state=LifecycleState.enriched,
            type=KOType.quiz,
        ),
        offset=0,
        limit=20,
    )
    return results


# ─── What complexity is hidden internally ───────────────────────────────
#
# 1. Version management — every update() snapshots the pre-mutation state.
#    Callers never manually create/list versions; get(version=N) retrieves
#    frozen snapshots.
#
# 2. Lifecycle state machine — update() validates legal transitions
#    (e.g. enriched→processing is rejected).
#
# 3. Soft-delete isolation — deleted KOs are excluded from list() by default
#    (filter.include_deleted overrides). get() still works for direct reads.
#
# 4. Metadata deep-merge — update(metadata={...}) merges into existing;
#    callers don't need to read-then-write.
#
# 5. Storage / indexing / cache — the implementation owns persistence,
#    materialized views for listing, and any caching layer.
#
# 6. Idempotency guard — update() on non-existent KO_id raises immediately.
#
# ─── Trade-offs ─────────────────────────────────────────────────────────
#
# + Callers learn 4 methods. That's it. No cognitive load.
# + Adding new mutable fields = adding optional fields to KnowledgeUpdate.
#   No new methods, no caller changes unless they want the new field.
# + Testing: 4 methods × a few scenarios = small test matrix.
# + Versioning is free — every caller gets it without opting in.
#
# - Every mutation goes through one method → the update() signature is a
#   bag of optional fields. Callers must know which subset they need.
# - No type-level distinction between "state update" and "metadata update" —
#   the type system can't enforce that Processing Service only sets state+metadata
#   while Frontend only sets title+collection_id. Runtime validation only.
# - get() returns versions inline (as a tuple). Callers that never need
#   versions still receive it. Could push to a separate get_versions()
#   method, but that violates the "4-method max" constraint.
