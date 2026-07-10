from unittest.mock import AsyncMock, patch

import pytest

from src.agents.recovery_agent import RecoveryAgent
from src.schemas.recovery import (
    GeneratedPlanInfo,
    GeneratedTaskInfo,
    GenerateRecoveryPlanRequest,
    GenerateRecoveryPlanResponse,
)

MOCK_PLAN_JSON = (
    '{"plan_title": "Cell Biology Recovery", "tasks": ['
    '{"title": "Review Cell Structure", "task_type": "review_notes", '
    '"description": "Review cell organelles and their functions"}, '
    '{"title": "Label Cell Diagram", "task_type": "diagram_exercise", '
    '"description": "Practice labeling animal and plant cell diagrams"}]}'
)


@pytest.fixture
def mock_router():
    router = AsyncMock()
    router.route.return_value = {
        "content": MOCK_PLAN_JSON,
        "model": "ollama/test",
        "confidence": 0.95,
        "usage": {"total_tokens": 150},
    }
    return router


@pytest.fixture
def mock_router_no_weak_topics():
    router = AsyncMock()
    return router


@pytest.fixture
def agent(mock_router):
    return RecoveryAgent(mock_router)


@pytest.mark.asyncio
async def test_generate_plan_no_weak_topics(agent):
    session = AsyncMock()
    session.execute = AsyncMock()
    session.execute.return_value.scalars.return_value.all.return_value = []

    with patch("src.agents.recovery_agent.get_weak_topics", new=AsyncMock(return_value=[])):
        result = await agent.generate_plan(user_id="test-user", session=session)

    assert result["plan"] is None
    assert result["error"] == "No weak topics found for this user"


@pytest.mark.asyncio
async def test_generate_plan_success(agent, mock_router):
    session = AsyncMock()

    weak_topics = [
        {
            "topic": "Cell Structure",
            "unit": "Unit 2: Cell Biology",
            "grade_level": 10,
            "average_score": 45.0,
            "attempt_count": 2,
            "severity": "moderate",
            "confidence": 0.67,
            "misconceptions": [
                {
                    "pattern_type": "wrong_answer",
                    "description": "Student answers 'mitochondria' instead of 'chloroplast'",
                    "frequency": 2,
                }
            ],
            "last_assessed_at": None,
        }
    ]

    with patch(
        "src.agents.recovery_agent.get_weak_topics", new=AsyncMock(return_value=weak_topics)
    ):
        with patch.object(session, "add"):
            session.flush = AsyncMock()
            session.commit = AsyncMock()
            session.refresh = AsyncMock()

            agent.llm_router.route.return_value = {
                "content": MOCK_PLAN_JSON,
                "model": "ollama/test",
                "confidence": 0.95,
                "usage": {"total_tokens": 150},
            }

            result = await agent.generate_plan(user_id="test-user", session=session)

    assert result["error"] is None
    assert result["plan"] is not None
    assert result["plan"]["topic"] == "Cell Biology Recovery"
    assert result["plan"]["total_tasks"] == 2
    assert result["plan"]["weak_topics_addressed"] == 1
    assert len(result["plan"]["tasks"]) == 2
    assert result["plan"]["tasks"][0]["task_type"] == "review_notes"
    assert result["plan"]["tasks"][1]["task_type"] == "diagram_exercise"


@pytest.mark.asyncio
async def test_format_weak_topics(agent):
    topics = [
        {
            "topic": "Cell Structure",
            "unit": "Unit 2",
            "grade_level": 10,
            "average_score": 45.0,
            "attempt_count": 2,
            "severity": "moderate",
            "confidence": 0.67,
            "misconceptions": [],
            "last_assessed_at": None,
        }
    ]
    formatted = agent._format_weak_topics(topics)
    assert "Cell Structure" in formatted
    assert "45.0%" in formatted
    assert "moderate" in formatted


@pytest.mark.asyncio
async def test_format_weak_topics_with_misconceptions(agent):
    topics = [
        {
            "topic": "Genetics",
            "unit": "Unit 3",
            "grade_level": 10,
            "average_score": 30.0,
            "attempt_count": 3,
            "severity": "critical",
            "confidence": 1.0,
            "misconceptions": [
                {
                    "pattern_type": "wrong_answer",
                    "description": "Student answers 'dominant' instead of 'recessive'",
                    "frequency": 3,
                }
            ],
            "last_assessed_at": None,
        }
    ]
    formatted = agent._format_weak_topics(topics)
    assert "Genetics" in formatted
    assert "critical" in formatted
    assert "dominant" in formatted
    assert "frequency: 3" in formatted


@pytest.mark.asyncio
async def test_severity_summary(agent):
    topics = [
        {"topic": "A", "severity": "critical", "average_score": 30.0},
        {"topic": "B", "severity": "moderate", "average_score": 50.0},
        {"topic": "C", "severity": "critical", "average_score": 25.0},
    ]
    summary = agent._get_severity_summary(topics)
    assert "2 critical" in summary
    assert "1 moderate" in summary


@pytest.mark.asyncio
async def test_generate_plan_json_parse_error(agent, mock_router):
    session = AsyncMock()
    agent.llm_router.route.return_value = {
        "content": "Not valid JSON at all",
        "model": "ollama/test",
    }
    weak_topics = [
        {
            "topic": "Cell Structure",
            "unit": "Unit 2",
            "grade_level": 10,
            "average_score": 45.0,
            "attempt_count": 2,
            "severity": "moderate",
            "confidence": 0.67,
            "misconceptions": [],
            "last_assessed_at": None,
        }
    ]

    with patch(
        "src.agents.recovery_agent.get_weak_topics", new=AsyncMock(return_value=weak_topics)
    ):
        result = await agent.generate_plan(user_id="test-user", session=session)

    assert result["plan"] is None
    assert "Failed to generate plan" in (result["error"] or "")


@pytest.mark.asyncio
async def test_generate_plan_with_topic_filter_no_match(agent, mock_router):
    session = AsyncMock()
    weak_topics = [
        {
            "topic": "Cell Structure",
            "unit": "Unit 2",
            "grade_level": 10,
            "average_score": 45.0,
            "attempt_count": 2,
            "severity": "moderate",
            "confidence": 0.67,
            "misconceptions": [],
            "last_assessed_at": None,
        }
    ]

    with patch(
        "src.agents.recovery_agent.get_weak_topics", new=AsyncMock(return_value=weak_topics)
    ):
        result = await agent.generate_plan(
            user_id="test-user", session=session, topic_filter="Genetics"
        )

    assert result["plan"] is None
    assert "No weak topics match filter: Genetics" in (result["error"] or "")


def test_generate_recovery_plan_request_schema():
    req = GenerateRecoveryPlanRequest()
    assert req.topic_filter is None

    req = GenerateRecoveryPlanRequest(topic_filter="Cell")
    assert req.topic_filter == "Cell"


def test_generate_recovery_plan_response_schema():
    task = GeneratedTaskInfo(
        id="00000000-0000-0000-0000-000000000001",
        title="Review Cell Structure",
        task_type="review_notes",
        description="Review cell organelles",
    )
    plan = GeneratedPlanInfo(
        id="00000000-0000-0000-0000-000000000002",
        user_id="00000000-0000-0000-0000-000000000003",
        topic="Cell Biology Recovery",
        total_tasks=1,
        status="active",
        weak_topics_addressed=1,
        tasks=[task],
        created_at="2026-05-26T00:00:00",
    )
    resp = GenerateRecoveryPlanResponse(plan=plan, error=None)
    assert resp.plan is not None
    assert resp.plan.topic == "Cell Biology Recovery"
    assert resp.plan.total_tasks == 1
    assert resp.plan.weak_topics_addressed == 1
    assert len(resp.plan.tasks) == 1
    assert resp.plan.tasks[0].title == "Review Cell Structure"
    assert resp.plan.tasks[0].task_type == "review_notes"


def test_generate_recovery_plan_response_error():
    resp = GenerateRecoveryPlanResponse(plan=None, error="No weak topics found")
    assert resp.plan is None
    assert resp.error == "No weak topics found"


def test_generated_task_info_defaults():
    task = GeneratedTaskInfo(
        id="00000000-0000-0000-0000-000000000001",
        title="Test Task",
        task_type="practice_questions",
    )
    assert task.description is None
