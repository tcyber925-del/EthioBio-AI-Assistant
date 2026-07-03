from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.knowledge_registry.events import (
    KnowledgeEvent,
    KnowledgeObjectDeleted,
    KnowledgeObjectRegistered,
    LifecycleChanged,
    MetadataUpdated,
    VersionCreated,
)
from src.core.knowledge_registry.models import (
    KnowledgeFilter,
    KnowledgeObject,
    LifecycleState,
    LifecycleTransition,
    NewKnowledgeObject,
)
from src.database.models import KnowledgeObject as KnowledgeObjectModel
from src.database.models import KnowledgeObjectVersion as KnowledgeObjectVersionModel

logger = structlog.get_logger()

_VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.UPLOADED: {LifecycleState.PROCESSING, LifecycleState.FAILED},
    LifecycleState.PROCESSING: {
        LifecycleState.PUBLISHED,
        LifecycleState.ARCHIVED,
        LifecycleState.FAILED,
    },
    LifecycleState.PUBLISHED: {LifecycleState.ACTIVE, LifecycleState.ARCHIVED},
    LifecycleState.ACTIVE: {LifecycleState.PUBLISHED, LifecycleState.ARCHIVED},
    LifecycleState.ARCHIVED: {LifecycleState.ACTIVE, LifecycleState.DELETED},
    LifecycleState.DELETED: set(),
    LifecycleState.FAILED: {LifecycleState.UPLOADED},
}


def _ko_from_orm(row: KnowledgeObjectModel) -> KnowledgeObject:
    return KnowledgeObject(
        id=str(row.id),
        workspace_id=str(row.workspace_id) if row.workspace_id else "",
        collection_id=str(row.collection_id) if row.collection_id else None,
        owner_id=str(row.owner_id),
        title=row.title,
        content_type=row.content_type,
        content_hash=row.content_hash,
        lifecycle_state=LifecycleState(row.lifecycle_state),
        enrichment_status=row.enrichment_status,
        version=row.version,
        metadata=row.ko_metadata or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class KnowledgeRegistry:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def register(
        self, ko: NewKnowledgeObject
    ) -> tuple[KnowledgeObject, list[KnowledgeEvent]]:
        events: list[KnowledgeEvent] = []
        async with self._session_factory() as db:
            row = KnowledgeObjectModel(
                workspace_id=UUID(ko.workspace_id) if ko.workspace_id else None,
                collection_id=UUID(ko.collection_id) if ko.collection_id else None,
                owner_id=UUID(ko.owner_id),
                title=ko.title,
                content_type=ko.content_type,
                content_hash=ko.content_hash,
                metadata=ko.metadata,
            )
            db.add(row)
            await db.flush()

            ko_version = KnowledgeObjectVersionModel(
                ko_id=row.id,
                version=row.version,
                snapshot={
                    "id": str(row.id),
                    "workspace_id": str(row.workspace_id) if row.workspace_id else None,
                    "collection_id": str(row.collection_id) if row.collection_id else None,
                    "owner_id": str(row.owner_id),
                    "title": row.title,
                    "content_type": row.content_type,
                    "content_hash": row.content_hash,
                    "lifecycle_state": row.lifecycle_state,
                    "enrichment_status": row.enrichment_status,
                    "version": row.version,
                    "metadata": row.ko_metadata,
                },
            )
            db.add(ko_version)
            await db.commit()

            result = _ko_from_orm(row)
            events.append(
                KnowledgeObjectRegistered(
                    ko_id=str(row.id),
                    workspace_id=ko.workspace_id,
                    title=ko.title,
                    content_type=ko.content_type,
                    actor_id=ko.owner_id,
                )
            )
            events.append(
                VersionCreated(
                    ko_id=str(row.id),
                    version_number=row.version,
                )
            )
            logger.info("knowledge_object_registered", ko_id=str(row.id))
            return result, events

    async def get(self, ko_id: str) -> KnowledgeObject | None:
        async with self._session_factory() as db:
            row = await db.get(KnowledgeObjectModel, UUID(ko_id))
            if row is None or row.deleted_at is not None:
                return None
            return _ko_from_orm(row)

    async def list_by_filter(self, filter: KnowledgeFilter) -> list[KnowledgeObject]:
        async with self._session_factory() as db:
            query = select(KnowledgeObjectModel).where(KnowledgeObjectModel.deleted_at.is_(None))

            if filter.workspace_id:
                query = query.where(
                    KnowledgeObjectModel.workspace_id == UUID(filter.workspace_id)
                )
            if filter.collection_id:
                query = query.where(
                    KnowledgeObjectModel.collection_id == UUID(filter.collection_id)
                )
            if filter.lifecycle_states:
                query = query.where(
                    KnowledgeObjectModel.lifecycle_state.in_(
                        [s.value for s in filter.lifecycle_states]
                    )
                )
            if filter.enrichment_status:
                query = query.where(
                    KnowledgeObjectModel.enrichment_status == filter.enrichment_status
                )
            if filter.search:
                query = query.where(
                    KnowledgeObjectModel.title.ilike(f"%{filter.search}%")
                )

            query = query.order_by(KnowledgeObjectModel.created_at.desc())
            query = query.offset(filter.offset).limit(filter.limit)

            rows = (await db.execute(query)).scalars().all()
            return [_ko_from_orm(r) for r in rows]

    async def update_lifecycle(
        self, ko_id: str, transition: LifecycleTransition
    ) -> tuple[KnowledgeObject, list[KnowledgeEvent]]:
        events: list[KnowledgeEvent] = []
        async with self._session_factory() as db:
            row = await db.get(KnowledgeObjectModel, UUID(ko_id))
            if row is None:
                raise ValueError(f"KnowledgeObject {ko_id} not found")
            if row.deleted_at is not None:
                raise ValueError(f"KnowledgeObject {ko_id} is deleted")

            from_state = LifecycleState(row.lifecycle_state)
            to_state = transition.to_state
            if to_state not in _VALID_TRANSITIONS.get(from_state, set()):
                raise ValueError(
                    f"Invalid transition from {from_state} to {to_state}"
                )

            old_state = row.lifecycle_state
            row.lifecycle_state = to_state.value
            row.updated_at = datetime.now(timezone.utc)
            await db.commit()

            events.append(
                LifecycleChanged(
                    ko_id=ko_id,
                    from_state=old_state,
                    to_state=to_state.value,
                    reason=transition.reason,
                )
            )
            logger.info("knowledge_object_lifecycle_changed", ko_id=ko_id, to_state=to_state.value)
            return _ko_from_orm(row), events

    async def update_metadata(
        self, ko_id: str, metadata: dict
    ) -> tuple[KnowledgeObject, list[KnowledgeEvent]]:
        events: list[KnowledgeEvent] = []
        async with self._session_factory() as db:
            row = await db.get(KnowledgeObjectModel, UUID(ko_id))
            if row is None:
                raise ValueError(f"KnowledgeObject {ko_id} not found")
            if row.deleted_at is not None:
                raise ValueError(f"KnowledgeObject {ko_id} is deleted")

            old_meta = dict(row.ko_metadata or {})
            row.ko_metadata = {**old_meta, **metadata}
            row.updated_at = datetime.now(timezone.utc)
            await db.commit()

            events.append(
                MetadataUpdated(
                    ko_id=ko_id,
                    changes=metadata,
                )
            )
            logger.info("knowledge_object_metadata_updated", ko_id=ko_id)
            return _ko_from_orm(row), events

    async def soft_delete(self, ko_id: str, reason: str | None = None) -> list[KnowledgeEvent]:
        events: list[KnowledgeEvent] = []
        async with self._session_factory() as db:
            row = await db.get(KnowledgeObjectModel, UUID(ko_id))
            if row is None:
                raise ValueError(f"KnowledgeObject {ko_id} not found")
            if row.deleted_at is not None:
                raise ValueError(f"KnowledgeObject {ko_id} already deleted")

            row.lifecycle_state = LifecycleState.DELETED.value
            row.deleted_at = datetime.now(timezone.utc)
            row.updated_at = datetime.now(timezone.utc)
            await db.commit()

            events.append(
                KnowledgeObjectDeleted(
                    ko_id=ko_id,
                    reason=reason,
                )
            )
            logger.info("knowledge_object_deleted", ko_id=ko_id)
            return events

    async def create_version(self, ko_id: str) -> tuple[int, list[KnowledgeEvent]]:
        events: list[KnowledgeEvent] = []
        async with self._session_factory() as db:
            row = await db.get(KnowledgeObjectModel, UUID(ko_id))
            if row is None:
                raise ValueError(f"KnowledgeObject {ko_id} not found")

            row.version += 1
            row.updated_at = datetime.now(timezone.utc)

            ko_version = KnowledgeObjectVersionModel(
                ko_id=row.id,
                version=row.version,
                snapshot={
                    "id": str(row.id),
                    "workspace_id": str(row.workspace_id) if row.workspace_id else None,
                    "collection_id": str(row.collection_id) if row.collection_id else None,
                    "owner_id": str(row.owner_id),
                    "title": row.title,
                    "content_type": row.content_type,
                    "content_hash": row.content_hash,
                    "lifecycle_state": row.lifecycle_state,
                    "enrichment_status": row.enrichment_status,
                    "version": row.version,
                    "metadata": row.ko_metadata,
                },
            )
            db.add(ko_version)
            await db.commit()

            events.append(
                VersionCreated(
                    ko_id=ko_id,
                    version_number=row.version,
                )
            )
            logger.info("knowledge_object_version_created", ko_id=ko_id, version=row.version)
            return row.version, events

    async def list_versions(self, ko_id: str) -> list[dict]:
        async with self._session_factory() as db:
            query = (
                select(KnowledgeObjectVersionModel)
                .where(KnowledgeObjectVersionModel.ko_id == UUID(ko_id))
                .order_by(KnowledgeObjectVersionModel.version.desc())
            )
            rows = (await db.execute(query)).scalars().all()
            return [
                {
                    "id": str(r.id),
                    "ko_id": str(r.ko_id),
                    "version": r.version,
                    "snapshot": r.snapshot,
                    "created_at": r.created_at,
                }
                for r in rows
            ]
