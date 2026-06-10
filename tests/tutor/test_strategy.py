from src.agents.tutor.models import TeachingStrategy
from src.agents.tutor.strategy import select_teaching_strategy


def test_socratic_mode_returns_socratic():
    result = select_teaching_strategy(
        user_message="What is mitosis?",
        socratic_mode=True,
        hint_level=0,
        intent="tutor",
        misconception_detected=False,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.SOCRATIC


def test_hint_level_triggers_socratic():
    result = select_teaching_strategy(
        user_message="What is mitosis?",
        socratic_mode=False,
        hint_level=2,
        intent="tutor",
        misconception_detected=False,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.SOCRATIC


def test_quiz_intent_returns_assessment_prep():
    result = select_teaching_strategy(
        user_message="Quiz me on genetics",
        socratic_mode=False,
        hint_level=0,
        intent="quiz",
        misconception_detected=False,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.ASSESSMENT_PREP


def test_misconception_returns_remediation():
    result = select_teaching_strategy(
        user_message="Why do I struggle with genetics?",
        socratic_mode=False,
        hint_level=0,
        intent="tutor",
        misconception_detected=True,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.REMEDIATION


def test_conceptual_question_returns_guided_discovery():
    result = select_teaching_strategy(
        user_message="Why is meiosis important?",
        socratic_mode=False,
        hint_level=0,
        intent="tutor",
        misconception_detected=False,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.GUIDED_DISCOVERY


def test_factual_question_returns_direct_explanation():
    result = select_teaching_strategy(
        user_message="What is osmosis?",
        socratic_mode=False,
        hint_level=0,
        intent="tutor",
        misconception_detected=False,
        learner_profile_block="",
    )
    assert result == TeachingStrategy.DIRECT_EXPLANATION


def test_weak_area_in_profile_returns_remediation():
    result = select_teaching_strategy(
        user_message="Tell me about genetics",
        socratic_mode=False,
        hint_level=0,
        intent="tutor",
        misconception_detected=False,
        learner_profile_block="weak_areas: genetics, cell division",
    )
    assert result == TeachingStrategy.REMEDIATION
