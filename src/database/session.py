import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings

logger = structlog.get_logger()

_engine = None
_async_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _engine


def _get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_factory


async_session_factory = _get_session_factory


class Base(DeclarativeBase):
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "__tablename__") and cls.__tablename__:
            existing = getattr(cls, "__table_args__", None) or {}
            if isinstance(existing, dict):
                existing.setdefault("extend_existing", True)
                cls.__table_args__ = existing


async def get_session() -> AsyncSession:
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    logger.info("running_database_migrations")
    import asyncio
    from pathlib import Path

    from alembic.command import upgrade as alembic_upgrade
    from alembic.config import Config as AlembicConfig

    alembic_cfg = AlembicConfig(Path(__file__).parents[2] / "alembic.ini")
    await asyncio.to_thread(alembic_upgrade, alembic_cfg, "head")
    logger.info("database_migrations_complete")


async def close_db():
    global _engine, _async_session_factory
    if _engine is not None:
        try:
            await _engine.dispose()
        except Exception:
            logger.warning("database_engine_dispose_error_ignored")
        finally:
            _engine = None
    _async_session_factory = None
    logger.info("database engine disposed")
