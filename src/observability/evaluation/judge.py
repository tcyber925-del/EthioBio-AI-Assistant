import json
import re

import structlog

from src.config import settings
from src.llm.router import ModelRouter
from src.observability.evaluation.dimensions import EvalDimension

logger = structlog.get_logger()

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(content: str) -> str:
    """Pull the JSON object out of a judge response.

    Handles code-fenced output, prose-wrapped objects, and trailing
    commentary — models frequently answer with more than bare JSON.
    """
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    try:
        json.loads(content)
        return content
    except json.JSONDecodeError:
        match = _JSON_OBJECT_RE.search(content)
        if match:
            return match.group(0)
        raise


class LLMJudge:
    def __init__(self, router: ModelRouter | None = None):
        self._router = router or ModelRouter(preferred_model=settings.eval_judge_model)

    async def score(
        self, dimension: EvalDimension, question: str, response: str, context: str = ""
    ) -> dict:
        user_prompt = (
            f"Question: {question}\n\nResponse: {response}\n\nContext: {context}" if context else ""
        )
        messages = [
            {"role": "system", "content": dimension.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        raw_content = ""
        try:
            result = await self._router.route(
                messages=messages,
                request_type="eval",
                temperature=0.0,
                max_tokens=300,
            )
            raw_content = str(result.get("content", ""))
            parsed = json.loads(_extract_json(raw_content))
            score = float(parsed.get("score", 0.0))
            explanation = parsed.get("explanation", "")
            return {"score": max(0.0, min(1.0, score)), "explanation": explanation}
        except Exception as e:
            logger.error(
                "eval_score_failed",
                dimension=dimension.name,
                error=str(e),
                raw_content=raw_content[:200],
            )
            return {"score": 0.0, "explanation": f"Evaluation failed: {e}"}
