import json
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()

DIAGRAM_SYSTEM_PROMPT = """You are EthioBio Diagram Generator, creating
visual biology diagrams for Ethiopian students (Grades 7-12).

Generate an SVG diagram of a biology structure based on the user's request. The diagram must:
- Be valid SVG markup (no HTML wrapping, no markdown fences in the svg value)
- Use clear colors and label positions
- Fit within a 800x600 viewBox
- Include visual elements (shapes, lines, curves) that represent the biology structure
- Have labeled parts with leader lines connecting labels to structures
- Be age-appropriate for the specified difficulty level

Output a JSON object following this schema:
{
  "title": "Diagram title",
  "labels": [
    {"id": "label_1", "text": "Part Name", "x": 650, "y": 50},
    {"id": "label_2", "text": "Another Part", "x": 700, "y": 150}
  ],
  "diagram_svg": "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>...</svg>"
}

Rules for labels:
- Each label's x,y should be the position of the label TEXT on the SVG canvas
- Labels should be placed to the right of the diagram content area (x > 500 typically)
- id must be unique and use snake_case
- The label text in the SVG should match the label text in the labels array

Rules for SVG:
- The SVG must be self-contained (no external CSS or fonts)
- Use simple colors, shapes, and text
- For beginner: simpler diagrams with 3-5 labels
- For intermediate: moderate complexity with 6-10 labels
- For advanced: detailed diagrams with 10-15 labels
"""


class DiagramAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="diagram")

    async def generate(
        self,
        prompt: str,
        topic: str,
        difficulty: str = "beginner",
        session: Optional[AsyncSession] = None,
    ) -> dict:
        user_message = f"""Create a biology diagram for topic: {topic}.
User request: {prompt}
Difficulty level: {difficulty}

For {difficulty} difficulty:
- beginner: 3-5 labeled structures, simple shapes, large text
- intermediate: 6-10 labeled structures, moderate detail
- advanced: 10-15 labeled structures, detailed anatomical accuracy

Respond with valid JSON only."""

        result = await self._call_llm(
            system_prompt=DIAGRAM_SYSTEM_PROMPT,
            user_message=user_message,
            session=session,
            temperature=0.7,
            max_tokens=4096,
            request_type="diagram_generation",
        )

        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            return {
                "title": parsed.get("title", f"{topic} - {prompt[:50]}"),
                "diagram_svg": parsed.get("diagram_svg", ""),
                "labels": parsed.get("labels", []),
                "topic": topic,
                "difficulty": difficulty,
                "model_used": result.get("model", ""),
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("diagram_parse_error", error=str(e), content=result["content"][:300])
            return {
                "title": f"{topic} - {prompt[:50]}",
                "diagram_svg": result["content"],
                "labels": [],
                "topic": topic,
                "difficulty": difficulty,
                "model_used": result.get("model", ""),
            }


def validate_labels(
    correct_labels: list[dict],
    submitted_labels: list[dict],
) -> list[dict]:
    correct_map = {l["id"]: l for l in correct_labels}
    results = []
    for sub in submitted_labels:
        lid = sub["id"]
        if lid in correct_map:
            correct = correct_map[lid]
            is_correct = sub["text"].strip().lower() == correct["text"].strip().lower()
            explanation = "" if is_correct else f"The correct term is '{correct['text']}'."
            results.append({
                "label_id": lid,
                "correct_text": correct["text"],
                "submitted_text": sub["text"],
                "is_correct": is_correct,
                "explanation": explanation,
            })
        else:
            results.append({
                "label_id": lid,
                "correct_text": "",
                "submitted_text": sub["text"],
                "is_correct": False,
                "explanation": "Unknown label position.",
            })
    return results
