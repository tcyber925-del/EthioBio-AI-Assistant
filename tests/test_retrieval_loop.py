"""Tests for the RetrievalLoopController."""

from dataclasses import dataclass, field

import pytest

from src.core.loops.controller import RetrievalLoopController
from src.core.loops.feedback_processor import FeedbackProcessor
from src.core.loops.telemetry import record_loop_decision
from src.graph.nodes.sufficient_context import (
    SufficientContextNode,
    route_after_sufficiency,
)
from src.graph.state import AgentState


@dataclass
class FakeState:
    retrieval_iterations: int = 0
    max_iterations: int = 3
    coverage_score: float = 0.0
    coverage_history: list[float] = field(default_factory=list)
    previous_evidence_count: int = 0
    evidence_ids: list[str] = field(default_factory=list)


def test_controller_continue_when_below_all_thresholds():
    state = FakeState(
        retrieval_iterations=1,
        max_iterations=3,
        coverage_score=0.5,
        coverage_history=[0.3],
        previous_evidence_count=1,
        evidence_ids=["e1", "e2"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is True
    assert decision.reason == "CONTINUE"


def test_controller_stops_at_max_iterations():
    state = FakeState(
        retrieval_iterations=3,
        max_iterations=3,
        coverage_score=0.7,
        coverage_history=[0.5],
        previous_evidence_count=2,
        evidence_ids=["e1", "e2", "e3"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is False
    assert decision.reason == "MAX_ITERATIONS"


def test_controller_exceeds_max_iterations():
    state = FakeState(
        retrieval_iterations=4,
        max_iterations=3,
        coverage_score=0.7,
        coverage_history=[0.5],
        previous_evidence_count=2,
        evidence_ids=["e1", "e2", "e3"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is False
    assert decision.reason == "MAX_ITERATIONS"


def test_controller_stops_on_no_progress():
    """2 consecutive low gains → stop.
    Gains here: 0.31-0.5=-0.19, 0.32-0.31=0.01 → both < 0.02."""
    state = FakeState(
        retrieval_iterations=2,
        max_iterations=5,
        coverage_score=0.32,
        coverage_history=[0.5, 0.31],
        previous_evidence_count=3,
        evidence_ids=["e1", "e2", "e3"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is False
    assert decision.reason == "NO_PROGRESS"


def test_controller_continues_after_single_low_gain():
    """Only stop after 2 consecutive low-gain iterations.
    Gains here: 0.05-0.5=-0.45 (low), 0.50-0.05=0.45 (high) → only 1 low → continue."""
    state = FakeState(
        retrieval_iterations=2,
        max_iterations=5,
        coverage_score=0.50,
        coverage_history=[0.5, 0.05],
        previous_evidence_count=2,
        evidence_ids=["e1", "e2", "e3"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is True


def test_controller_stops_on_no_new_evidence():
    state = FakeState(
        retrieval_iterations=2,
        max_iterations=5,
        coverage_score=0.5,
        coverage_history=[0.3, 0.5],
        previous_evidence_count=2,
        evidence_ids=["e1", "e2"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is False
    assert decision.reason == "NO_NEW_EVIDENCE"


def test_controller_respects_state_max_iterations():
    state = FakeState(
        retrieval_iterations=2,
        max_iterations=2,
        coverage_score=0.5,
        coverage_history=[0.3],
        previous_evidence_count=1,
        evidence_ids=["e1", "e2"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is False
    assert decision.reason == "MAX_ITERATIONS"


def test_controller_no_history_is_continue():
    """First iteration with empty history should not trigger no-progress."""
    state = FakeState(
        retrieval_iterations=1,
        max_iterations=5,
        coverage_score=0.5,
        coverage_history=[],
        previous_evidence_count=0,
        evidence_ids=["e1"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is True


def test_controller_no_new_evidence_first_iteration():
    """First iteration with 0 evidence should continue
    (previous_evidence_count starts at 0, but iterations=1 means check is skipped
    because the 'no new evidence' check only runs when iterations > 0 and
    evidence count <= previous count with both being 0, it would trigger.
    Actually iterations=0 would skip the check entirely, but with iterations=1
    and both 0, it would trigger. So set iterations=0 to test first pass.)"""
    state = FakeState(
        retrieval_iterations=0,
        max_iterations=5,
        coverage_score=0.0,
        coverage_history=[0.0],
        previous_evidence_count=0,
        evidence_ids=[],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.should_continue is True


def test_controller_first_iteration_new_evidence_continues():
    """Second iteration with new evidence should not trigger no-new-evidence."""
    state = FakeState(
        retrieval_iterations=1,
        max_iterations=5,
        coverage_score=0.5,
        coverage_history=[0.0, 0.5],
        previous_evidence_count=0,
        evidence_ids=["e1"],
    )
    controller = RetrievalLoopController()
    decision = controller.decide(state)
    assert decision.reason != "NO_NEW_EVIDENCE"


# ─── FeedbackProcessor Tests ──────────────────────────────────────────


def test_feedback_empty_gaps():
    processor = FeedbackProcessor()
    result = processor.process(missing_information=[], coverage_score=0.95)
    assert result == []


def test_feedback_single_gap():
    processor = FeedbackProcessor()
    result = processor.process(
        missing_information=["Explain DNA replication steps"],
        coverage_score=0.6,
    )
    assert len(result) == 1
    assert "DNA replication" in result[0]


def test_feedback_multiple_gaps():
    processor = FeedbackProcessor()
    result = processor.process(
        missing_information=[
            "Describe mitosis phases",
            "Define cell wall function",
            "List organelles",
        ],
        coverage_score=0.3,
    )
    assert len(result) == 3


def test_feedback_empty_gaps_low_coverage():
    processor = FeedbackProcessor()
    result = processor.process(missing_information=[], coverage_score=0.2)
    assert len(result) == 1
    assert "Broader" in result[0] or "broaden" in result[0].lower()


# ─── Telemetry Tests ──────────────────────────────────────────────────


def test_record_loop_decision_returns_metrics():
    state = FakeState(
        retrieval_iterations=2,
        max_iterations=3,
        coverage_score=0.7,
        coverage_history=[0.3, 0.7],
        previous_evidence_count=1,
        evidence_ids=["e1", "e2"],
    )
    state.sufficiency_score = 0.8
    state.termination_reason = "MAX_ITERATIONS"

    metrics = record_loop_decision(state)
    assert metrics["iteration"] == 2
    assert metrics["coverage"] == 0.7
    assert metrics["sufficiency"] == 0.8
    assert metrics["termination"] == "MAX_ITERATIONS"
    assert metrics["evidence_count"] == 2
    assert metrics["coverage_history"] == [0.3, 0.7]


# ─── SufficientContextNode Integration Tests ──────────────────────────


@pytest.mark.asyncio
async def test_sufficient_context_node_delegates_to_controller():
    """Verify the node sets termination_reason and requires_iteration."""
    node = SufficientContextNode()
    state = AgentState(user_message="test")
    state.evidence_ids = ["e1"]
    state.coverage_score = 0.5
    state.missing_information = ["gap about dna"]

    result = await node(state)

    assert result.termination_reason in (
        "CONTINUE",
        "MAX_ITERATIONS",
        "NO_PROGRESS",
        "NO_NEW_EVIDENCE",
    )
    assert result.retrieval_iterations == 1
    assert result.retrieval_feedback is not None


@pytest.mark.asyncio
async def test_sufficient_context_node_appends_coverage_history():
    """Verify coverage is appended to history before controller."""
    node = SufficientContextNode()
    state = AgentState(user_message="test")
    state.evidence_ids = ["e1"]
    state.coverage_score = 0.5

    result = await node(state)

    assert len(result.coverage_history) == 1
    assert result.coverage_history[0] == 0.5


@pytest.mark.asyncio
async def test_sufficient_context_node_increments_iterations():
    """Verify iteration counter increments."""
    node = SufficientContextNode()
    state = AgentState(user_message="test")
    state.evidence_ids = ["e1"]
    state.coverage_score = 0.5
    state.retrieval_iterations = 0

    result = await node(state)

    assert result.retrieval_iterations == 1


def test_route_after_sufficiency_returns_synthesis_when_stopped():
    state = AgentState(user_message="test")
    state.sufficiency_score = 0.8
    state.coverage_score = 0.8
    state.requires_iteration = False

    route = route_after_sufficiency(state)

    assert route == "synthesis"


def test_route_after_sufficiency_returns_rewrite_for_minor_gap():
    state = AgentState(user_message="test")
    state.sufficiency_score = 0.3
    state.coverage_score = 0.3
    state.requires_iteration = True
    state.missing_information = ["Explain mitosis"]

    route = route_after_sufficiency(state)

    assert route == "rewrite"


def test_route_after_sufficiency_returns_replan_for_major_gap():
    state = AgentState(user_message="test")
    state.sufficiency_score = 0.1
    state.coverage_score = 0.1
    state.requires_iteration = True
    state.missing_information = ["gap 1", "gap 2", "gap 3"]

    route = route_after_sufficiency(state)

    assert route == "replan"
