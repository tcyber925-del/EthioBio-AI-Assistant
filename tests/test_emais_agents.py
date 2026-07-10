from unittest.mock import AsyncMock, patch

import pytest

from src.agents.curriculum_agent import CurriculumAgent
from src.agents.forecast_agent import ForecastAgent
from src.agents.intervention_agent import InterventionAgent
from src.agents.misconception_agent import MisconceptionAgent
from src.agents.research_agent import ResearchAgent
from src.core.agent_orchestrator.setup import build_registry


@pytest.mark.asyncio
async def test_emais_agents_execution():
    mock_llm_router = AsyncMock()
    mock_llm_router.call.return_value = {"content": "mocked response"}

    agents = [
        MisconceptionAgent(mock_llm_router),
        InterventionAgent(mock_llm_router),
        ForecastAgent(mock_llm_router),
        CurriculumAgent(mock_llm_router),
        ResearchAgent(mock_llm_router),
    ]

    for agent in agents:
        with patch.object(agent, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"content": f"{agent.name} result"}
            res = await agent.execute(task="Test task", context={})
            assert res == f"{agent.name} result"
            mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_emais_agents_registration():
    mock_llm_router = AsyncMock()
    mock_adapter = AsyncMock()
    registry = build_registry(mock_llm_router, mock_adapter)

    agent_names = [a.name for a in registry.list_agents()]
    assert "tutor_agent" in agent_names
    assert "quiz_agent" in agent_names
    assert "lesson_planner_agent" in agent_names
    assert "diagnostic_agent" in agent_names
    assert "translator_agent" in agent_names
    assert "safety_agent" in agent_names
    assert "diagram_agent" in agent_names
    assert "student_progress_agent" in agent_names


@pytest.mark.asyncio
async def test_emais_agents_reflection():
    mock_llm_router = AsyncMock()

    intervention_agent = InterventionAgent(mock_llm_router)
    with patch.object(intervention_agent, "_call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {
            "content": '{"effectiveness_score": 8, "lessons_learned": "Visual aid helped.", "suggested_adjustments": "Use interactive next time."}'
        }
        res = await intervention_agent.reflect(
            past_intervention={"type": "visual"}, outcome_data={"score": 85}
        )
        assert res["effectiveness_score"] == 8
        mock_call.assert_called_once()

    misconception_agent = MisconceptionAgent(mock_llm_router)
    with patch.object(misconception_agent, "_call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = {
            "content": '{"diagnosis_accuracy": 9, "lessons_learned": "Accurate.", "model_updates": "None."}'
        }
        res = await misconception_agent.reflect(
            past_diagnosis={"cause": "confuses terms"}, outcome_data={"score": 90}
        )
        assert res["diagnosis_accuracy"] == 9
        mock_call.assert_called_once()
