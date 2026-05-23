from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()

SAFETY_SYSTEM_PROMPT = """You are EthioBio Safety Agent, responsible for reviewing content for:
1. Factual accuracy (especially biology curriculum alignment)
2. Grade-appropriateness (content suitable for Grade 7-12 students)
3. Safety (no harmful, dangerous, or inappropriate content)
4. Curriculum match (does it follow Ethiopian biology curriculum)
5. Clarity (is the explanation clear and understandable)
6. Language quality (proper English/Amharic)

Analyze the content and respond with a JSON object:
{"safe": true/false, "issues": ["issue1", "issue2"], "score": 0.0-1.0, "suggestions": ["suggestion"]}
"""


class SafetyAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="safety")

    async def review(
        self,
        content: str,
        grade_level: Optional[int] = None,
        session: Optional[AsyncSession] = None,
    ) -> dict:
        grade_context = f" (Grade {grade_level})" if grade_level else ""
        user_message = f"""Review the following biology content{grade_context} for safety, accuracy, and appropriateness.

Content to review:
{content}"""

        result = await self._call_llm(
            system_prompt=SAFETY_SYSTEM_PROMPT,
            user_message=user_message,
            session=session,
            temperature=0.1,
            max_tokens=1000,
            request_type="safety_check",
        )

        import json
        try:
            content_text = result["content"]
            if "```json" in content_text:
                content_text = content_text.split("```json")[1].split("```")[0].strip()
            elif "```" in content_text:
                content_text = content_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content_text)
            return {
                "safe": parsed.get("safe", True),
                "issues": parsed.get("issues", []),
                "score": parsed.get("score", 1.0),
                "suggestions": parsed.get("suggestions", []),
                "model_used": result.get("model", ""),
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("safety_parse_error", error=str(e))
            return {
                "safe": True,
                "issues": [],
                "score": 1.0,
                "suggestions": ["Unable to parse safety review"],
                "model_used": result.get("model", ""),
            }

    async def check_hallucination(
        self,
        response: str,
        context: str,
        session: Optional[AsyncSession] = None,
    ) -> dict:
        user_message = f"""Check if the following response is factually grounded in the provided curriculum context.

Context:
{context}

Response:
{response}

Is the response supported by the context? Identify any unsupported claims."""

        return await self.review(
            content=f"Response: {response}\n\nContext: {context}",
            session=session,
        )
