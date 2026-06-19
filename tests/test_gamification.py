from src.schemas.gamification import calculate_level, progress_pct, xp_for_next_level


def test_calculate_level_starts_at_one():
    assert calculate_level(0) == 1
    assert calculate_level(50) == 1


def test_calculate_level_thresholds():
    assert calculate_level(100) == 2
    assert calculate_level(250) == 3
    assert calculate_level(500) == 4
    assert calculate_level(1000) == 5
    assert calculate_level(1750) == 6


def test_calculate_level_high_values():
    assert calculate_level(10000) >= 11


def test_xp_for_next_level():
    assert xp_for_next_level(0) == 100
    assert xp_for_next_level(50) == 50
    assert xp_for_next_level(100) == 150


def test_xp_for_next_level_max_level():
    assert xp_for_next_level(100000) == 0


def test_quiz_xp_calculation():
    from src.telegram.bot import _calculate_quiz_xp
    assert _calculate_quiz_xp(50) == 10
    assert _calculate_quiz_xp(80) == 20
    assert _calculate_quiz_xp(90) == 20
    assert _calculate_quiz_xp(100) == 35


def test_progress_pct_at_level_start():
    assert progress_pct(0) == 0.0


def test_progress_pct_halfway():
    assert progress_pct(50) == 50.0


def test_progress_pct_near_level_up():
    assert progress_pct(99) == 99.0


def test_progress_pct_at_threshold():
    val = progress_pct(100)
    assert val == 0.0 or val == 100.0


def test_achievement_definitions_exist():
    from src.api.gamification import ACHIEVEMENT_DEFINITIONS
    expected = ["first_quiz", "quiz_master", "perfect_score", "streak_3", "streak_7", "streak_30", "xp_1000", "level_5", "level_10"]
    for ach_id in expected:
        assert ach_id in ACHIEVEMENT_DEFINITIONS
        assert "title" in ACHIEVEMENT_DEFINITIONS[ach_id]
        assert "icon" in ACHIEVEMENT_DEFINITIONS[ach_id]


def test_streak_bonus_thresholds():
    from src.api.gamification import STREAK_BONUS_THRESHOLDS
    assert STREAK_BONUS_THRESHOLDS[7] == 20
    assert STREAK_BONUS_THRESHOLDS[14] == 50
    assert STREAK_BONUS_THRESHOLDS[21] == 100
    assert STREAK_BONUS_THRESHOLDS[30] == 200


def test_tutor_interaction_xp_source():
    from src.api.gamification import XP_SOURCES
    assert "tutor_interaction" in XP_SOURCES
    assert XP_SOURCES["tutor_interaction"] == 5


def test_diagram_completion_xp_source():
    from src.api.gamification import XP_SOURCES
    assert "diagram_completion" in XP_SOURCES
    assert XP_SOURCES["diagram_completion"] == 10


def test_diagram_validate_response_has_xp_fields():
    from uuid import uuid4
    from src.schemas.diagram import DiagramValidateResponse, DiagramLabelResult
    resp = DiagramValidateResponse(
        score=80.0, total_labels=5, correct_count=4,
        results=[DiagramLabelResult(label_id="l1", correct_text="A", submitted_text="A", is_correct=True)],
        attempt_id=uuid4(),
    )
    assert hasattr(resp, "xp_awarded")
    assert hasattr(resp, "level_up")
    assert hasattr(resp, "new_level")
    assert resp.xp_awarded == 0
    assert resp.level_up is False


def test_chat_response_schema_has_xp_fields():
    from src.schemas.chat import TutorResponse
    resp = TutorResponse(answer="test", language="en", sources=[], model_used="test", confidence=0.5)
    assert hasattr(resp, "xp_awarded")
    assert hasattr(resp, "level_up")
    assert hasattr(resp, "new_level")
    assert resp.xp_awarded == 0
    assert resp.level_up is False


def test_graph_chat_response_schema_has_xp_fields():
    from src.api.graph import GraphChatResponse
    graph_resp = GraphChatResponse(answer="test", model_used="test", confidence=0.5)
    assert hasattr(graph_resp, "xp_awarded")
    assert hasattr(graph_resp, "level_up")
    assert hasattr(graph_resp, "new_level")
    assert graph_resp.xp_awarded == 0
