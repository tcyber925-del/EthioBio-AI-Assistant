import pytest
from unittest.mock import AsyncMock, patch
from src.llm.router import ModelRouter
from src.agents.tutor_agent import TutorAgent
from src.agents.quiz import QuizAgent
from src.agents.lesson_planner import LessonPlannerAgent
from src.agents.orchestrator import OrchestratorAgent
from src.agents.safety import SafetyAgent
from src.agents.translator import TranslatorAgent
from src.agents.student_progress import StudentProgressAgent
from src.agents.parent_summary import ParentSummaryAgent
from uuid import uuid4


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
async def test_quiz_generation(mock_router, mock_adapter):
    agent = QuizAgent(llm_router=mock_router, adapter=mock_adapter)
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
async def test_student_progress_analysis():
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

    result = await agent.analyze_progress(records, MockProfile())
    assert "topics" in result
    assert "weak_areas" in result
    assert "Genetics" in result["weak_areas"]
    assert result["overall_score"] > 0
