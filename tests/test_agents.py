from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.agents.lesson_planner import LessonPlannerAgent
from src.agents.orchestrator import OrchestratorAgent
from src.agents.quiz import QuizAgent
from src.agents.safety import SafetyAgent
from src.agents.student_progress import StudentProgressAgent
from src.agents.translator import TranslatorAgent
from src.agents.tutor_agent import TutorAgent
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
async def test_quiz_generation(mock_router, mock_retriever):
    mock_retriever.search = AsyncMock(return_value=[])
    mock_retriever.format_context.return_value = "Test curriculum context"
    agent = QuizAgent(llm_router=mock_router, adapter=mock_retriever)
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
async def test_lesson_plan_with_exit_ticket(mock_router):
    agent = LessonPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.side_effect = [
        {
            "content": '{"objective": "Understand mitosis", "prior_knowledge": "Cell theory", "explanation": "Mitosis phases", "activities": [{"name": "Draw phases", "duration_minutes": 15, "description": "Draw each phase", "type": "individual"}], "assessment": "Label phases", "homework": "Review notes", "teacher_notes": "Use diagrams"}',
            "model": "ollama/test",
        },
        {
            "content": '[{"question_type": "multiple_choice", "question_text": "What is mitosis?", "options": ["A) Cell division", "B) Cell death", "C) Cell growth", "D) Cell transport"], "correct_answer": "A) Cell division", "explanation": "Mitosis is cell division"}]',
            "model": "ollama/test",
        },
    ]

    result = await agent.generate(
        grade_level=10, topic="Mitosis",
        generate_exit_ticket=True,
    )
    assert result["objective"] == "Understand mitosis"
    assert "exit_ticket" in result
    assert len(result["exit_ticket"]) == 1
    assert result["exit_ticket"][0]["question_type"] == "multiple_choice"


@pytest.mark.asyncio
async def test_lesson_plan_with_differentiation(mock_router):
    agent = LessonPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.side_effect = [
        {
            "content": '{"objective": "Understand photosynthesis", "prior_knowledge": "Plant cells", "explanation": "Photosynthesis process", "activities": [{"name": "Leaf experiment", "duration_minutes": 20, "description": "Test for starch", "type": "group"}], "assessment": "Written questions", "homework": "Diagram labeling", "teacher_notes": "Prepare iodine"}',
            "model": "ollama/test",
        },
        {
            "content": '[{"group": "support", "description": "Label diagram with word bank", "duration_minutes": 15}, {"group": "standard", "description": "Write photosynthesis equation", "duration_minutes": 15}, {"group": "advanced", "description": "Explain limiting factors", "duration_minutes": 15}]',
            "model": "ollama/test",
        },
    ]

    result = await agent.generate(
        grade_level=10, topic="Photosynthesis",
        generate_differentiation=True,
    )
    assert result["objective"] == "Understand photosynthesis"
    assert "differentiation" in result
    assert len(result["differentiation"]) == 3
    groups = [d["group"] for d in result["differentiation"]]
    assert "support" in groups
    assert "standard" in groups
    assert "advanced" in groups


@pytest.mark.asyncio
async def test_lesson_plan_with_diagram_suggestions(mock_router):
    agent = LessonPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.side_effect = [
        {
            "content": '{"objective": "Identify cell organelles", "prior_knowledge": "Cell theory", "explanation": "Organelle functions", "activities": [{"name": "Microscope lab", "duration_minutes": 25, "description": "View prepared slides", "type": "pair"}], "assessment": "Organelle quiz", "homework": "Draw and label", "teacher_notes": "Prepare slides"}',
            "model": "ollama/test",
        },
        {
            "content": '[{"title": "Animal Cell", "description": "Labeled animal cell diagram", "diagram_type": "labeling"}, {"title": "Cell Comparison", "description": "Plant vs animal cell", "diagram_type": "comparison"}]',
            "model": "ollama/test",
        },
    ]

    result = await agent.generate(
        grade_level=10, topic="Cell Organelles",
        generate_diagram_suggestions=True,
    )
    assert result["objective"] == "Identify cell organelles"
    assert "diagram_suggestions" in result
    assert len(result["diagram_suggestions"]) == 2
    assert result["diagram_suggestions"][0]["diagram_type"] == "labeling"


@pytest.mark.asyncio
async def test_lesson_plan_with_misconception_activities(mock_router):
    agent = LessonPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.side_effect = [
        {
            "content": '{"objective": "Understand plant respiration", "prior_knowledge": "Cellular respiration", "explanation": "Plants respire too", "activities": [{"name": "Experiment design", "duration_minutes": 20, "description": "Design respiration experiment", "type": "group"}], "assessment": "Explain results", "homework": "Read chapter", "teacher_notes": "Prepare seeds"}',
            "model": "ollama/test",
        },
        {
            "content": '[{"misconception": "Plants do not respire", "activity_name": "Evidence Challenge", "description": "Students compare data from plant respiration experiment", "duration_minutes": 15, "activity_type": "evidence_challenge"}]',
            "model": "ollama/test",
        },
    ]

    classroom_context = {
        "misconceptions": {
            "by_topic": [
                {"topic": "Plant Respiration", "top_pattern": "Plants do not respire", "affected_students": 12},
            ],
        },
    }

    result = await agent.generate(
        grade_level=10, topic="Plant Respiration",
        generate_misconception_activities=True,
        classroom_context=classroom_context,
    )
    assert result["objective"] == "Understand plant respiration"
    assert "misconception_activities" in result
    assert len(result["misconception_activities"]) == 1
    assert result["misconception_activities"][0]["activity_type"] == "evidence_challenge"


@pytest.mark.asyncio
async def test_lesson_plan_all_features(mock_router):
    agent = LessonPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.side_effect = [
        {
            "content": '{"objective": "Learn genetics", "prior_knowledge": "Cell division", "explanation": "DNA structure and function", "activities": [{"name": "DNA model", "duration_minutes": 20, "description": "Build DNA model", "type": "group"}], "assessment": "DNA quiz", "homework": "Review notes", "teacher_notes": "Prepare materials"}',
            "model": "ollama/test",
        },
        {"content": '[{"question_type": "true_false", "question_text": "DNA is single-stranded", "options": ["True", "False"], "correct_answer": "False", "explanation": "DNA is double-stranded"}]', "model": "ollama/test"},
        {"content": '[{"group": "support", "description": "Label DNA components", "duration_minutes": 10}, {"group": "standard", "description": "Describe DNA replication", "duration_minutes": 10}, {"group": "advanced", "description": "Explain mutation effects", "duration_minutes": 10}]', "model": "ollama/test"},
        {"content": '[{"title": "DNA Double Helix", "description": "Structure of DNA", "diagram_type": "labeling"}]', "model": "ollama/test"},
        {"content": '[{"misconception": "Genes only exist in reproductive cells", "activity_name": "Concept Conflict", "description": "Challenge misconception with evidence", "duration_minutes": 12, "activity_type": "concept_conflict"}]', "model": "ollama/test"},
    ]

    classroom_context = {
        "misconceptions": {
            "by_topic": [
                {"topic": "Genetics", "top_pattern": "Genes only exist in reproductive cells", "affected_students": 8},
            ],
        },
    }

    result = await agent.generate(
        grade_level=10, topic="Genetics",
        generate_exit_ticket=True,
        generate_differentiation=True,
        generate_diagram_suggestions=True,
        generate_misconception_activities=True,
        classroom_context=classroom_context,
    )
    assert "exit_ticket" in result
    assert len(result["exit_ticket"]) == 1
    assert "differentiation" in result
    assert len(result["differentiation"]) == 3
    assert "diagram_suggestions" in result
    assert len(result["diagram_suggestions"]) == 1
    assert "misconception_activities" in result
    assert len(result["misconception_activities"]) == 1


@pytest.mark.asyncio
async def test_lesson_plan_with_classroom_context(mock_router):
    agent = LessonPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": '{"objective": "Learn ecology", "prior_knowledge": "Ecosystem basics", "explanation": "Food chains and webs", "activities": [{"name": "Build food web", "duration_minutes": 20, "description": "Create a food web", "type": "group"}], "assessment": "Food web quiz", "homework": "Research local ecosystem", "teacher_notes": "Use examples"}',
        "model": "ollama/test",
    }

    classroom_context = {
        "classroom": {
            "total_students": 45,
            "classroom_health": 72.5,
            "readiness_distribution": {"low": 8, "medium": 22, "high": 15},
            "risk_students": [{"student_id": "abc", "readiness_score": 35, "risk_level": "high", "risk_factors": ["low_mastery"]}],
        },
        "misconceptions": {
            "by_topic": [
                {"topic": "Ecology", "top_pattern": "Producers don\'t need energy", "affected_students": 10},
            ],
        },
        "prerequisite_gaps": [
            {"topic": "Photosynthesis", "affected_count": 5, "total_checked": 10},
        ],
        "best_strategies": [
            {"type": "diagram_based_learning", "avg_effectiveness": 85.0},
        ],
    }

    result = await agent.generate(
        grade_level=10, topic="Ecology",
        classroom_context=classroom_context,
    )
    assert result["objective"] == "Learn ecology"
    assert len(result["activities"]) > 0


@pytest.mark.asyncio
async def test_lesson_plan_parse_error_fallback(mock_router):
    agent = LessonPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": "This is not valid JSON at all",
        "model": "ollama/test",
    }

    result = await agent.generate(grade_level=10, topic="Invalid")
    assert result["objective"] == "Error parsing lesson plan"
    assert "explanation" in result


def test_derive_activities_from_periods():
    from src.agents.lesson_planner import _derive_activities_from_periods

    periods = [
        {"name": "Opening", "duration_minutes": 5, "description": "Warm-up", "activity_type": "teacher_led"},
        {"name": "Direct Instruction", "duration_minutes": 15, "description": "Lecture", "activity_type": "teacher_led"},
        {"name": "Guided Practice", "duration_minutes": 10, "description": "Group work", "activity_type": "group"},
    ]

    activities = _derive_activities_from_periods(periods)

    assert len(activities) == 3
    assert activities[0]["name"] == "Opening"
    assert activities[0]["duration_minutes"] == 5
    assert activities[0]["description"] == "Warm-up"
    assert activities[0]["type"] == "teacher_led"
    assert activities[1]["name"] == "Direct Instruction"
    assert activities[2]["name"] == "Guided Practice"


@pytest.mark.asyncio
async def test_lesson_plan_with_periods(mock_router):
    agent = LessonPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": '{"objective": "Understand cell division", "prior_knowledge": "Basic cell structure", "explanation": "Mitosis and meiosis", "periods": [{"name": "Opening", "duration_minutes": 5, "objective": "Engage students", "description": "Quick review game", "activity_type": "teacher_led", "teacher_activity": "Pose questions", "student_activity": "Answer in pairs", "materials_needed": ["Whiteboard"]}, {"name": "Direct Instruction", "duration_minutes": 15, "description": "Explain mitosis phases", "activity_type": "lecture", "teacher_activity": "Diagram on board", "student_activity": "Take notes", "materials_needed": ["Chalk", "Diagram"]}, {"name": "Guided Practice", "duration_minutes": 10, "description": "Label mitosis stages", "activity_type": "individual", "teacher_activity": "Circulate and assist", "student_activity": "Complete worksheet"}, {"name": "Independent Work", "duration_minutes": 8, "description": "Answer review questions", "activity_type": "individual"}, {"name": "Closing", "duration_minutes": 2, "description": "Summarize key points", "activity_type": "teacher_led"}], "assessment": "Quiz on stages", "homework": "Label diagrams", "teacher_notes": "Use visual aids"}',
        "model": "ollama/test",
    }

    result = await agent.generate(grade_level=10, topic="Cell Division")
    assert result["objective"] == "Understand cell division"
    assert "periods" in result
    assert len(result["periods"]) == 5
    assert result["periods"][0]["name"] == "Opening"
    assert result["periods"][4]["name"] == "Closing"
    assert "activities" in result
    assert len(result["activities"]) == 5
    assert result["activities"][0]["name"] == "Opening"
    assert result["activities"][0]["description"] == "Quick review game"
    assert result["activities"][0]["type"] == "teacher_led"
    assert result["activities"][4]["name"] == "Closing"


@pytest.mark.asyncio
async def test_lesson_plan_periods_backward_compat(mock_router):
    agent = LessonPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": '{"objective": "Understand cell division", "prior_knowledge": "Basic cell structure", "explanation": "Mitosis and meiosis", "activities": [{"name": "Diagram drawing", "duration_minutes": 15, "description": "Draw cell division stages", "type": "individual"}], "assessment": "Quiz on stages", "homework": "Label diagrams", "teacher_notes": "Use visual aids"}',
        "model": "ollama/test",
    }

    result = await agent.generate(grade_level=10, topic="Cell Division")
    assert result["objective"] == "Understand cell division"
    assert "periods" not in result or result["periods"] is None
    assert len(result["activities"]) == 1
    assert result["activities"][0]["name"] == "Diagram drawing"
    assert result["activities"][0]["type"] == "individual"


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
    from src.agents.tutor_agent import TUTOR_SYSTEM_PROMPT
    assert "conceptual error" in TUTOR_SYSTEM_PROMPT
    assert "gently point it out" in TUTOR_SYSTEM_PROMPT
    assert "never condescending" in TUTOR_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_tutor_agent_socratic_prompt_has_misconception_directive():
    from src.agents.tutor_agent import SOCRATIC_SYSTEM_PROMPT
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
    from src.agents.tutor_agent import detect_misconception
    response = (
        "That's not quite right. Mitochondria are not involved in photosynthesis."
        " They are the powerhouse of the cell."
    )
    detected, correction = detect_misconception(response)
    assert detected is True
    assert "mitochondria" in correction.lower() or "powerhouse" in correction.lower()


@pytest.mark.asyncio
async def test_detect_misconception_no_false_positive():
    from src.agents.tutor_agent import detect_misconception
    response = (
        "Great question! Photosynthesis occurs in the chloroplasts"
        " of plant cells."
    )
    detected, _ = detect_misconception(response)
    assert detected is False


@pytest.mark.asyncio
async def test_detect_misconception_common_misconception():
    from src.agents.tutor_agent import detect_misconception
    response = (
        "That's a common misconception. Evolution is not about individuals adapting,"
        " but about populations changing over generations through natural selection."
    )
    detected, correction = detect_misconception(response)
    assert detected is True
    assert "evolution" in correction.lower()


@pytest.mark.asyncio
async def test_detect_misconception_youre_confusing():
    from src.agents.tutor_agent import detect_misconception
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


@pytest.mark.asyncio
async def test_diagram_generate_with_preferred_model():
    from src.agents.diagram import DiagramAgent

    router = AsyncMock()
    router.route = AsyncMock(return_value={
        "content": '{"title": "Test", "diagram_svg": "<svg></svg>", "labels": []}',
        "model": "openrouter/openai/gpt-4o",
    })

    agent = DiagramAgent(llm_router=router)
    result = await agent.generate(
        prompt="Test cell",
        topic="cells",
        difficulty="beginner",
        preferred_model="openrouter/openai/gpt-4o",
    )
    call_args = router.route.call_args
    assert call_args[1]["preferred_model"] == "openrouter/openai/gpt-4o"
    assert result["model_used"] == "openrouter/openai/gpt-4o"


@pytest.mark.asyncio
async def test_diagram_generate_default_model_when_none():
    from src.agents.diagram import DiagramAgent

    router = AsyncMock()
    router.route = AsyncMock(return_value={
        "content": '{"title": "Test", "diagram_svg": "<svg></svg>", "labels": []}',
        "model": "ollama/tinyllama",
    })

    agent = DiagramAgent(llm_router=router)
    result = await agent.generate(
        prompt="Test cell",
        topic="cells",
    )
    call_args = router.route.call_args
    assert call_args[1]["preferred_model"] is None
    assert result["model_used"] == "ollama/tinyllama"


@pytest.mark.asyncio
async def test_quiz_generation_with_weak_topics(mock_router):
    mock_adapter = AsyncMock()
    mock_adapter.search = AsyncMock(return_value=[])
    mock_adapter.format_context.return_value = "Test curriculum context"
    agent = QuizAgent(llm_router=mock_router, adapter=mock_adapter)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": '{"title": "Adaptive Quiz", "questions": [{"question_type": "multiple_choice", "question_text": "What is a cell?", "correct_answer": "Basic unit of life", "difficulty": "easy"}], "answer_key": "1. Basic unit of life"}',
        "model": "ollama/test",
    }

    weak_topics = [
        {"topic": "Cell Biology", "unit": "Unit 1", "grade_level": 10,
         "average_score": 35.0, "attempt_count": 2, "severity": "critical",
         "confidence": 0.67, "misconceptions": [], "last_assessed_at": None},
    ]

    result = await agent.generate(
        grade_level=10,
        topic="Cell Biology",
        question_count=1,
        weak_topics=weak_topics,
        target_difficulty="easy",
    )
    assert "questions" in result
    assert len(result["questions"]) > 0
    call_args = agent._call_llm.call_args
    user_msg = call_args[1]["user_message"]
    assert "WEAK TOPICS" in user_msg
    assert "35% mastery" in user_msg
    assert "critical" in user_msg


@pytest.mark.asyncio
async def test_quiz_generation_weak_topics_difficulty_adaptation(mock_router):
    mock_adapter = AsyncMock()
    mock_adapter.search = AsyncMock(return_value=[])
    mock_adapter.format_context.return_value = "Test context"
    agent = QuizAgent(llm_router=mock_router, adapter=mock_adapter)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": '{"title": "Adaptive Quiz", "questions": [], "answer_key": ""}',
        "model": "ollama/test",
    }

    weak_critical = [
        {"topic": "Cell Biology", "unit": "Unit 1", "grade_level": 10,
         "average_score": 30.0, "attempt_count": 1, "severity": "critical",
         "confidence": 0.33, "misconceptions": [], "last_assessed_at": None},
    ]
    weak_moderate = [
        {"topic": "Cell Biology", "unit": "Unit 1", "grade_level": 10,
         "average_score": 55.0, "attempt_count": 2, "severity": "moderate",
         "confidence": 0.67, "misconceptions": [], "last_assessed_at": None},
    ]
    weak_mild = [
        {"topic": "Cell Biology", "unit": "Unit 1", "grade_level": 10,
         "average_score": 70.0, "attempt_count": 3, "severity": "mild",
         "confidence": 1.0, "misconceptions": [], "last_assessed_at": None},
    ]

    await agent.generate(grade_level=10, topic="Cell Biology", weak_topics=weak_critical)
    msg1 = agent._call_llm.call_args[1]["user_message"]
    assert "EASY" in msg1

    await agent.generate(grade_level=10, topic="Cell Biology", weak_topics=weak_moderate)
    msg2 = agent._call_llm.call_args[1]["user_message"]
    assert "MIXED" in msg2

    await agent.generate(grade_level=10, topic="Cell Biology", weak_topics=weak_mild)
    msg3 = agent._call_llm.call_args[1]["user_message"]
    assert "MEDIUM/HARD" in msg3


@pytest.mark.asyncio
async def test_quiz_generation_target_difficulty_override(mock_router):
    mock_adapter = AsyncMock()
    mock_adapter.search = AsyncMock(return_value=[])
    mock_adapter.format_context.return_value = "Test context"
    agent = QuizAgent(llm_router=mock_router, adapter=mock_adapter)
    agent._call_llm = AsyncMock()
    agent._call_llm.return_value = {
        "content": '{"title": "Hard Quiz", "questions": [], "answer_key": ""}',
        "model": "ollama/test",
    }

    await agent.generate(grade_level=10, topic="Cell Biology", target_difficulty="hard")
    msg = agent._call_llm.call_args[1]["user_message"]
    assert "HARD questions" in msg

    await agent.generate(grade_level=10, topic="Cell Biology", target_difficulty="easy")
    msg = agent._call_llm.call_args[1]["user_message"]
    assert "EASY questions" in msg


@pytest.mark.asyncio
async def test_unit_plan_generation(mock_router):
    from src.agents.unit_planner import UnitPlannerAgent

    outline_json = (
        '[{"day": 1, "subtopic": "Cell Structure", "objective": "Identify organelles"},'
        '{"day": 2, "subtopic": "Cell Division", "objective": "Explain mitosis"},'
        '{"day": 3, "subtopic": "DNA", "objective": "Describe DNA replication"}]'
    )
    lesson_json = (
        '{"objective": "Understand topic", "prior_knowledge": "Basic knowledge",'
        '"explanation": "Content", "activities": [{"name": "Act1", "duration_minutes": 15,'
        '"description": "Do it", "type": "individual"}], "assessment": "Quiz",'
        '"homework": "Review", "teacher_notes": "Notes"}'
    )

    agent = UnitPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock(return_value={
        "content": outline_json,
        "model": "ollama/test",
    })

    mock_router.route.return_value = {
        "content": lesson_json,
        "model": "ollama/test",
    }

    result = await agent.generate_unit(
        unit_title="Cell Biology Unit",
        grade_level=10,
        topic="Cell Biology",
        days=3,
    )

    assert result["unit_title"] == "Cell Biology Unit"
    assert result["days"] == 3
    assert len(result["lessons"]) == 3
    assert result["lessons"][0]["day_index"] == 1
    assert result["lessons"][0]["subtopic"] == "Cell Structure"
    assert "lesson" in result["lessons"][0]
    assert result["lessons"][0]["lesson"]["objective"] == "Understand topic"
    assert result["lessons"][2]["day_index"] == 3


@pytest.mark.asyncio
async def test_unit_plan_outline_fallback(mock_router):
    from src.agents.unit_planner import UnitPlannerAgent

    lesson_json = (
        '{"objective": "Objective", "prior_knowledge": "Pre",'
        '"explanation": "Exp", "activities": [{"name": "A", "duration_minutes": 10,'
        '"description": "D", "type": "pair"}], "assessment": "A",'
        '"homework": "H", "teacher_notes": "T"}'
    )

    agent = UnitPlannerAgent(llm_router=mock_router)
    agent._call_llm = AsyncMock(return_value={
        "content": "invalid json here",
        "model": "ollama/test",
    })

    mock_router.route.return_value = {
        "content": lesson_json,
        "model": "ollama/test",
    }

    result = await agent.generate_unit(
        unit_title="Fallback Unit",
        grade_level=10,
        topic="Biology",
        days=2,
    )

    assert result["unit_title"] == "Fallback Unit"
    assert result["days"] == 2
    assert len(result["lessons"]) == 2
    assert result["lessons"][0]["day_index"] == 1
    assert result["lessons"][1]["day_index"] == 2
