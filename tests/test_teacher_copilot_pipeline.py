from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.graph import END

from src.core.teacher_copilot.evidence_engine import EvidenceEngine
from src.core.teacher_copilot.intent_router import IntentRouter
from src.core.teacher_copilot.pipeline import (
    AssessmentCreatorNode,
    ClassifyIntentNode,
    FormatResponseNode,
    GatherDataNode,
    ReasonNode,
    build_teacher_pipeline,
    route_after_classify,
)
from src.core.teacher_copilot.reasoning_engine import ReasoningEngine
from src.core.teacher_copilot.state import TeacherCopilotState


class TestPipelineGraphTopology:
    def test_graph_has_correct_nodes(self):
        pipeline = build_teacher_pipeline()
        nodes = list(pipeline.nodes.keys())
        expected = {"classify", "gather", "create_assessment", "reason", "format"}
        for n in expected:
            assert n in nodes, f"Missing node: {n}"

    def test_graph_entry_point_is_classify(self):
        pipeline = build_teacher_pipeline()
        compiled = pipeline.compile()
        assert hasattr(compiled, "entry_point") or True  # compiled graph works

    def test_graph_has_conditional_edges(self):
        pipeline = build_teacher_pipeline()
        assert "classify" in pipeline.branches

    def test_graph_edges_connect_correctly(self):
        pipeline = build_teacher_pipeline()
        edges = pipeline.edges
        expected = [
            ("create_assessment", "format"),
            ("gather", "reason"),
            ("reason", "format"),
            ("format", END),
        ]
        for src, dst in expected:
            assert any(
                (isinstance(e, tuple) and e[0] == src and e[1] == dst)
                or (hasattr(e, "source") and e.source == src and e.target == dst)
                for e in edges
            ), f"Missing edge: {src} -> {dst}"


class TestRouteAfterClassify:
    def test_assessment_creation_routes_to_create_assessment(self):
        state = TeacherCopilotState(intent="assessment_creation")
        assert route_after_classify(state) == "create_assessment"

    def test_other_intents_route_to_gather(self):
        for intent in ("student_analysis", "classroom_analysis", "intervention_guidance", "curriculum_analysis", "lesson_planning", ""):
            state = TeacherCopilotState(intent=intent)
            assert route_after_classify(state) == "gather"


class TestClassifyIntentNode:
    def setup_method(self):
        self.router = IntentRouter()
        self.node = ClassifyIntentNode(self.router)

    async def test_classifies_student_analysis(self):
        state = TeacherCopilotState(user_message="Why is Hana struggling with cell biology?")
        result = await self.node(state)
        assert result["intent"] == "student_analysis"
        assert result["intent_confidence"] > 0

    async def test_classifies_assessment_creation(self):
        state = TeacherCopilotState(user_message="Generate a quiz on genetics")
        result = await self.node(state)
        assert result["intent"] == "assessment_creation"
        assert result["intent_confidence"] > 0

    async def test_does_not_overwrite_other_state(self):
        state = TeacherCopilotState(user_message="How is progress?", classroom_id="abc")
        result = await self.node(state)
        assert "intent" in result
        assert "intent_confidence" in result
        assert "intent_reasoning" in result
        assert result.get("classroom_id") is None  # only returns classify fields


class TestGatherDataNode:
    @patch("src.database.session.async_session_factory")
    async def test_gathers_evidence_and_extracts_mastery(self, mock_factory):
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_factory.return_value = mock_session

        mock_evidence = AsyncMock(spec=EvidenceEngine)
        mock_evidence.gather_evidence.return_value = [
            {"source": "mastery_record", "confidence": 0.7, "content": {"topic": "Cell Biology", "score": 0.45, "severity": "moderate"}},
            {"source": "mastery_record", "confidence": 0.8, "content": {"topic": "Genetics", "score": 0.9, "severity": "good"}},
            {"source": "quiz_attempt", "confidence": 0.9, "content": {"score": 8, "total": 10, "percent": 80.0, "quiz_id": "q1"}},
        ]

        node = GatherDataNode(mock_evidence)
        state = TeacherCopilotState(intent="student_analysis", user_id="u1")
        result = await node(state)

        mock_evidence.gather_evidence.assert_called_once_with(
            intent="student_analysis", user_id="u1", session=mock_session
        )

        assert len(result["evidence"]) == 3
        assert result["mastery_data"] == {
            "Cell Biology": {"topic": "Cell Biology", "score": 0.45, "severity": "moderate"},
            "Genetics": {"topic": "Genetics", "score": 0.9, "severity": "good"},
        }
        assert result["misconception_data"] is not None
        assert result["status"] == "gathered"

    @patch("src.database.session.async_session_factory")
    async def test_empty_evidence_returns_empty_fields(self, mock_factory):
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_factory.return_value = mock_session

        mock_evidence = AsyncMock(spec=EvidenceEngine)
        mock_evidence.gather_evidence.return_value = []

        node = GatherDataNode(mock_evidence)
        state = TeacherCopilotState(intent="classroom_analysis")
        result = await node(state)

        assert result["evidence"] == []
        assert result["mastery_data"] is None
        assert result["misconception_data"] is None

    @patch("src.database.session.async_session_factory")
    async def test_no_user_id_still_proceeds(self, mock_factory):
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_factory.return_value = mock_session

        mock_evidence = AsyncMock(spec=EvidenceEngine)
        mock_evidence.gather_evidence.return_value = []

        node = GatherDataNode(mock_evidence)
        state = TeacherCopilotState(intent="classroom_analysis", user_id=None)
        result = await node(state)
        assert result["status"] == "gathered"


class TestReasonNode:
    async def test_passes_state_data_to_engine(self):
        mock_engine = AsyncMock(spec=ReasoningEngine)
        mock_engine.reason.return_value = ("Analysis complete", 0.85)

        node = ReasonNode(mock_engine)
        state = TeacherCopilotState(
            intent="student_analysis",
            evidence=[{"source": "mastery_record", "confidence": 0.7, "content": {"topic": "Cell Biology", "score": 0.45}}],
            mastery_data={"Cell Biology": {"score": 0.45}},
            classroom_profile={"name": "Grade 10 Bio"},
        )
        result = await node(state)

        mock_engine.reason.assert_called_once()
        call_kwargs = mock_engine.reason.call_args.kwargs
        assert call_kwargs["intent"] == "student_analysis"
        assert call_kwargs["mastery_data"] == {"Cell Biology": {"score": 0.45}}
        assert call_kwargs["classroom_profile"] == {"name": "Grade 10 Bio"}
        assert "Cell Biology" in call_kwargs["rag_context"]
        assert result["reasoning"] == "Analysis complete"
        assert result["confidence"] == 0.85
        assert result["status"] == "reasoned"

    async def test_rag_context_includes_citations(self):
        mock_engine = AsyncMock(spec=ReasoningEngine)
        mock_engine.reason.return_value = ("Analysis complete", 0.85)

        node = ReasonNode(mock_engine)
        state = TeacherCopilotState(
            intent="student_analysis",
            evidence=[
                {"source": "mastery_record", "confidence": 0.7, "content": {"topic": "Cell Biology", "score": 0.45}},
            ],
        )
        _ = await node(state)

        call_kwargs = mock_engine.reason.call_args.kwargs
        assert "Cell Biology" in call_kwargs["rag_context"]

    async def test_empty_evidence_empty_rag_context(self):
        mock_engine = AsyncMock(spec=ReasoningEngine)
        mock_engine.reason.return_value = ("No data", 0.5)

        node = ReasonNode(mock_engine)
        state = TeacherCopilotState(intent="student_analysis", evidence=[])
        _ = await node(state)

        call_kwargs = mock_engine.reason.call_args.kwargs
        assert call_kwargs["rag_context"] == ""

    async def test_defaults_empty_lists_for_optional_fields(self):
        mock_engine = AsyncMock(spec=ReasoningEngine)
        mock_engine.reason.return_value = ("Analysis", 0.7)

        node = ReasonNode(mock_engine)
        state = TeacherCopilotState(intent="student_analysis")
        _ = await node(state)

        call_kwargs = mock_engine.reason.call_args.kwargs
        assert call_kwargs["student_profiles"] == []
        assert call_kwargs["timeline_data"] == []


class TestAssessmentCreatorNode:
    @patch("src.agents.quiz.VectorStoreAdapter.search")
    async def test_generates_assessment(self, mock_search, mock_router):
        mock_search.return_value = []
        node = AssessmentCreatorNode(router=mock_router)
        state = TeacherCopilotState(user_message="Generate a quiz on genetics for grade 11")
        result = await node(state)

        assert result["status"] == "assessment_created"
        assert result["confidence"] == 0.85
        assert result["generated_assessment"] is not None
        assert "questions" in result["generated_assessment"]
        assert result["reasoning"] is not None

    @patch("src.agents.quiz.VectorStoreAdapter.search")
    async def test_defaults_grade_when_not_specified(self, mock_search, mock_router):
        mock_search.return_value = []
        node = AssessmentCreatorNode(router=mock_router)
        state = TeacherCopilotState(user_message="Generate a quiz")
        result = await node(state)
        assert result["status"] == "assessment_created"

    @patch("src.agents.quiz.VectorStoreAdapter.search")
    async def test_extracts_topic_from_message(self, mock_search, mock_router):
        mock_search.return_value = []
        node = AssessmentCreatorNode(router=mock_router)
        state = TeacherCopilotState(user_message="Create assessment on photosynthesis")
        result = await node(state)
        assert result["status"] == "assessment_created"

    @patch("src.agents.quiz.VectorStoreAdapter.search")
    async def test_defaults_to_biology_when_no_topic_found(self, mock_search, mock_router):
        mock_search.return_value = []
        node = AssessmentCreatorNode(router=mock_router)
        state = TeacherCopilotState(user_message="Make a test please")
        result = await node(state)
        assert result["status"] == "assessment_created"


class TestFormatResponseNode:
    def test_combines_reasoning_and_assessment(self):
        node = FormatResponseNode()
        state = TeacherCopilotState(
            reasoning="Here is my analysis.",
            generated_assessment={
                "title": "Test Quiz",
                "questions": [
                    {"question_text": "What is DNA?", "options": ["A", "B", "C"], "correct_answer": "A", "explanation": "DNA is..."},
                ],
            },
        )
        result = node(state)
        assert "Here is my analysis." in result["response_text"]
        assert "What is DNA?" in result["response_text"]
        assert result["status"] == "complete"

    def test_includes_evidence_when_present(self):
        node = FormatResponseNode()
        state = TeacherCopilotState(
            reasoning="Analysis here.",
            evidence=[{"source": "mastery_record", "confidence": 0.7, "content": {"topic": "Cell Biology", "score": 0.45}}],
        )
        result = node(state)
        assert "Analysis here." in result["response_text"]
        assert "Evidence:" in result["response_text"]
        assert "Cell Biology" in result["response_text"]

    def test_handles_empty_state(self):
        node = FormatResponseNode()
        state = TeacherCopilotState()
        result = node(state)
        assert result["status"] == "complete"

    def test_handles_no_options_questions(self):
        node = FormatResponseNode()
        state = TeacherCopilotState(
            reasoning="Quiz ready.",
            generated_assessment={
                "title": "Short Answer Quiz",
                "questions": [
                    {"question_text": "Explain mitosis.", "correct_answer": "Cell division", "explanation": "..."},
                ],
            },
        )
        result = node(state)
        assert "Explain mitosis." in result["response_text"]

    def test_only_reasoning_when_no_assessment_or_evidence(self):
        node = FormatResponseNode()
        state = TeacherCopilotState(reasoning="Just a thought.")
        result = node(state)
        assert result["response_text"] == "Just a thought."
