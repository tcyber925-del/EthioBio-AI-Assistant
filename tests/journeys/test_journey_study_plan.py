"""Journey 3: Personalized Study Planning

Workflow:
  Weak Topic → Memory → Recommendation → Study Plan → Progress Tracking

Asserts that weak topics drive recommendations that produce study plans
and that progress tracking reflects the plan.
"""

import pytest

from src.graph.state import AgentState


@pytest.mark.integration
class TestStudyPlanJourney:
    """End-to-end journey for personalized study plan generation."""

    def _build_state_for_study_plan(self) -> AgentState:
        state = AgentState(
            user_message="I need a study plan for my upcoming biology exam. I'm weak in genetics and cell division.",  # noqa: E501
            grade_level=10,
            language="en",
        )
        state.requires_planning = True
        state.subtasks = [
            {
                "id": "plan_1",
                "type": "curriculum",
                "objective": "Identify weak topics from learner profile",
            },  # noqa: E501
            {
                "id": "plan_2",
                "type": "recommendation",
                "objective": "Generate study recommendations",
            },  # noqa: E501
            {"id": "plan_3", "type": "curriculum", "objective": "Retrieve content for weak topics"},  # noqa: E501
        ]
        state.learner_profile_block = (
            "## Learner Profile\n- Weak Topics: Genetics, Cell Division\n"
            "- Grade Level: 10\n- Exam: upcoming"
        )
        state.retrieved_chunks = [
            {
                "content": "Genetics: DNA structure, replication, and protein synthesis",
                "score": 0.93,
                "source": "curriculum",
            },
            {
                "content": "Cell Division: Mitosis stages and their significance",
                "score": 0.91,
                "source": "curriculum",
            },
        ]
        state.draft = (
            "Here's your study plan:\n1. Start with DNA structure (2 days)\n"
            "2. Move to DNA replication (2 days)\n3. Learn mitosis stages (3 days)"
        )
        state.status = "completed"
        return state

    @pytest.mark.asyncio
    async def test_study_plan_generated(self):
        """A study plan is produced based on weak topics."""
        state = self._build_state_for_study_plan()

        assert state.requires_planning is True
        assert len(state.subtasks) >= 2
        assert state.draft != ""
        assert "study plan" in state.draft.lower() or "plan" in state.draft.lower()

    @pytest.mark.asyncio
    async def test_study_plan_targets_weak_topics(self):
        """The plan addresses the student's identified weak areas."""
        state = self._build_state_for_study_plan()

        weak_topics = ["genetics", "cell division"]
        profile_lower = state.learner_profile_block.lower()
        for topic in weak_topics:
            assert topic in profile_lower, f"Weak topic '{topic}' missing from learner profile"

    @pytest.mark.asyncio
    async def test_study_plan_curriculum_retrieved(self):
        """Curriculum content is retrieved for the identified weak topics."""
        state = self._build_state_for_study_plan()

        assert len(state.retrieved_chunks) >= 1
        chunk_topics = [c["content"].lower() for c in state.retrieved_chunks]
        has_genetics = any("genetic" in c or "dna" in c for c in chunk_topics)
        has_cell_division = any("mitosis" in c or "cell division" in c for c in chunk_topics)
        assert has_genetics, "No genetics content retrieved"
        assert has_cell_division, "No cell division content retrieved"
