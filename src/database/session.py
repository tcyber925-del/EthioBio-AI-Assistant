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
    logger.info("database_init_deferred - waiting for first connection")
    engine = _get_engine()
    logger.debug("engine_created")
    from src.database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")

    # Run pending SQL migrations
    from pathlib import Path

    from sqlalchemy import text

    migrations_dir = Path("scripts/migrations")
    if migrations_dir.exists():
        logger.info("checking_database_migrations")
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS applied_migrations (migration_name VARCHAR(255) PRIMARY KEY)"  # noqa: E501
                )
            )

        migration_files = sorted(migrations_dir.glob("*.sql"))
        for sql_file in migration_files:
            migration_name = sql_file.name
            async with engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT 1 FROM applied_migrations WHERE migration_name = :name"),
                    {"name": migration_name},
                )
                if not result.scalar():
                    logger.info("applying_migration", name=migration_name)
                    sql_content = sql_file.read_text().strip()
                    if sql_content:
                        # Split by semicolon to run statements individually (avoiding prepared statement limits)  # noqa: E501
                        statements = [
                            stmt.strip() for stmt in sql_content.split(";") if stmt.strip()
                        ]
                        for stmt in statements:
                            await conn.execute(text(stmt))
                    await conn.execute(
                        text("INSERT INTO applied_migrations (migration_name) VALUES (:name)"),
                        {"name": migration_name},
                    )
                    logger.info("migration_applied", name=migration_name)


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
