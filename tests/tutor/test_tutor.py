from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.tutor.models import TeachingStrategy
from src.agents.tutor.tutor import TutorSynthesisAgent


@pytest.mark.asyncio
async def test_agent_selects_strategy_and_extracts_citations():
    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value={
        "content": "Meiosis produces diverse cells. [id:bio_ch4_22]",
        "model": "test-model",
        "confidence": 0.9,
    })

    agent = TutorSynthesisAgent(mock_router)
    response = await agent.generate(
        user_message="What is meiosis?",
        evidence_items=[
            {"id": "bio_ch4_22", "content": "Meiosis diversity", "source_name": "curriculum"},
        ],
        evidence_synthesis="Synthesis text",
        grade_level=10,
        language="en",
        socratic_mode=False,
        hint_level=0,
        reveal_answer=False,
        learner_profile_block="",
        messages=[],
        intent="tutor",
        misconception_detected=False,
        student_misconceptions=[],
    )

    assert response.content == "Meiosis produces diverse cells."
    assert response.teaching_strategy == TeachingStrategy.DIRECT_EXPLANATION
    assert len(response.citation_map) == 1
    assert response.citation_map[0].evidence_ids == ["bio_ch4_22"]
    assert response.confidence == 0.9


@pytest.mark.asyncio
async def test_agent_uses_socratic_when_in_socratic_mode():
    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value={
        "content": "What do you think? [id:bio_ch4_22]",
        "model": "test-model",
        "confidence": 0.8,
    })

    agent = TutorSynthesisAgent(mock_router)
    response = await agent.generate(
        user_message="What is meiosis?",
        evidence_items=[],
        evidence_synthesis="",
        grade_level=None,
        language="en",
        socratic_mode=True,
        hint_level=0,
        reveal_answer=False,
        learner_profile_block="",
        messages=[],
        intent="tutor",
        misconception_detected=False,
        student_misconceptions=[],
    )

    assert response.teaching_strategy == TeachingStrategy.SOCRATIC
