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
    from src.graph.nodes.tutor import SYSTEM_PROMPT, SOCRATIC_SYSTEM_PROMPT
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
