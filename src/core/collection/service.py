from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.models import Collection as CollectionModel
from src.database.models import KnowledgeObject as KnowledgeObjectModel

from .models import Collection, NewCollection, UpdateCollection

logger = structlog.get_logger()


def _from_orm(row: CollectionModel) -> Collection:
    return Collection(
        id=str(row.id),
        workspace_id=str(row.workspace_id),
        name=row.name,
        description=row.description,
        created_by=str(row.created_by),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class CollectionService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def create(self, data: NewCollection, created_by: str) -> Collection:
        async with self._session_factory() as db:
            row = CollectionModel(
                workspace_id=UUID(data.workspace_id),
                name=data.name,
                description=data.description,
                created_by=UUID(created_by),
            )
            db.add(row)
            await db.commit()
            logger.info("collection_created", id=str(row.id), name=data.name)
            return _from_orm(row)

    async def get(self, collection_id: str) -> Collection | None:
        async with self._session_factory() as db:
            row = await db.get(CollectionModel, UUID(collection_id))
            if row is None or row.deleted_at is not None:
                return None
            return _from_orm(row)

    async def list_for_workspace(self, workspace_id: str) -> list[Collection]:
        async with self._session_factory() as db:
            query = (
                select(CollectionModel)
                .where(
                    CollectionModel.workspace_id == UUID(workspace_id),
                    CollectionModel.deleted_at.is_(None),
                )
                .order_by(CollectionModel.created_at.desc())
            )
            rows = (await db.execute(query)).scalars().all()
            return [_from_orm(r) for r in rows]

    async def update(self, collection_id: str, data: UpdateCollection) -> Collection | None:
        async with self._session_factory() as db:
            row = await db.get(CollectionModel, UUID(collection_id))
            if row is None or row.deleted_at is not None:
                return None
            if data.name is not None:
                row.name = data.name
            if data.description is not None:
                row.description = data.description
            await db.commit()
            logger.info("collection_updated", id=collection_id)
            return _from_orm(row)

    async def soft_delete(self, collection_id: str) -> bool:
        async with self._session_factory() as db:
            row = await db.get(CollectionModel, UUID(collection_id))
            if row is None or row.deleted_at is not None:
                return False
            row.deleted_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("collection_deleted", id=collection_id)
            return True

    async def add_knowledge_object(self, collection_id: str, ko_id: str) -> bool:
        async with self._session_factory() as db:
            collection = await db.get(CollectionModel, UUID(collection_id))
            if collection is None or collection.deleted_at is not None:
                return False
            ko = await db.get(KnowledgeObjectModel, UUID(ko_id))
            if ko is None or ko.deleted_at is not None:
                return False
            ko.collection_id = UUID(collection_id)
            await db.commit()
            logger.info("ko_added_to_collection", ko_id=ko_id, collection_id=collection_id)
            return True

    async def remove_knowledge_object(self, collection_id: str, ko_id: str) -> bool:
        async with self._session_factory() as db:
            ko = await db.get(KnowledgeObjectModel, UUID(ko_id))
            if ko is None or ko.deleted_at is not None or str(ko.collection_id) != collection_id:
                return False
            ko.collection_id = None
            await db.commit()
            logger.info("ko_removed_from_collection", ko_id=ko_id, collection_id=collection_id)
            return True

    async def list_knowledge_objects(self, collection_id: str) -> list[dict]:
        async with self._session_factory() as db:
            query = (
                select(KnowledgeObjectModel)
                .where(
                    KnowledgeObjectModel.collection_id == UUID(collection_id),
                    KnowledgeObjectModel.deleted_at.is_(None),
                )
                .order_by(KnowledgeObjectModel.created_at.desc())
            )
            rows = (await db.execute(query)).scalars().all()
            return [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "content_type": r.content_type,
                    "lifecycle_state": r.lifecycle_state,
                }
                for r in rows
            ]
