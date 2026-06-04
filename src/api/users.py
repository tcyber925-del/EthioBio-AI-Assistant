from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User
from src.database.session import get_session

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch("/{telegram_id}/language")
async def update_user_language(
    telegram_id: int, language: str, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if language not in ("en", "am", "both"):
        raise HTTPException(status_code=400, detail="Invalid language. Must be en, am, or both.")
    user.language_preference = language
    await session.commit()
    return {"status": "ok", "language": language}
