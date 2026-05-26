import json
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.retrieval.adapter import RetrievalFilter, VectorStoreAdapter

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

CURRICULUM_CONTEXT_BLOCK = """

Curriculum reference materials (textbook diagrams with captions):
{context}

Use the exact biological terminology from these references when labeling diagram structures.
"""


class DiagramAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter, adapter: Optional[VectorStoreAdapter] = None):
        super().__init__(llm_router, name="diagram")
        self._adapter = adapter

    @property
    def adapter(self) -> VectorStoreAdapter:
        if self._adapter is None:
            self._adapter = VectorStoreAdapter()
        return self._adapter

    async def generate(
        self,
        prompt: str,
        topic: str,
        difficulty: str = "beginner",
        session: Optional[AsyncSession] = None,
        preferred_model: str | None = None,
        grade: int = 10,
    ) -> dict:
        textbook_references = []
        system_prompt = DIAGRAM_SYSTEM_PROMPT
        try:
            filter_obj = RetrievalFilter(grade_level=grade, source_type="textbook_diagram")
            results = await self.adapter.search(query=topic, n_results=3, filter_obj=filter_obj)
            if results:
                context = self.adapter.format_context(results)
                system_prompt = (
                    DIAGRAM_SYSTEM_PROMPT + CURRICULUM_CONTEXT_BLOCK.format(context=context)
                )
                for r in results:
                    textbook_references.append({
                        "grade": r.metadata.get("grade_level", grade),
                        "unit": r.metadata.get("unit"),
                        "figure_number": r.metadata.get("figure_number"),
                        "caption": r.content,
                    })
        except Exception:
            logger.warning("rag_retrieval_failed", exc_info=True)

        user_message = f"""Create a biology diagram for topic: {topic}.
User request: {prompt}
Difficulty level: {difficulty}
Grade level: {grade}

For {difficulty} difficulty:
- beginner: 3-5 labeled structures, simple shapes, large text
- intermediate: 6-10 labeled structures, moderate detail
- advanced: 10-15 labeled structures, detailed anatomical accuracy

Respond with valid JSON only."""

        result = await self._call_llm(
            system_prompt=system_prompt,
            user_message=user_message,
            session=session,
            temperature=0.7,
            max_tokens=4096,
            request_type="diagram_generation",
            preferred_model=preferred_model,
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
                "textbook_references": textbook_references,
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
                "textbook_references": textbook_references,
            }


def validate_labels(
    correct_labels: list[dict],
    submitted_labels: list[dict],
) -> list[dict]:
    correct_map = {item["id"]: item for item in correct_labels}
    results = []
    for sub in submitted_labels:
        lid = sub["id"]
        if lid in correct_map:
            correct = correct_map[lid]
            is_correct = sub["text"].strip().lower() == correct["text"].strip().lower()
            explanation = (
                ""
                if is_correct
                else (
                    f"Not quite. The correct label is '{correct['text']}'. "
                    "Review the diagram structure and try to associate the "
                    "numbered position with its biological name."
                )
            )
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
