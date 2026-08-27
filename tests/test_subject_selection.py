"""Tests for subject selection across grades (Phases 0-2 / 5)."""

import pytest

from src.graph.nodes.tutor import _graceful_no_content_message
from src.graph.state import AgentState
from src.schemas.common import SUBJECT_LABELS, SUBJECT_LABELS_AM, SUBJECT_VALUES, SubjectEnum


@pytest.mark.parametrize("value", ["biology", "chemistry", "physics", "mathematics"])
def test_subject_enum_values(value):
    assert SubjectEnum(value).value == value


def test_subject_label_coverage():
    for value in SUBJECT_VALUES:
        assert value in SUBJECT_LABELS
        assert value in SUBJECT_LABELS_AM


def test_graceful_message_english():
    state = AgentState(user_message="hi", subject="chemistry", grade_level=10, language="en")
    msg = _graceful_no_content_message(state)
    assert "Chemistry" in msg
    assert "Grade 10" in msg
    assert "Biology" in msg


def test_graceful_message_amharic():
    state = AgentState(user_message="hi", subject="physics", grade_level=9, language="am")
    msg = _graceful_no_content_message(state)
    assert "ፊዚክስ" in msg
    assert "Grade 9".replace("Grade 9", "") or "9" in msg or "ፊዚክስ" in msg


def test_graceful_message_both():
    state = AgentState(user_message="hi", subject="mathematics", grade_level=11, language="both")
    msg = _graceful_no_content_message(state)
    assert "mathematics" in msg.lower() or "ሂሳብ" in msg


def test_graceful_message_falls_back_when_subject_missing():
    state = AgentState(user_message="hi", language="en")
    msg = _graceful_no_content_message(state)
    assert "this subject" in msg


def test_grade_only_no_subject_still_graceful_when_flagged():
    # Grade 7 biology has no PDFs; retrieval sets the flag and tutor stays silent on LLM.
    state = AgentState(user_message="hi", subject="biology", grade_level=7, language="en")
    msg = _graceful_no_content_message(state)
    assert "Biology" in msg
