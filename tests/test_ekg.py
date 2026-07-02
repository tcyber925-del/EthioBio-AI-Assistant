"""Tests for the Educational Knowledge Graph components."""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.knowledge_graph import GraphReasoningEngine, RelationshipBuilder
from src.database.models import Base, CurriculumTopic, TopicPrerequisite

builder = RelationshipBuilder()
engine = GraphReasoningEngine()


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def topics():
    return {
        "cell_structure": CurriculumTopic(
            id=uuid4(),
            grade_level=10,
            unit="Unit 1",
            topic="Cell Structure",
            content="Cells are the basic unit of life",
        ),
        "cell_biology": CurriculumTopic(
            id=uuid4(),
            grade_level=10,
            unit="Unit 1",
            topic="Cell Biology",
            content="Study of cells",
        ),
        "genetics": CurriculumTopic(
            id=uuid4(),
            grade_level=10,
            unit="Unit 2",
            topic="Genetics",
            content="Study of genes",
        ),
        "dna": CurriculumTopic(
            id=uuid4(),
            grade_level=10,
            unit="Unit 2",
            topic="DNA Structure",
            content="DNA molecule structure",
        ),
    }


@pytest.mark.asyncio
async def test_add_prerequisite(db_session, topics):
    for t in topics.values():
        db_session.add(t)
    await db_session.flush()

    prereq = await builder.add_prerequisite(
        db_session,
        topic_id=topics["cell_biology"].id,
        prerequisite_topic_id=topics["cell_structure"].id,
    )
    assert prereq.topic_id == topics["cell_biology"].id
    assert prereq.prerequisite_topic_id == topics["cell_structure"].id
    assert prereq.relationship_type == "prerequisite"


@pytest.mark.asyncio
async def test_add_prerequisite_duplicate_raises(db_session, topics):
    for t in topics.values():
        db_session.add(t)
    await db_session.flush()

    await builder.add_prerequisite(
        db_session,
        topic_id=topics["cell_biology"].id,
        prerequisite_topic_id=topics["cell_structure"].id,
    )
    with pytest.raises(ValueError, match="already exists"):
        await builder.add_prerequisite(
            db_session,
            topic_id=topics["cell_biology"].id,
            prerequisite_topic_id=topics["cell_structure"].id,
        )


@pytest.mark.asyncio
async def test_add_batch_skips_duplicates(db_session, topics):
    for t in topics.values():
        db_session.add(t)
    await db_session.flush()

    created = await builder.add_batch(
        db_session,
        topic_id=topics["genetics"].id,
        prerequisite_ids=[
            topics["cell_biology"].id,
            topics["cell_structure"].id,
        ],
    )
    assert len(created) == 2

    created2 = await builder.add_batch(
        db_session,
        topic_id=topics["genetics"].id,
        prerequisite_ids=[
            topics["cell_biology"].id,
            topics["dna"].id,
        ],
    )
    assert len(created2) == 1
    assert created2[0].prerequisite_topic_id == topics["dna"].id


@pytest.mark.asyncio
async def test_get_prerequisites_and_dependents(db_session, topics):
    for t in topics.values():
        db_session.add(t)
    await db_session.flush()

    await builder.add_prerequisite(
        db_session,
        topic_id=topics["cell_biology"].id,
        prerequisite_topic_id=topics["cell_structure"].id,
    )
    await builder.add_prerequisite(
        db_session,
        topic_id=topics["genetics"].id,
        prerequisite_topic_id=topics["dna"].id,
    )

    prereqs = await builder.get_prerequisites(db_session, topics["cell_biology"].id)
    assert len(prereqs) == 1
    assert prereqs[0].prerequisite_topic_id == topics["cell_structure"].id

    deps = await builder.get_dependents(db_session, topics["cell_structure"].id)
    assert len(deps) == 1
    assert deps[0].topic_id == topics["cell_biology"].id


@pytest.mark.asyncio
async def test_remove_prerequisite(db_session, topics):
    for t in topics.values():
        db_session.add(t)
    await db_session.flush()

    prereq = await builder.add_prerequisite(
        db_session,
        topic_id=topics["cell_biology"].id,
        prerequisite_topic_id=topics["cell_structure"].id,
    )

    removed = await builder.remove(db_session, prereq.id)
    assert removed is True

    remaining = await builder.get_prerequisites(db_session, topics["cell_biology"].id)
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent_returns_false(db_session):
    removed = await builder.remove(db_session, uuid4())
    assert removed is False


@pytest.mark.skip(reason="Requires PostgreSQL (ARRAY/ANY syntax not supported by SQLite)")
@pytest.mark.asyncio
async def test_prerequisite_chain(db_session, topics):
    for t in topics.values():
        db_session.add(t)
    await db_session.flush()

    await builder.add_prerequisite(
        db_session,
        topic_id=topics["cell_biology"].id,
        prerequisite_topic_id=topics["cell_structure"].id,
    )
    await builder.add_prerequisite(
        db_session,
        topic_id=topics["genetics"].id,
        prerequisite_topic_id=topics["cell_biology"].id,
    )
    await builder.add_prerequisite(
        db_session,
        topic_id=topics["genetics"].id,
        prerequisite_topic_id=topics["dna"].id,
    )

    chain = await engine.get_prerequisite_chain(db_session, topics["genetics"].id)
    chain_topics = {n.topic for n in chain}
    assert "Cell Biology" in chain_topics
    assert "Cell Structure" in chain_topics
    assert "DNA Structure" in chain_topics


@pytest.mark.skip(reason="Requires PostgreSQL (ARRAY/ANY syntax not supported by SQLite)")
@pytest.mark.asyncio
async def test_chain_depth_limit(db_session, topics):
    for t in topics.values():
        db_session.add(t)
    await db_session.flush()

    await builder.add_prerequisite(
        db_session,
        topic_id=topics["cell_biology"].id,
        prerequisite_topic_id=topics["cell_structure"].id,
    )

    chain = await engine.get_prerequisite_chain(
        db_session, topics["cell_biology"].id, max_depth=0
    )
    assert len(chain) == 0


@pytest.mark.skip(reason="Requires PostgreSQL (ARRAY/ANY syntax not supported by SQLite)")
@pytest.mark.asyncio
async def test_dependent_chain(db_session, topics):
    for t in topics.values():
        db_session.add(t)
    await db_session.flush()

    await builder.add_prerequisite(
        db_session,
        topic_id=topics["cell_biology"].id,
        prerequisite_topic_id=topics["cell_structure"].id,
    )
    await builder.add_prerequisite(
        db_session,
        topic_id=topics["genetics"].id,
        prerequisite_topic_id=topics["cell_biology"].id,
    )

    chain = await engine.get_dependent_chain(db_session, topics["cell_structure"].id)
    chain_topics = {n.topic for n in chain}
    assert "Cell Biology" in chain_topics
    assert "Genetics" in chain_topics
