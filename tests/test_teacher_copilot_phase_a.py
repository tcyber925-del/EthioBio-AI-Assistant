from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.core.teacher_copilot.intent_router import IntentRouter
from src.core.teacher_copilot.pipeline import (
    AssessmentCreatorNode,
    LessonCreatorNode,
    route_after_classify,
)
from src.core.teacher_copilot.state import TeacherCopilotState as State

WS_ID = UUID("00000000-0000-0000-0000-00000000000f")
CLASS_ID = UUID("00000000-0000-0000-0000-00000000000e")


class TestIntentRoutingFixes:
    @pytest.mark.asyncio
    async def test_create_a_quiz_routes_to_assessment(self):
        intent, confidence, _ = await IntentRouter().classify("create a quiz on genetics")
        assert intent == "assessment_creation"

    @pytest.mark.asyncio
    async def test_create_a_lesson_plan_routes_to_lesson_planning(self):
        intent, _, _ = await IntentRouter().classify("create a lesson plan for tomorrow")
        assert intent == "lesson_planning"

    @pytest.mark.asyncio
    async def test_who_needs_attention_routes_to_classroom(self):
        intent, _, _ = await IntentRouter().classify("who needs attention in my class")
        assert intent == "classroom_analysis"

    def test_lesson_planning_routes_to_create_lesson(self):
        state = State(intent="lesson_planning")
        assert route_after_classify(state) == "create_lesson"

    def test_classroom_analysis_still_routes_to_gather(self):
        state = State(intent="classroom_analysis")
        assert route_after_classify(state) == "gather"


class TestGatherDataNodeClassroom:
    @patch("src.core.teacher_copilot.pipeline.async_session_factory")
    async def test_populates_classroom_profile_and_interventions(self, mock_factory):
        from unittest.mock import AsyncMock

        from src.core.teacher_copilot.pipeline import GatherDataNode

        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_factory.return_value.return_value = mock_session

        from src.core.learning_intelligence.teacher.models.classroom_profile import (
            ClassroomProfile,
        )

        profile = ClassroomProfile(
            classroom_id=CLASS_ID,
            generated_at=__import__("datetime").datetime.now(),
            total_students=30,
            classroom_health=72.5,
            readiness_distribution={"high": 10, "medium": 15, "low": 5},
            risk_students=[],
            intervention_candidates=[],
            mastery_heatmap={"Cell Biology": 0.7},
        )

        node = GatherDataNode(AsyncMock())
        with patch(
            "src.core.teacher_copilot.pipeline.TeacherService"
        ) as teacher_cls, patch(
            "src.core.teacher_copilot.pipeline.InterventionService"
        ) as intervention_cls:
            teacher_cls.return_value.get_classroom_overview = AsyncMock(return_value=profile)
            intervention_cls.return_value.list_for_classroom = AsyncMock(
                return_value=[
                    MagicMock(
                        **{
                            "id": 1,
                            "user_id": UUID("00000000-0000-0000-0000-00000000000d"),
                            "intervention_type": "REVIEW_TOPIC",
                            "topic": "Cell Biology",
                            "status": "active",
                            "priority": 0.9,
                        }
                    )
                ]
            )

            state = State(intent="classroom_analysis", classroom_id=CLASS_ID)
            result = await node(state)

        assert result["classroom_profile"]["classroom_health"] == 72.5
        assert result["classroom_profile"]["total_students"] == 30
        assert result["readiness_data"]["readiness_distribution"]["low"] == 5
        assert result["intervention_data"]
        assert result["intervention_data"][0]["intervention_type"] == "REVIEW_TOPIC"


class TestLessonCreatorNode:
    async def test_generates_lesson_plan_with_workspace_grounding(self):
        from src.core.retrieval.models import RetrievalResult, TextMatch

        kml_result = RetrievalResult(
            ko_id="ko-1",
            title="Cell Structure Notes",
            content_type="application/pdf",
            score=0.9,
            matches=[TextMatch(text="mitochondria are the powerhouse", chunk_index=0, score=0.9)],
            workspace_id=str(WS_ID),
        )

        class FakeRouter:
            async def route_and_search(self, query, workspace_id=None, limit=10):
                return [kml_result]

        generate = AsyncMock(
            return_value={
                "objective": "Understand mitochondria",
                "explanation": "x",
                "activities": [],
                "assessment": "",
            }
        )

        with patch("src.core.teacher_copilot.pipeline.LessonPlannerAgent") as agent_cls, patch(
            "src.core.retrieval.router.create_knowledge_router", return_value=FakeRouter()
        ):
            agent_instance = MagicMock()
            agent_instance.generate = generate
            agent_cls.return_value = agent_instance

            node = LessonCreatorNode(router=MagicMock())
            state = State(
                user_message="create a lesson plan about mitochondria for grade 10",
                workspace_id=WS_ID,
            )
            result = await node(state)

        call = generate.await_args
        assert call is not None
        kwargs = call.kwargs
        assert kwargs["topic"].lower() == "mitochondria"
        assert kwargs["grade_level"] == 10
        assert "Cell Structure Notes" in kwargs["workspace_context"]
        assert result["status"] == "lesson_created"
        assert result["generated_lesson_plan"]["objective"] == "Understand mitochondria"

    async def test_extracts_topic_without_workspace(self):
        generate = AsyncMock(
            return_value={"objective": "o", "explanation": "e", "activities": [], "assessment": ""}
        )

        with patch("src.core.teacher_copilot.pipeline.LessonPlannerAgent") as agent_cls:
            agent_instance = MagicMock()
            agent_instance.generate = generate
            agent_cls.return_value = agent_instance

            node = LessonCreatorNode(router=MagicMock())
            state = State(user_message="plan a lesson on chemical bonding")
            await node(state)

        call = generate.await_args
        assert call is not None
        assert call.kwargs["topic"].lower() == "chemical bonding"
        assert call.kwargs.get("workspace_context") is None


class TestAssessmentTopicExtraction:
    async def test_chemistry_topic_extracted(self):
        generate = AsyncMock(return_value={"title": "Quiz", "questions": [], "answer_key": ""})

        with patch("src.core.teacher_copilot.pipeline.QuizAgent") as quiz_cls:
            agent_instance = MagicMock()
            agent_instance.generate = generate
            quiz_cls.return_value = agent_instance

            node = AssessmentCreatorNode(router=MagicMock())
            state = State(user_message="create a quiz on chemical bonding")
            await node(state)

        call = generate.await_args
        assert call is not None
        assert call.kwargs["topic"].lower() == "chemical bonding"

    async def test_about_pattern_extracts_topic(self):
        generate = AsyncMock(return_value={"title": "Quiz", "questions": [], "answer_key": ""})

        with patch("src.core.teacher_copilot.pipeline.QuizAgent") as quiz_cls:
            agent_instance = MagicMock()
            agent_instance.generate = generate
            quiz_cls.return_value = agent_instance

            node = AssessmentCreatorNode(router=MagicMock())
            state = State(user_message="make an assessment about photosynthesis")
            await node(state)

        call = generate.await_args
        assert call is not None
        assert "photosynthesis" in call.kwargs["topic"].lower()
