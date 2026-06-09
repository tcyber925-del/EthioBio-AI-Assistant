"""Synthesis Node — pre-digests evidence for TutorNode.

Phase 0: LLM-based synthesis using TutorSynthesisAgent.
Phase 1+: Support for structured JSON output and multi-source merging.
"""

import logging

from src.agents.synthesis import TutorSynthesisAgent
from src.graph.state import AgentState
from src.llm.router import ModelRouter

logger = logging.getLogger(__name__)


class SynthesisNode:
    """Pre-digests evidence into structured synthesis before tutor generation.

    Transforms raw retrieved chunks into a condensed evidence summary
    that the TutorNode injects into its system prompt, reducing token
    burden and improving answer groundedness.
    """

    def __init__(self, router: ModelRouter):
        self.agent = TutorSynthesisAgent(router)

    async def __call__(self, state: AgentState) -> AgentState:
        """Synthesize evidence and update state.

        Args:
            state: AgentState with retrieved_chunks and user_message.

        Returns:
            Updated AgentState with evidence_synthesis populated.
        """
        chunks = state.retrieved_chunks or []
        question = state.user_message

        synthesis = await self.agent.synthesize(
            question=question,
            evidence_chunks=chunks,
            grade_level=state.grade_level,
        )

        state.evidence_synthesis = synthesis

        logger.info(
            "evidence_synthesized",
            chunk_count=len(chunks),
            synthesis_length=len(synthesis),
        )

        return state
