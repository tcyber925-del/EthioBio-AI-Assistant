from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Bookmark as BookmarkModel
from src.database.models import KnowledgeObject as KnowledgeObjectModel
from src.database.session import get_session

router = APIRouter(prefix="/api/v1/bookmarks", tags=["Bookmarks"])


@router.post("/{ko_id}")
async def add_bookmark(
    ko_id: str, user_id: str = Query(...), db: AsyncSession = Depends(get_session)
):
    ko = await db.get(KnowledgeObjectModel, UUID(ko_id))
    if ko is None or ko.deleted_at is not None:
        raise HTTPException(status_code=404, detail="KnowledgeObject not found")

    existing = await db.execute(
        select(BookmarkModel).where(
            BookmarkModel.user_id == UUID(user_id),
            BookmarkModel.ko_id == UUID(ko_id),
        )
    )
    if existing.scalar_one_or_none():
        return {"bookmarked": True}

    db.add(BookmarkModel(user_id=UUID(user_id), ko_id=UUID(ko_id)))
    await db.commit()
    return {"bookmarked": True}


@router.delete("/{ko_id}")
async def remove_bookmark(
    ko_id: str, user_id: str = Query(...), db: AsyncSession = Depends(get_session)
):
    await db.execute(
        delete(BookmarkModel).where(
            BookmarkModel.user_id == UUID(user_id),
            BookmarkModel.ko_id == UUID(ko_id),
        )
    )
    await db.commit()
    return {"bookmarked": False}


@router.get("/")
async def list_bookmarks(user_id: str = Query(...), db: AsyncSession = Depends(get_session)):
    rows = await db.execute(
        select(KnowledgeObjectModel)
        .join(BookmarkModel, BookmarkModel.ko_id == KnowledgeObjectModel.id)
        .where(
            BookmarkModel.user_id == UUID(user_id),
            KnowledgeObjectModel.deleted_at.is_(None),
        )
        .order_by(BookmarkModel.created_at.desc())
    )
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "content_type": r.content_type,
            "lifecycle_state": r.lifecycle_state,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows.scalars().all()
    ]


@router.get("/check")
async def check_bookmark(
    ko_id: str, user_id: str = Query(...), db: AsyncSession = Depends(get_session)
):
    row = await db.execute(
        select(BookmarkModel).where(
            BookmarkModel.user_id == UUID(user_id),
            BookmarkModel.ko_id == UUID(ko_id),
        )
    )
    return {"bookmarked": row.scalar_one_or_none() is not None}
