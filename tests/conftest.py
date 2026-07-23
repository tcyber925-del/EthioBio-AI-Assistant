from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from src.database.session import Base


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    from sqlalchemy.types import Text
    return compiler.visit_text(Text(), **kw)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def _disable_rate_limit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("src.config.settings.rate_limit_enabled", False)


@pytest.fixture
def mock_router():
    router = AsyncMock()
    router.route.return_value = {
        "content": "Test response",
        "model": "ollama/test",
        "confidence": 0.95,
        "usage": {"total_tokens": 50},
    }
    router.generate_embedding.return_value = [0.1] * 384
    router.manager = AsyncMock()
    return router


@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    retriever.retrieve = AsyncMock(
        return_value=[
            {
                "content": "Test curriculum content",
                "metadata": {"topic": "Cell Biology", "grade_level": 10},
                "score": 0.95,
                "id": "1",
            }
        ]
    )
    retriever.format_context.return_value = (
        "[Source 1] Topic: Cell Biology | Grade: 10\nTest curriculum content"
    )
    return retriever
