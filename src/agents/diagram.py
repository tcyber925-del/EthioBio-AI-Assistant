import asyncio
import json
import re
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.retrieval.adapter import RetrievalFilter, VectorStoreAdapter
from src.schemas.diagram import DiagramPanel
from src.schemas.streaming import TokenChunk

logger = structlog.get_logger()

PANEL_CONNECTIVES = re.compile(
    r"\b(and|vs|versus|compared with|comparison|external and internal|"
    r"difference between|similarities and differences)\b",
    re.IGNORECASE,
)

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

    def _push_status(self, queue: asyncio.Queue[TokenChunk | None] | None, message: str):
        if queue:
            queue.put_nowait(TokenChunk(delta=message, node="diagram", status=True))

    @property
    def adapter(self) -> VectorStoreAdapter:
        if self._adapter is None:
            self._adapter = VectorStoreAdapter()
        return self._adapter

    @staticmethod
    def detect_panel_count(prompt: str) -> int:
        """Heuristic: detect whether a prompt needs 1 or 2 panels.

        Returns 2 if the prompt contains comparison connectives
        (and, vs, versus, external and internal, comparison, etc.),
        otherwise 1.
        """
        if PANEL_CONNECTIVES.search(prompt):
            return 2
        return 1

    async def generate_panel(
        self,
        sub_prompt: str,
        panel_index: int,
        topic: str,
        difficulty: str,
        grade: int,
        session: Optional[AsyncSession] = None,
        preferred_model: str | None = None,
        token_queue: asyncio.Queue[TokenChunk | None] | None = None,
    ) -> DiagramPanel:
        """Generate a single panel diagram. Returns a DiagramPanel instance."""
        caption = sub_prompt[:80] if len(sub_prompt) > 80 else sub_prompt
        user_message = (
            f"Panel {panel_index + 1} for topic: {topic}.\n"
            f"Focus on: {sub_prompt}\n"
            f"Difficulty: {difficulty}\n"
            f"Grade level: {grade}\n\n"
            "Respond with valid JSON only."
        )

        if token_queue is not None:
            buf: list[str] = []
            async for token in self._call_llm_stream(
                system_prompt=DIAGRAM_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=0.7,
                max_tokens=4096,
                request_type="diagram_generation",
                preferred_model=preferred_model,
            ):
                buf.append(token)
                token_queue.put_nowait(TokenChunk(delta=token, node="diagram"))
            content = "".join(buf)
        else:
            result = await self._call_llm(
                system_prompt=DIAGRAM_SYSTEM_PROMPT,
                user_message=user_message,
                session=session,
                temperature=0.7,
                max_tokens=4096,
                request_type="diagram_generation",
                preferred_model=preferred_model,
            )
            content = result["content"]
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = json.loads(content)
        except (json.JSONDecodeError, KeyError):
            parsed = None

        if parsed:
            return DiagramPanel(
                id=f"panel_{panel_index}",
                caption=caption,
                svg=parsed.get("diagram_svg", ""),
                labels=parsed.get("labels", []),
            )
        return DiagramPanel(
            id=f"panel_{panel_index}",
            caption=caption,
            svg=content,
            labels=[],
        )

    async def _split_prompt(self, prompt: str) -> list[str]:
        """Split a comparison prompt into two sub-prompts.

        Tries common delimiters: ' vs ', 'versus', ' and ' (for comparisons),
        'external and internal'.
        """
        lower = prompt.lower()
        if "external and internal" in lower:
            parts = re.split(r"external and internal", prompt, flags=re.IGNORECASE)
            return [f"External {parts[0].strip()}", f"Internal {parts[0].strip()}"]
        for delim in [" vs ", " versus "]:
            if delim in lower:
                parts = prompt.split(delim)
                return [p.strip() for p in parts if p.strip()]
        # Fallback: first half / second half
        words = prompt.split()
        mid = len(words) // 2
        return [" ".join(words[:mid]), " ".join(words[mid:])]

    async def generate(
        self,
        prompt: str,
        topic: str,
        difficulty: str = "beginner",
        session: Optional[AsyncSession] = None,
        preferred_model: str | None = None,
        grade: int = 10,
        token_queue: asyncio.Queue[TokenChunk | None] | None = None,
    ) -> dict:
        textbook_references = []

        panel_count = self.detect_panel_count(prompt)
        if panel_count > 1:
            sub_prompts = await self._split_prompt(prompt)
            panels = []
            for i, sub in enumerate(sub_prompts):
                if token_queue is not None:
                    self._push_status(token_queue, f"Drawing panel {i+1}...")
                panel = await self.generate_panel(
                    sub_prompt=sub,
                    panel_index=i,
                    topic=topic,
                    difficulty=difficulty,
                    grade=grade,
                    session=session,
                    preferred_model=preferred_model,
                    token_queue=token_queue,
                )
                panels.append(panel.model_dump())

            if token_queue is not None:
                token_queue.put_nowait(TokenChunk(delta="", node="diagram", done=True))

            return {
                "title": prompt[:80] if len(prompt) > 80 else prompt,
                "diagram_svg": panels[0]["svg"],
                "labels": panels[0]["labels"],
                "topic": topic,
                "difficulty": difficulty,
                "model_used": "",
                "textbook_references": textbook_references,
                "panels": panels,
            }

        system_prompt = DIAGRAM_SYSTEM_PROMPT
        try:
            filter_obj = RetrievalFilter(grade_level=grade, source_type="textbook_diagram")
            results = await self.adapter.search(query=topic, n_results=3, filter_obj=filter_obj)
            if results:
                context = self.adapter.format_context(results)
                system_prompt = DIAGRAM_SYSTEM_PROMPT + CURRICULUM_CONTEXT_BLOCK.format(
                    context=context
                )
                for r in results:
                    textbook_references.append(
                        {
                            "grade": r.metadata.get("grade_level", grade),
                            "unit": r.metadata.get("unit"),
                            "figure_number": r.metadata.get("figure_number"),
                            "caption": r.content,
                        }
                    )
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

        if token_queue is not None:
            self._push_status(token_queue, f"Drawing {topic} diagram...")
            buf: list[str] = []
            async for token in self._call_llm_stream(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.7,
                max_tokens=4096,
                request_type="diagram_generation",
                preferred_model=preferred_model,
            ):
                buf.append(token)
                token_queue.put_nowait(TokenChunk(delta=token, node="diagram"))
            content = "".join(buf)
        else:
            result = await self._call_llm(
                system_prompt=system_prompt,
                user_message=user_message,
                session=session,
                temperature=0.7,
                max_tokens=4096,
                request_type="diagram_generation",
                preferred_model=preferred_model,
            )
            content = result["content"]

        model_used = "" if token_queue is not None else result.get("model", "")
        try:
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
                "model_used": model_used,
                "textbook_references": textbook_references,
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("diagram_parse_error", error=str(e), content=content[:300])
            return {
                "title": f"{topic} - {prompt[:50]}",
                "diagram_svg": content,
                "labels": [],
                "topic": topic,
                "difficulty": difficulty,
                "model_used": model_used,
                "textbook_references": textbook_references,
            }
        finally:
            if token_queue is not None:
                token_queue.put_nowait(TokenChunk(delta="", node="diagram", done=True))


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
            results.append(
                {
                    "label_id": lid,
                    "correct_text": correct["text"],
                    "submitted_text": sub["text"],
                    "is_correct": is_correct,
                    "explanation": explanation,
                }
            )
        else:
            results.append(
                {
                    "label_id": lid,
                    "correct_text": "",
                    "submitted_text": sub["text"],
                    "is_correct": False,
                    "explanation": "Unknown label position.",
                }
            )
    return results
