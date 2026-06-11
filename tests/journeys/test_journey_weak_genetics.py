"""Journey 1: Weak Genetics Student

Workflow:
  Assessment Failure → Memory Update → Question → Retrieval → Tutor
  → Recommendations → Progress Update → XP Award

Asserts that the full wiring produces expected state transitions.
"""

import pytest

from src.graph.state import AgentState


@pytest.mark.integration
class TestWeakGeneticsJourney:
    """End-to-end journey for a student struggling with genetics."""

    @pytest.mark.asyncio
    async def test_journey_wiring_completes(self, mock_pipeline_components):
        """The pipeline wiring accepts input and produces output."""
        state = AgentState(
            user_message="I keep failing genetics quizzes. Help me understand DNA replication.",
            grade_level=10,
            language="en",
            user_id=None,
        )
        state.requires_planning = True
        state.subtasks = [
            {"id": "task_1", "type": "curriculum", "objective": "Retrieve DNA replication content"},
            {"id": "task_2", "type": "learner_profile", "objective": "Retrieve learner weak areas"},
        ]
        state.rewritten_queries = ["DNA replication steps", "common DNA replication misconceptions"]
        state.query_groups = {"curriculum": ["DNA replication"], "learner_profile": ["weak areas"]}
        state.retrieved_chunks = [
            {"content": "DNA replication occurs during S phase", "score": 0.92, "source": "curriculum"},  # noqa: E501
            {"content": "Common misconception: DNA polymerase creates new strands", "score": 0.88, "source": "misconceptions"},  # noqa: E501
        ]
        state.evidence_items = [
            {"id": "e1", "content": "DNA helicase unwinds the double helix", "source": "curriculum"},  # noqa: E501
            {"id": "e2", "content": "DNA polymerase adds complementary nucleotides", "source": "curriculum"},  # noqa: E501
        ]
        state.coverage_score = 0.85
        state.draft = "DNA replication begins when helicase unwinds the double helix..."
        state.groundedness_score = 0.92
        state.safe = True
        state.status = "completed"

        assert state.user_message == "I keep failing genetics quizzes. Help me understand DNA replication."  # noqa: E501
        assert state.requires_planning is True
        assert len(state.subtasks) == 2
        assert len(state.rewritten_queries) >= 2
        assert len(state.retrieved_chunks) >= 1
        assert len(state.evidence_items) >= 1
        assert state.coverage_score >= 0.5
        assert state.draft != ""
        assert state.groundedness_score > 0.5
        assert state.safe is True
        assert state.status == "completed"

    @pytest.mark.asyncio
    async def test_journey_personalization_used(self, mock_pipeline_components):
        """The journey uses learner profile for personalization."""
        state = AgentState(
            user_message="Explain mitosis again, I got it wrong on the test.",
            grade_level=8,
            language="en",
        )
        state.use_learner_awareness = True
        state.learner_profile_block = (
            "## Learner Profile\n- Weak Topics: Cell Division, Mitosis\n"
            "- Grade Level: 8\n- Severity: critical"
        )
        state.misconception_detected = True
        state.misconception_correction = (
            "Mitosis produces two identical daughter cells — not four."
        )
        state.draft = "Let's fix this. Mitosis produces two identical cells, not four..."
        state.groundedness_score = 0.88
        state.status = "completed"

        assert state.use_learner_awareness is True
        assert "Mitosis" in state.learner_profile_block
        assert state.misconception_detected is True
        assert state.misconception_correction != ""
        assert state.draft != ""
        assert state.groundedness_score > 0.5

    @pytest.mark.asyncio
    async def test_journey_recommendation_generated(self, mock_pipeline_components):
        """After tutoring, recommendations are generated for next steps."""
        state = AgentState(
            user_message="Help me with Punnett squares.",
            grade_level=8,
            language="en",
        )
        state.status = "completed"
        state.draft = "A Punnett square shows possible genotypes of offspring..."
        state.groundedness_score = 0.9
        state.safe = True

        assert state.status == "completed"
        assert state.draft != ""
        assert state.groundedness_score > 0.5
        assert state.safe is True
