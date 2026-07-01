import json

import structlog

from src.config import settings
from src.llm.router import ModelRouter
from src.observability.evaluation.dimensions import EvalDimension

logger = structlog.get_logger()


class LLMJudge:
    def __init__(self, router: ModelRouter | None = None):
        self._router = router or ModelRouter(preferred_model=settings.eval_judge_model)

    async def score(
        self, dimension: EvalDimension, question: str, response: str, context: str = ""
    ) -> dict:
        user_prompt = (
            f"Question: {question}\n\n"
            f"Response: {response}\n\n"
            f"Context: {context}" if context else ""
        )
        messages = [
            {"role": "system", "content": dimension.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            result = await self._router.route(
                messages=messages,
                request_type="eval",
                temperature=0.0,
                max_tokens=300,
            )
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = json.loads(content)
            score = float(parsed.get("score", 0.0))
            explanation = parsed.get("explanation", "")
            return {"score": max(0.0, min(1.0, score)), "explanation": explanation}
        except (json.JSONDecodeError, KeyError, Exception) as e:
            logger.error("eval_score_failed", dimension=dimension.name, error=str(e))
            return {"score": 0.0, "explanation": f"Evaluation failed: {e}"}
