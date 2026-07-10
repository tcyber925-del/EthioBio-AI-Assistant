"""Journey 2: Misconception Correction

Workflow:
  Assessment → Incorrect Answer → Misconception Stored → Question
  → Retrieval → Correction

Asserts that stored misconceptions are retrieved and addressed in the tutor response.
"""

import pytest

from src.graph.state import AgentState


@pytest.mark.integration
class TestMisconceptionCorrectionJourney:
    """End-to-end journey for correcting a student's misconception."""

    def _build_state_with_misconception(self) -> AgentState:
        state = AgentState(
            user_message="I think plants get their food from the soil, not from photosynthesis.",
            grade_level=8,
            language="en",
        )
        state.misconception_detected = True
        state.misconception_correction = (
            "Plants produce their own food through photosynthesis using sunlight. "
            "Soil provides water and minerals, not food."
        )
        state.retrieved_chunks = [
            {
                "content": "Photosynthesis converts light energy into chemical energy (glucose)",
                "score": 0.95,
                "source": "curriculum",
            },
            {
                "content": "Common misconception: plants eat soil. Actually, they produce their own food.",  # noqa: E501
                "score": 0.91,
                "source": "misconceptions",
            },
        ]
        state.draft = (
            "That's a common misconception! Plants don't eat soil — "
            "they make their own food through photosynthesis..."
        )
        state.groundedness_score = 0.94
        state.status = "completed"
        return state

    @pytest.mark.asyncio
    async def test_misconception_detected_and_addressed(self):
        """Misconception is flagged and correction is provided."""
        state = self._build_state_with_misconception()

        assert state.misconception_detected is True
        assert "photosynthesis" in state.misconception_correction.lower()
        assert state.groundedness_score > 0.8

    @pytest.mark.asyncio
    async def test_misconception_evidence_retrieved(self):
        """Misconception-related chunks are retrieved alongside curriculum."""
        state = self._build_state_with_misconception()

        retrieved_sources = [c["source"] for c in state.retrieved_chunks]
        assert "misconceptions" in retrieved_sources
        assert "curriculum" in retrieved_sources

    @pytest.mark.asyncio
    async def test_misconception_response_grounded(self):
        """The correction response cites evidence and is safe."""
        state = self._build_state_with_misconception()

        assert state.draft != ""
        assert state.groundedness_score > 0.8
        assert state.safe is True
        assert state.status == "completed"
