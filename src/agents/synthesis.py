"""Tutor Synthesis Agent — pre-digests evidence for the TutorNode.

Creates a structured synthesis of evidence: key claims with supporting
citations, unresolved gaps, and source quality indicators. Reduces token
burden on the tutor and produces more grounded responses.

PRD-008: Synthesis is not the same as generation.
"""

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

SYNTHESIS_SYSTEM_PROMPT = """You are the Evidence Synthesis Agent.

Your job: digest raw evidence chunks into a structured summary for the biology tutor.

Output structure:
1. KEY FACTS — List specific factual claims found in the evidence, grouped by topic
2. CITED SOURCES — For each fact, cite which source(s) support it
3. GAPS — Note any aspects of the question NOT covered by the evidence
4. QUALITY — Assess overall evidence quality (high/medium/low)

Rules:
- Be concise. The tutor will read this summary + the original question.
- Only include information present in the evidence. Do not add external knowledge.
- If evidence conflicts, flag the conflict clearly.
- Use bullet points, not paragraphs."""


class TutorSynthesisAgent(BaseAgent):
    """Pre-digests evidence into a structured synthesis for tutor generation.

    Takes raw evidence chunks and produces a condensed, structured summary
    that the TutorNode can inject into its system prompt.
    """

    def __init__(self, router: ModelRouter):
        super().__init__(router, name="tutor_synthesis")

    async def synthesize(
        self,
        question: str,
        evidence_chunks: list[dict],
        grade_level: int | None = None,
    ) -> str:
        """Synthesize evidence into a structured summary.

        Args:
            question: Original user question.
            evidence_chunks: List of evidence dicts with content, source, score.
            grade_level: Optional grade level for context.

        Returns:
            Structured synthesis text for the tutor's system prompt.
        """
        if not evidence_chunks:
            return "No evidence retrieved for this question."

        evidence_text = ""
        for i, chunk in enumerate(evidence_chunks):
            content = chunk.get("content", "")
            source = chunk.get("source", chunk.get("source_type", "unknown"))
            score = chunk.get("score", chunk.get("confidence", 0.0))
            evidence_text += f"\n[{i}] Source: {source} (confidence: {score:.2f})\n{content}\n"

        grade_context = f" (Grade {grade_level})" if grade_level else ""

        user_prompt = (
            f"Synthesize evidence for this question{grade_context}:\n\n"
            f"Question: {question}\n\n"
            f"Evidence:\n{evidence_text}"
        )

        result = await self._call_llm(
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            user_message=user_prompt,
            temperature=0.3,
            max_tokens=1024,
            request_type="synthesis",
        )

        return result.get("content", "")
