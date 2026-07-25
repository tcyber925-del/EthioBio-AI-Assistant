from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")

TEST_USER_ID = uuid4()


async def _seed_preference(db):
    from src.core.memory.semantic_manager import SemanticFactManager
    mgr = SemanticFactManager()
    await mgr.upsert(
        db=db, user_id=TEST_USER_ID,
        fact_key="learning_style", fact_value="prefers diagrams",
        category="preference", confidence=0.9,
    )
    await db.commit()


async def _seed_misconception_turns(db, session_id):
    from src.database.models import ConversationTurn
    now = datetime.now(timezone.utc)
    turns_data = [
        ("user", "I'm really confused about mitosis. I don't get how the phases work."),
        ("assistant", "Let's break down the phases of mitosis. First, prophase..."),
        ("user", "OK so chromosomes condense in prophase, but what happens after that?"),
    ]
    for i, (role, content) in enumerate(turns_data):
        db.add(ConversationTurn(
            id=uuid4(), user_id=TEST_USER_ID, session_id=session_id,
            role=role, content=content, topic="mitosis",
            created_at=now - timedelta(minutes=10 - i),
        ))
    await db.commit()


async def _seed_summary(db, user_id, topic, understanding, confidence,
                         misconceptions=None, goal="", minutes_ago=0):
    from src.core.memory.vector_store import MemoryVectorStore
    from src.database.models import MemoryEducationalSummary
    from src.rag.embedder import Embedder
    text = (
        f"Topic: {topic} | Understanding: {understanding} | "
        f"Confidence: {confidence:.2f} | Next goal: {goal}"
    )
    if misconceptions:
        text += f" | Misconceptions: {'; '.join(misconceptions[:3])}"
    summary_id = uuid4()
    embedder = Embedder()
    embedding = await embedder.embed_text(text)
    vs = MemoryVectorStore()
    await vs.add_memory(
        embedding=embedding, text=text,
        metadata={
            "user_id": str(user_id), "topic": topic,
            "understanding_level": understanding, "confidence": confidence,
            "created_at": (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat(),
        },
        memory_id=str(summary_id),
    )
    db.add(MemoryEducationalSummary(
        id=summary_id, user_id=user_id, topic=topic,
        understanding_level=understanding, key_misconceptions=misconceptions or [],
        confidence=confidence, next_learning_goal=goal,
        embedding_id=str(summary_id),
        created_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    ))
    await db.commit()
    return summary_id


async def _assemble_context(db, user_id, topic=None):
    from src.core.memory.context_assembler import ContextAssembler
    assembler = ContextAssembler()
    return await assembler.assemble(
        user_id=user_id, topic=topic, db=db,
        session_state={"active_topic": topic or "general", "tutoring_mode": "direct"},
    )


class TestMemoryRecall:
    """Benchmark scenarios for educational memory recall."""

    async def test_preference_recall(self, db):
        """SemanticFact about learning style must appear in context."""
        await _seed_preference(db)
        context = await _assemble_context(db, TEST_USER_ID)
        assert "prefers diagrams" in context, (
            f"Expected 'prefers diagrams' in context, got:\n{context}"
        )

    async def test_misconception_cross_session(self, db):
        """A misconception from a prior session must surface in new session context."""
        session_id = uuid4()
        await _seed_misconception_turns(db, session_id)
        await _seed_summary(
            db, TEST_USER_ID, "mitosis", "beginner", 0.6,
            misconceptions=["confused about chromosome behavior"],
            goal="understand prophase chromosome condensation",
            minutes_ago=30,
        )
        context = await _assemble_context(db, TEST_USER_ID, topic="mitosis")
        assert "confused" in context.lower() or "misconception" in context.lower(), (
            f"Expected misconception context for mitosis, got:\n{context}"
        )

    async def test_mastery_progression(self, db):
        """Multiple summaries: newest understanding level should appear."""
        await _seed_summary(db, TEST_USER_ID, "genetics", "beginner", 0.5,
                            minutes_ago=60)
        await _seed_summary(db, TEST_USER_ID, "genetics", "intermediate", 0.7,
                            minutes_ago=30)
        await _seed_summary(db, TEST_USER_ID, "genetics", "advanced", 0.85,
                            minutes_ago=5)
        context = await _assemble_context(db, TEST_USER_ID, topic="genetics")
        assert "advanced" in context, (
            f"Expected 'advanced' understanding in context, got:\n{context}"
        )

    async def test_multi_topic_recall(self, db):
        """Turns from different topics: topic filter should return only matching turns."""
        now = datetime.now(timezone.utc)
        from src.database.models import ConversationTurn
        for role, content, topic in [
            ("user", "Tell me about genetics", "genetics"),
            ("assistant", "Genetics is the study of heredity", "genetics"),
            ("user", "Explain mitosis phases", "mitosis"),
            ("assistant", "Mitosis has prophase, metaphase...", "mitosis"),
        ]:
            db.add(ConversationTurn(
                id=uuid4(), user_id=TEST_USER_ID, session_id=None,
                role=role, content=content, topic=topic,
                created_at=now,
            ))
        await db.commit()

        context_mitosis = await _assemble_context(db, TEST_USER_ID, topic="mitosis")
        assert "mitosis" in context_mitosis.lower()
        assert "genetics is the study" not in context_mitosis

    async def test_entity_extractor_ner(self):
        """EntityExtractor must detect biology terms and difficulty markers."""
        from src.core.memory.entity_extractor import EntityExtractor
        extractor = EntityExtractor()
        entities = extractor._extract_entities_from_text(
            "Student struggles with Punnett squares and mitosis phases"
        )
        texts = {e["text"] for e in entities}
        types = {e["type"] for e in entities}
        assert "punnett" in texts, f"Expected 'punnett' in entities: {entities}"
        assert "mitosis" in texts, f"Expected 'mitosis' in entities: {entities}"
        assert "difficulty" in types, f"Expected 'difficulty' type in entities: {entities}"

    async def test_entity_match_boost(self, db):
        """Entity match score must be > 0 when query mentions known entity."""
        from src.database.models import MemoryEntity
        db.add(MemoryEntity(
            id=uuid4(), user_id=TEST_USER_ID,
            entity_text="punnett", entity_type="concept",
        ))
        await db.commit()

        from src.core.memory.retrieval_orchestrator import RetrievalOrchestrator
        orch = RetrievalOrchestrator()
        score = await orch._entity_match_score(
            "struggles with Punnett squares",
            str(TEST_USER_ID), db,
        )
        assert score > 0, (
            f"Expected entity match score > 0, got {score}"
        )

    @pytest.mark.skip(reason="Requires PostgreSQL tsvector — see Task 3+")
    async def test_recency_ranking(self, db):
        """Two similar facts: newer one should rank higher."""
        now = datetime.now(timezone.utc)
        from src.database.models import ConversationTurn
        for _i, (content, days_ago) in enumerate([
            ("Student understands basic genetics concepts", 20),
            ("Student has strong grasp of genetics now", 1),
        ]):
            db.add(ConversationTurn(
                id=uuid4(), user_id=TEST_USER_ID, session_id=None,
                role="assistant", content=content, topic="genetics",
                created_at=now - timedelta(days=days_ago),
            ))
        await db.commit()

        from src.core.memory.retrieval_orchestrator import RetrievalOrchestrator
        orch = RetrievalOrchestrator()
        results = await orch.search("genetics understanding", n_results=5,
                                     user_id=str(TEST_USER_ID), db=db)
        contents = [r.content for r in results]
        strong_idx = next(i for i, c in enumerate(contents) if "strong grasp" in c)
        basic_idx = next(i for i, c in enumerate(contents) if "basic" in c)
        assert strong_idx < basic_idx, (
            f"Newer fact should rank higher. Order: {contents}"
        )
