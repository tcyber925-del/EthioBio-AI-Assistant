import json
from typing import Any

import structlog

from src.llm.router import ModelRouter

logger = structlog.get_logger()

SEMANTIC_ANALYSIS_PROMPT = (
    "You are an educational misconception analyst. "
    "Analyze a student's wrong answer and determine if it stems "
    "from a specific conceptual misconception rather than a simple error.\n\n"
    "Topic: {topic}\n"
    "Question: {question_text}\n"
    "Correct answer: {correct_answer}\n"
    "Student's answer: {wrong_answer}\n\n"
    "Analyze the student's answer and respond in JSON format:\n"
    "{{\n"
    '  "has_misconception": true/false,\n'
    '  "misconception": "brief name of the misconception if any",\n'
    '  "misconception_type": "knowledge_gap" | "misunderstanding"'
    ' | "misconception" | "persistent_misconception" | null,\n'
    '  "explanation": "why this answer reveals this misconception",\n'
    '  "confidence": 0.0-1.0,\n'
    '  "related_patterns": ["common phrases that might match this misconception"]\n'
    "}}\n\n"
    "Rules:\n"
    '- "has_misconception" must be true only if there is clear evidence\n'
    "  of a specific conceptual misunderstanding\n"
    "- A simple wrong calculation or memory recall failure is NOT a misconception\n"
    "- Severity levels: knowledge_gap (missing info) < misunderstanding (confused)\n"
    "  < misconception (deeply held wrong belief)\n"
    "  < persistent_misconception (resists correction)\n"
    "- Return valid JSON only, no markdown formatting, no code fences"
)


class SemanticDetector:
    def __init__(self, router: ModelRouter | None = None):
        self._router = router or ModelRouter()

    async def analyze(
        self,
        topic: str,
        wrong_answer: str,
        correct_answer: str,
        question_text: str = "",
    ) -> dict[str, Any]:
        prompt = SEMANTIC_ANALYSIS_PROMPT.format(
            topic=topic,
            question_text=question_text or "(not provided)",
            correct_answer=correct_answer,
            wrong_answer=wrong_answer,
        )

        try:
            result = await self._router.route(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an educational misconception analyst. Output only valid JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                request_type="chat",
                temperature=0.1,
                max_tokens=512,
            )
            return self._parse_response(result["content"])
        except Exception as e:
            logger.warning("semantic_detection_failed", error=str(e))
            return {"has_misconception": False, "confidence": 0.0}

    def _parse_response(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if "```" in cleaned:
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            try:
                start = cleaned.index("{")
                end = cleaned.rindex("}") + 1
                parsed = json.loads(cleaned[start:end])
            except (ValueError, json.JSONDecodeError):
                logger.warning("semantic_detection_parse_failed", raw=content[:200])
                return {"has_misconception": False, "confidence": 0.0}

        return {
            "has_misconception": bool(parsed.get("has_misconception", False)),
            "misconception": parsed.get("misconception") or None,
            "misconception_type": parsed.get("misconception_type") or None,
            "explanation": parsed.get("explanation") or "",
            "confidence": min(float(parsed.get("confidence", 0.0)), 1.0),
            "related_patterns": parsed.get("related_patterns") or [],
        }

    async def close(self):
        await self._router.close()
