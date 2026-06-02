"""Tests for TutorNode integration with LearnerProfileBuilder (TUT-002)."""

from uuid import uuid4

import pytest

from src.graph.nodes.tutor import TutorNode
from src.graph.state import AgentState


@pytest.mark.asyncio
async def test_learner_profile_block_injected_into_system_prompt(mock_router):
    node = TutorNode(mock_router)
    profile_block = "## Learner Profile\n- Weak Topics: Genetics\n- Difficulty Level: BEGINNER"
    state = AgentState(
        user_message="What is DNA?",
        user_id=uuid4(),
        grade_level=10,
        topic="Genetics",
        learner_profile_block=profile_block,
        use_learner_awareness=True,
    )
    await node(state)
    sent_messages = mock_router.route.call_args[0][0]
    system_content = sent_messages[0]["content"]
    assert "## Learner Profile" in system_content
    assert "Weak Topics: Genetics" in system_content
    assert "Difficulty Level: BEGINNER" in system_content


@pytest.mark.asyncio
async def test_learner_profile_block_not_injected_when_disabled(mock_router):
    node = TutorNode(mock_router)
    profile_block = "## Learner Profile\n- Weak Topics: Genetics"
    state = AgentState(
        user_message="What is DNA?",
        user_id=uuid4(),
        grade_level=10,
        topic="Genetics",
        learner_profile_block=profile_block,
        use_learner_awareness=False,
    )
    await node(state)
    sent_messages = mock_router.route.call_args[0][0]
    system_content = sent_messages[0]["content"]
    assert "## Learner Profile" not in system_content


@pytest.mark.asyncio
async def test_learner_profile_block_not_injected_when_empty(mock_router):
    node = TutorNode(mock_router)
    state = AgentState(
        user_message="What is DNA?",
        user_id=uuid4(),
        grade_level=10,
        topic="Genetics",
        learner_profile_block="",
        use_learner_awareness=True,
    )
    await node(state)
    sent_messages = mock_router.route.call_args[0][0]
    system_content = sent_messages[0]["content"]
    assert "## Learner Profile" not in system_content


@pytest.mark.asyncio
async def test_learner_profile_in_socratic_mode(mock_router):
    node = TutorNode(mock_router)
    profile_block = "## Learner Profile\n- Strong Topics: Cell Biology\n- Difficulty Level: PROFICIENT"
    state = AgentState(
        user_message="Tell me about mitosis",
        user_id=uuid4(),
        grade_level=11,
        topic="Cell Division",
        learner_profile_block=profile_block,
        use_learner_awareness=True,
        socratic_mode=True,
    )
    await node(state)
    sent_messages = mock_router.route.call_args[0][0]
    system_content = sent_messages[0]["content"]
    assert "## Learner Profile" in system_content
    assert "Strong Topics: Cell Biology" in system_content
    assert "Socratic Mode" in system_content


@pytest.mark.asyncio
async def test_learner_profile_appears_before_memory_context(mock_router):
    node = TutorNode(mock_router)
    profile_block = "## Learner Profile\n- Weak Topics: Genetics"
    state = AgentState(
        user_message="What is DNA?",
        user_id=uuid4(),
        grade_level=10,
        topic="Genetics",
        learner_profile_block=profile_block,
        use_learner_awareness=True,
        memory_context="## Learner Context\n- Previous topic: Cell Biology",
    )
    await node(state)
    sent_messages = mock_router.route.call_args[0][0]
    system_content = sent_messages[0]["content"]
    profile_pos = system_content.index("## Learner Profile")
    memory_pos = system_content.index("## Learner Context")
    assert profile_pos < memory_pos


@pytest.mark.asyncio
async def test_learner_profile_block_preserved_with_hints(mock_router):
    node = TutorNode(mock_router)
    profile_block = "## Learner Profile\n- Difficulty Level: BEGINNER"
    state = AgentState(
        user_message="What is DNA?",
        user_id=uuid4(),
        grade_level=9,
        topic="Genetics",
        learner_profile_block=profile_block,
        use_learner_awareness=True,
        hint_level=2,
    )
    await node(state)
    sent_messages = mock_router.route.call_args[0][0]
    system_content = sent_messages[0]["content"]
    assert "## Learner Profile" in system_content
    assert "hint" in system_content.lower()
