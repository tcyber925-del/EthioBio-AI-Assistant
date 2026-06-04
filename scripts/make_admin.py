"""
Promote a user to admin by email.
Usage: python -m scripts.make_admin --email user@example.com
"""
import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.config import settings
from src.database.models import User, UserRole


async def make_admin(email: str) -> bool:
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User not found: {email}")
            return False
        user.role = UserRole.admin
        await session.commit()
        print(f"Promoted {email} to admin (ID: {user.id})")
        return True


async def make_admin_by_id(user_id: str) -> bool:
    import uuid
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            print(f"User not found: {user_id}")
            return False
        user.role = UserRole.admin
        await session.commit()
        print(f"Promoted {user.email or user_id} to admin")
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote a user to admin")
    parser.add_argument("--email", help="User email")
    parser.add_argument("--id", dest="user_id", help="User UUID")
    args = parser.parse_args()

    if not args.email and not args.user_id:
        parser.print_help()
        exit(1)

    if args.email:
        asyncio.run(make_admin(args.email))
    else:
        asyncio.run(make_admin_by_id(args.user_id))
