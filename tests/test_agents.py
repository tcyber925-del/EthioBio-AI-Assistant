from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.agents.lesson_planner import LessonPlannerAgent
from src.agents.orchestrator import OrchestratorAgent
from src.agents.quiz import QuizAgent
from src.agents.safety import SafetyAgent
from src.agents.student_progress import StudentProgressAgent
from src.agents.translator import TranslatorAgent
from src.agents.tutor import TutorAgent
from src.llm.router import ModelRouter


@pytest.mark.asyncio
async def test_tutor_agent_basic(mock_router, mock_retriever):
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is a cell?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
    )
    assert "answer" in result
    assert "sources" in result
    assert "model_used" in result
    assert "confidence" in result


@pytest.mark.asyncio
async def test_tutor_agent_socratic_mode(mock_router, mock_retriever):
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is photosynthesis?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
        socratic_mode=True,
    )
    assert "answer" in result
    assert result.get("socratic_mode") is True
    assert "model_used" in result


@pytest.mark.asyncio
async def test_tutor_agent_normal_mode(mock_router, mock_retriever):
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is a cell?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
        socratic_mode=False,
    )
    assert "answer" in result
    assert result.get("socratic_mode") is False


@pytest.mark.asyncio
async def test_quiz_generation(mock_router):
    agent = QuizAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": '{"title": "Biology Quiz", "questions": [{"question_type": "multiple_choice", "question_text": "What is DNA?", "correct_answer": "Deoxyribonucleic acid", "difficulty": "easy"}], "answer_key": "1. Deoxyribonucleic acid"}',
        "model": "ollama/test",
    }

    result = await agent.generate(grade_level=10, topic="Genetics", question_count=1)
    assert "questions" in result
    assert len(result["questions"]) > 0
    assert result["questions"][0]["question_text"] == "What is DNA?"


@pytest.mark.asyncio
async def test_lesson_plan_generation(mock_router):
    agent = LessonPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": '{"objective": "Understand cell division", "prior_knowledge": "Basic cell structure", "explanation": "Mitosis and meiosis", "activities": [{"name": "Diagram drawing", "duration_minutes": 15, "description": "Draw cell division stages", "type": "individual"}], "assessment": "Quiz on stages", "homework": "Label diagrams", "teacher_notes": "Use visual aids"}',
        "model": "ollama/test",
    }

    result = await agent.generate(grade_level=10, topic="Cell Division")
    assert result["objective"] == "Understand cell division"
    assert len(result["activities"]) > 0


@pytest.mark.asyncio
async def test_orchestrator_intent_classification(mock_router):
    agent = OrchestratorAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": '{"intent": "tutor", "confidence": 0.95, "reason": "biology question"}',
        "model": "ollama/test",
    }

    intent = await agent.classify_intent("What is photosynthesis?")
    assert intent["intent"] == "tutor"
    assert intent["confidence"] > 0.9


@pytest.mark.asyncio
async def test_safety_review(mock_router):
    agent = SafetyAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": '{"safe": true, "issues": [], "score": 0.95, "suggestions": []}',
        "model": "ollama/test",
    }

    result = await agent.review("Mitosis is the process of cell division.")
    assert result["safe"] == True
    assert result["score"] > 0.9


@pytest.mark.asyncio
async def test_translator(mock_router):
    agent = TranslatorAgent(llm_router=mock_router)
    result = await agent.translate("What is a cell?", source_lang="en", target_lang="am")
    assert "translated_text" in result
    assert "model_used" in result


@pytest.mark.asyncio
async def test_tutor_agent_hint_level_1(mock_router, mock_retriever):
    """ST-003: Hint level 1 returns a broad hint."""
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is mitosis?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
        hint_level=1,
    )
    assert "answer" in result
    assert result.get("hint_level") == 1
    assert result.get("reveal_answer") is False


@pytest.mark.asyncio
async def test_tutor_agent_hint_level_2(mock_router, mock_retriever):
    """ST-003: Hint level 2 returns a more specific hint."""
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is mitosis?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
        hint_level=2,
    )
    assert "answer" in result
    assert result.get("hint_level") == 2


@pytest.mark.asyncio
async def test_tutor_agent_hint_level_3(mock_router, mock_retriever):
    """ST-003: Hint level 3 returns a very specific hint."""
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is mitosis?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
        hint_level=3,
    )
    assert "answer" in result
    assert result.get("hint_level") == 3


@pytest.mark.asyncio
async def test_tutor_agent_reveal_answer(mock_router, mock_retriever):
    """ST-003: Reveal answer provides full answer."""
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is mitosis?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
        hint_level=3,
        reveal_answer=True,
    )
    assert "answer" in result
    assert result.get("reveal_answer") is True
    assert result.get("hint_level") == 3


@pytest.mark.asyncio
async def test_tutor_agent_reveal_no_hints(mock_router, mock_retriever):
    """ST-005: Reveal answer works with hint_level=0 (no prior hints)."""
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is mitosis?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
        hint_level=0,
        reveal_answer=True,
    )
    assert "answer" in result
    assert result.get("reveal_answer") is True
    assert result.get("hint_level") == 0


@pytest.mark.asyncio
async def test_tutor_agent_reveal_tracks_attempts(mock_router, mock_retriever):
    """ST-005: Hint level is tracked as attempt count alongside reveal."""
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    for hint_lvl in [0, 1, 2, 3]:
        result = await agent.answer(
            question="What is mitosis?",
            user_id=uuid4(),
            grade_level=10,
            topic="Cell Biology",
            use_rag=True,
            hint_level=hint_lvl,
            reveal_answer=True,
        )
        assert result.get("hint_level") == hint_lvl
        assert result.get("reveal_answer") is True


@pytest.mark.asyncio
async def test_tutor_agent_hint_defaults(mock_router, mock_retriever):
    """ST-003: Default hint_level is 0 and reveal_answer is False."""
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is a cell?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
    )
    assert result.get("hint_level") == 0
    assert result.get("reveal_answer") is False


@pytest.mark.asyncio
async def test_tutor_agent_misconception_fields_present(mock_router, mock_retriever):
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is a cell?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
    )
    assert "misconception_detected" in result
    assert "misconception_correction" in result
    assert result["misconception_detected"] is False
    assert result["misconception_correction"] == ""


@pytest.mark.asyncio
async def test_tutor_agent_misconception_fields_socratic(mock_router, mock_retriever):
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is photosynthesis?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
        socratic_mode=True,
    )
    assert "misconception_detected" in result
    assert "misconception_correction" in result


@pytest.mark.asyncio
async def test_tutor_agent_normal_prompt_has_misconception_directive():
    from src.agents.tutor import TUTOR_SYSTEM_PROMPT
    assert "conceptual error" in TUTOR_SYSTEM_PROMPT
    assert "gently point it out" in TUTOR_SYSTEM_PROMPT
    assert "never condescending" in TUTOR_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_tutor_agent_socratic_prompt_has_misconception_directive():
    from src.agents.tutor import SOCRATIC_SYSTEM_PROMPT
    assert "conceptual error" in SOCRATIC_SYSTEM_PROMPT
    assert "gently correct" in SOCRATIC_SYSTEM_PROMPT
    assert "never condescending" in SOCRATIC_SYSTEM_PROMPT


def test_graph_node_prompt_has_misconception_directive():
    from src.graph.nodes.tutor import SOCRATIC_SYSTEM_PROMPT, SYSTEM_PROMPT
    assert "conceptual error" in SYSTEM_PROMPT
    assert "conceptual error" in SOCRATIC_SYSTEM_PROMPT
    assert "gently" in SYSTEM_PROMPT
    assert "gently" in SOCRATIC_SYSTEM_PROMPT


def test_schema_misconception_fields():
    from src.schemas.chat import TutorRequest, TutorResponse
    req = TutorRequest(user_id=uuid4(), question="test")
    assert hasattr(req, "misconception_detected")
    assert hasattr(req, "misconception_correction")
    assert req.misconception_detected is False
    assert req.misconception_correction == ""
    resp = TutorResponse(answer="test", language="en", model_used="test", confidence=0.9)
    assert hasattr(resp, "misconception_detected")
    assert hasattr(resp, "misconception_correction")
    assert resp.misconception_detected is False
    assert resp.misconception_correction == ""


@pytest.mark.asyncio
async def test_detect_misconception_detects_correction():
    from src.agents.tutor import detect_misconception
    response = (
        "That's not quite right. Mitochondria are not involved in photosynthesis."
        " They are the powerhouse of the cell."
    )
    detected, correction = detect_misconception(response)
    assert detected is True
    assert "mitochondria" in correction.lower() or "powerhouse" in correction.lower()


@pytest.mark.asyncio
async def test_detect_misconception_no_false_positive():
    from src.agents.tutor import detect_misconception
    response = (
        "Great question! Photosynthesis occurs in the chloroplasts"
        " of plant cells."
    )
    detected, _ = detect_misconception(response)
    assert detected is False


@pytest.mark.asyncio
async def test_detect_misconception_common_misconception():
    from src.agents.tutor import detect_misconception
    response = (
        "That's a common misconception. Evolution is not about individuals adapting,"
        " but about populations changing over generations through natural selection."
    )
    detected, correction = detect_misconception(response)
    assert detected is True
    assert "evolution" in correction.lower()


@pytest.mark.asyncio
async def test_detect_misconception_youre_confusing():
    from src.agents.tutor import detect_misconception
    response = (
        "I think you're confusing mitosis with meiosis."
        " Mitosis produces identical daughter cells, while meiosis produces gametes."
    )
    detected, correction = detect_misconception(response)
    assert detected is True
    assert "mitosis" in correction.lower()


@pytest.mark.asyncio
async def test_tutor_agent_misconception_detected_from_response(mock_router, mock_retriever):
    mock_router.route.return_value = {
        "content": (
            "That's not quite right. The cell membrane is not impermeable."
            " It is selectively permeable, allowing some molecules to pass"
            " while blocking others."
        ),
        "model": "ollama/test",
        "confidence": 0.95,
        "usage": {"total_tokens": 50},
    }
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="Is the cell membrane impermeable?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
    )
    assert result["misconception_detected"] is True
    assert "not impermeable" in result["misconception_correction"].lower()


@pytest.mark.asyncio
async def test_tutor_agent_misconception_not_detected_for_normal(mock_router, mock_retriever):
    mock_router.route.return_value = {
        "content": (
            "The cell membrane is selectively permeable."
            " It controls what enters and exits the cell."
        ),
        "model": "ollama/test",
        "confidence": 0.95,
        "usage": {"total_tokens": 50},
    }
    agent = TutorAgent(llm_router=mock_router, retriever=mock_retriever)
    result = await agent.answer(
        question="What is the cell membrane?",
        user_id=uuid4(),
        grade_level=10,
        topic="Cell Biology",
        use_rag=True,
    )
    assert result["misconception_detected"] is False
    assert result["misconception_correction"] == ""


def test_state_misconception_fields():
    from src.graph.state import AgentState, GraphOutput
    state = AgentState()
    assert state.misconception_detected is False
    assert state.misconception_correction == ""
    output = GraphOutput(
        answer="test", model_used="test", confidence=0.9,
        sources=[], status="ok", requires_teacher_review=False,
    )
    assert output.misconception_detected is False
    assert output.misconception_correction == ""


def test_diagram_validate_labels_all_correct():
    from src.agents.diagram import validate_labels
    correct = [
        {"id": "l1", "text": "Mitochondrion", "x": 100, "y": 100},
        {"id": "l2", "text": "Nucleus", "x": 200, "y": 200},
        {"id": "l3", "text": "Cell Membrane", "x": 300, "y": 300},
    ]
    submitted = [
        {"id": "l1", "text": "Mitochondrion", "x": 100, "y": 100},
        {"id": "l2", "text": "Nucleus", "x": 200, "y": 200},
        {"id": "l3", "text": "Cell Membrane", "x": 300, "y": 300},
    ]
    results = validate_labels(correct, submitted)
    assert len(results) == 3
    assert all(r["is_correct"] for r in results)


def test_diagram_validate_labels_some_incorrect():
    from src.agents.diagram import validate_labels
    correct = [
        {"id": "l1", "text": "Mitochondrion", "x": 100, "y": 100},
        {"id": "l2", "text": "Nucleus", "x": 200, "y": 200},
    ]
    submitted = [
        {"id": "l1", "text": "Mitochondrion", "x": 100, "y": 100},
        {"id": "l2", "text": "Ribosome", "x": 200, "y": 200},
    ]
    results = validate_labels(correct, submitted)
    assert results[0]["is_correct"] is True
    assert results[1]["is_correct"] is False
    assert "Ribosome" in results[1]["submitted_text"]
    assert "Nucleus" in results[1]["correct_text"]
    assert "correct label is 'Nucleus'" in results[1]["explanation"]


def test_diagram_validate_labels_case_insensitive():
    from src.agents.diagram import validate_labels
    correct = [
        {"id": "l1", "text": "Mitochondrion", "x": 100, "y": 100},
    ]
    submitted = [
        {"id": "l1", "text": "mitochondrion", "x": 100, "y": 100},
    ]
    results = validate_labels(correct, submitted)
    assert results[0]["is_correct"] is True


def test_diagram_validate_labels_unknown_id():
    from src.agents.diagram import validate_labels
    correct = [
        {"id": "l1", "text": "Mitochondrion", "x": 100, "y": 100},
    ]
    submitted = [
        {"id": "l1", "text": "Mitochondrion", "x": 100, "y": 100},
        {"id": "unknown", "text": "Nucleus", "x": 200, "y": 200},
    ]
    results = validate_labels(correct, submitted)
    assert results[0]["is_correct"] is True
    assert results[1]["is_correct"] is False
    assert "Unknown label" in results[1]["explanation"]


def test_diagram_validate_labels_whitespace_handling():
    from src.agents.diagram import validate_labels
    correct = [
        {"id": "l1", "text": "Cell Membrane", "x": 100, "y": 100},
    ]
    submitted = [
        {"id": "l1", "text": "  cell membrane  ", "x": 100, "y": 100},
    ]
    results = validate_labels(correct, submitted)
    assert results[0]["is_correct"] is True


def test_diagram_validate_labels_empty_submitted():
    from src.agents.diagram import validate_labels
    correct = [
        {"id": "l1", "text": "Mitochondrion", "x": 100, "y": 100},
    ]
    results = validate_labels(correct, [])
    assert len(results) == 0


@pytest.mark.asyncio
async def test_diagram_generate_prompt_difficulty():
    from src.agents.diagram import DiagramAgent

    router = AsyncMock()
    router.route = AsyncMock(return_value={
        "content": '{"title": "Test", "diagram_svg": "<svg></svg>", "labels": []}',
        "model": "test",
    })

    agent = DiagramAgent(llm_router=router)

    for difficulty, expected_range in [
        ("beginner", "3-5"),
        ("intermediate", "6-10"),
        ("advanced", "10-15"),
    ]:
        router.route.reset_mock()
        result = await agent.generate(
            prompt="Label a cell",
            topic="cells",
            difficulty=difficulty,
        )
        assert result["difficulty"] == difficulty
        call_args = router.route.call_args
        user_msg = call_args[1]["messages"][1]["content"]
        assert expected_range in user_msg, f"{expected_range} not in user message for {difficulty}"


def test_diagram_schema_validates_difficulty():
    from pydantic import ValidationError

    from src.schemas.diagram import DiagramGenerateRequest

    valid = DiagramGenerateRequest(prompt="Test", topic="cells", difficulty="advanced")
    assert valid.difficulty == "advanced"

    try:
        DiagramGenerateRequest(prompt="Test", topic="cells", difficulty="expert")
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_diagram_validate_request_schema():
    from uuid import uuid4

    from pydantic import ValidationError

    from src.schemas.diagram import DiagramValidateRequest

    valid = DiagramValidateRequest(
        user_id=uuid4(),
        correct_labels=[{"id": "l1", "text": "Nucleus", "x": 100, "y": 100}],
        submitted_labels=[{"id": "l1", "text": "Nucleus", "x": 100, "y": 100}],
        topic="cells",
        difficulty="intermediate",
    )
    assert valid.difficulty == "intermediate"

    try:
        DiagramValidateRequest(
            user_id=uuid4(),
            correct_labels=[{"id": "l1", "text": "Nucleus", "x": 100, "y": 100}],
            submitted_labels=[{"id": "l1", "text": "Nucleus", "x": 100, "y": 100}],
            topic="cells",
            difficulty="invalid",
        )
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_student_progress_analysis():
    router = ModelRouter()
    agent = StudentProgressAgent(llm_router=router)

    class MockRecord:
        def __init__(self, topic, score, total):
            self.topic = topic
            self.score = score
            self.total = total
            self.recorded_at = __import__("datetime").datetime.now()

    class MockProfile:
        id = uuid4()
        weak_areas = ["Genetics"]

    records = [
        MockRecord("Cell Biology", 80, 100),
        MockRecord("Cell Biology", 90, 100),
        MockRecord("Genetics", 40, 100),
        MockRecord("Genetics", 50, 100),
        MockRecord("Ecology", 75, 100),
    ]

    result = agent.analyze_progress(records, MockProfile())
    assert "topics" in result
    assert "weak_areas" in result
    assert "Genetics" in result["weak_areas"]
    assert result["overall_score"] > 0
