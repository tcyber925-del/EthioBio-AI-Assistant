# ruff: noqa: E501

import logging

from src.agents.tutor.grounding import extract_citations
from src.agents.tutor.models import TutorResponse
from src.agents.tutor.personalization import build_personalization_block
from src.agents.tutor.prompts import get_system_prompt
from src.agents.tutor.strategy import select_teaching_strategy
from src.llm.router import ModelRouter

logger = logging.getLogger(__name__)

HINT_PROMPTS = {
    1: "\n\nThe student has requested a HINT (Level 1). Give a BROAD, general hint that points them in the right direction without giving away the answer.",
    2: "\n\nThe student has requested a HINT (Level 2). Give a MORE SPECIFIC hint that narrows down the possibilities significantly.",
    3: "\n\nThe student has requested a HINT (Level 3). Give a VERY SPECIFIC hint that leads almost directly to the answer.",
}

REVEAL_PROMPT = "\n\nThe student has requested the final answer. Provide the complete correct answer with a full explanation. Include verbatim quotes from the evidence. Cite curriculum sources when available."


class TutorSynthesisAgent:
    def __init__(self, router: ModelRouter):
        self.router = router

    async def generate(
        self,
        user_message: str,
        evidence_items: list[dict],
        evidence_synthesis: str,
        grade_level: int | None,
        language: str,
        socratic_mode: bool,
        hint_level: int,
        reveal_answer: bool,
        learner_profile_block: str,
        messages: list[dict],
        intent: str,
        misconception_detected: bool,
        student_misconceptions: list[str],
        ungrounded_claims: list[str] | None = None,
    ) -> TutorResponse:
        strategy = select_teaching_strategy(
            user_message=user_message,
            socratic_mode=socratic_mode,
            hint_level=hint_level,
            intent=intent,
            misconception_detected=misconception_detected,
            learner_profile_block=learner_profile_block,
        )

        system = get_system_prompt(strategy)

        personalization = build_personalization_block(
            learner_profile_block=learner_profile_block,
            grade_level=grade_level,
            language=language,
            misconceptions=student_misconceptions,
        )
        if personalization:
            system += "\n\n" + personalization

        if evidence_synthesis:
            system += f"\n\n## Evidence Synthesis\n{evidence_synthesis}\n\nUse the above evidence to ground your answer. Include verbatim quotes from the evidence. Cite evidence IDs using [id:<evidence_id>]."
        elif evidence_items:
            items_text = "\n".join(
                f"- [{e.get('id', '?')}] {e.get('content', '')[:200]}"
                for e in evidence_items
            )
            system += f"\n\n## Evidence Items\n{items_text}\n\nUse the above evidence to ground your answer. Include verbatim quotes from the evidence. Cite evidence IDs using [id:<evidence_id>]."

        if reveal_answer:
            system += REVEAL_PROMPT
        elif hint_level > 0 and hint_level in HINT_PROMPTS:
            system += HINT_PROMPTS[hint_level]

        if ungrounded_claims:
            system += "\n\n## Revision Feedback\n"
            system += "Your previous response contained claims that could not be verified against the provided evidence. "
            system += "Please revise the response to fix the following ungrounded claims:\n"
            for i, claim in enumerate(ungrounded_claims, 1):
                system += f"\n{i}. \"{claim}\""
            system += "\n\nEnsure EVERY claim in your response is directly supported by the provided evidence. "
            system += "Remove or rephrase any claim you cannot support with a verbatim quote from the evidence."

        grade_context = f" (Grade {grade_level})" if grade_level else ""
        if language == "am":
            lang_context = "Respond entirely in Amharic (አማርኛ). Use Amharic biology terminology."
        elif language == "both":
            lang_context = "Answer in English with Amharic explanation. Provide key terms in both languages."
        else:
            lang_context = "Answer in English."

        user_prompt = f"[Grade{grade_context}] {lang_context}\n\nStudent question: {user_message}"
        llm_messages = [
            {"role": "system", "content": system},
            *messages,
            {"role": "user", "content": user_prompt},
        ]

        result = await self.router.route(
            llm_messages, request_type="tutor", temperature=0.7, max_tokens=2048,
        )

        content = result["content"]
        cleaned_content, citation_map = extract_citations(content, evidence_items)

        if evidence_items and not citation_map:
            logger.warning("tutor_response_missing_citations")
            disclaimer = "\n\n*Note: Some claims could not be directly cited to the available evidence.*"
            cleaned_content += disclaimer

        return TutorResponse(
            content=cleaned_content,
            confidence=result.get("confidence", 0.0),
            teaching_strategy=strategy,
            citation_map=citation_map,
            misconceptions_addressed=student_misconceptions if misconception_detected else [],
            recommendations=[],
        )
