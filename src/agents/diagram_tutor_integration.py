"""Integration between Tutor and Diagram generation.

When the tutor answers a science question, this module checks if a matching
textbook diagram exists and generates a diagram to accompany the response.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.diagram import DiagramAgent
from src.database.models import TextbookDiagram
from src.llm.router import ModelRouter

logger = structlog.get_logger()

DIAGRAM_TOPICS = frozenset(
    {
        # Biology
        "cells",
        "organ systems",
        "genetics",
        "anatomy",
        "botany",
        "angiosperms",
        "photosynthesis",
        "microbiology",
        "human biology",
        "zoology",
        "biochemistry",
        "biotechnology",
        # Chemistry
        "atomic structure",
        "chemical bonds",
        "periodic table",
        "chemical reactions",
        "acids and bases",
        # Physics
        "circuits",
        "forces",
        "optics",
        "waves",
        "electromagnetism",
        # Mathematics
        "geometry",
        "graphs",
        "functions",
        "triangles",
    }
)

_diagram_agent: DiagramAgent | None = None
_diagram_router: ModelRouter | None = None


def _get_diagram_agent() -> DiagramAgent:
    global _diagram_agent, _diagram_router
    if _diagram_agent is None:
        _diagram_router = ModelRouter()
        _diagram_agent = DiagramAgent(llm_router=_diagram_router)
    return _diagram_agent


async def find_best_textbook_diagram(
    query: str,
    grade_level: int | None,
    topic: str | None,
    session: AsyncSession,
) -> dict | None:
    """Query textbook_diagrams table for the best-matching figure.

    Priority:
    1. Exact grade + topic match (starts with, case-insensitive)
    2. Grade match + topic substring match
    3. Grade match only (first by figure_number)

    Returns {caption, figure_number, unit, grade_level, topic} or None.
    """
    stmt = select(TextbookDiagram)

    if grade_level is not None:
        stmt = stmt.where(TextbookDiagram.grade_level == grade_level)

    if topic:
        topic_lower = topic.lower()
        stmt = stmt.where(TextbookDiagram.topic.ilike(f"%{topic_lower}%"))

    stmt = stmt.order_by(TextbookDiagram.figure_number.asc()).limit(5)

    try:
        result = await session.execute(stmt)
        rows = result.scalars().all()
    except Exception:
        logger.warning("textbook_diagram_query_failed")
        return None

    if not rows:
        return None

    best = rows[0]
    if topic and len(rows) > 1:
        topic_lower = topic.lower().strip()
        for row in rows:
            row_topic = (row.topic or "").lower().strip()
            if row_topic == topic_lower:
                best = row
                break
        else:
            for row in rows:
                row_topic = (row.topic or "").lower().strip()
                if row_topic.startswith(topic_lower):
                    best = row
                    break

    return {
        "caption": best.caption or "",
        "figure_number": best.figure_number,
        "unit": best.unit or "",
        "grade_level": best.grade_level,
        "topic": best.topic or "",
    }


DIAGRAM_KEYWORDS = frozenset(
    {
        "diagram",
        "draw",
        "label",
        "structure",
        "parts",
        "component",
        "organ",
        "cell",
        "heart",
        "flower",
        "photosynthesis",
        "mitosis",
        "meiosis",
        "dna",
        "chromosome",
        "neuron",
        "eye",
        "ear",
        "leaf",
        "stem",
        "root",
        "chloroplast",
        "membrane",
        "nucleus",
    }
)


def should_generate_diagram(
    retrieved_chunks: list[dict] | None = None,
    topic: str | None = None,
    question: str | None = None,
) -> bool:
    """Check if a diagram should be generated.

    Three triggers (any match is sufficient):
    1. RAG trigger: retrieved chunks contain textbook_diagram source_type
    2. Topic trigger: topic is in the diagram-amenable topic list
    3. Keyword trigger: question text contains diagram-related keywords
    """
    if retrieved_chunks:
        for chunk in retrieved_chunks:
            meta = chunk.get("metadata", {})
            if meta.get("source_type") == "textbook_diagram":
                return True
    if topic and topic.lower() in DIAGRAM_TOPICS:
        return True
    if question:
        words = set(question.lower().split())
        if words & DIAGRAM_KEYWORDS:
            return True
    return False


async def generate_tutor_diagram(
    question: str,
    topic: str | None,
    grade_level: int | None,
    db_session: AsyncSession | None,
    retrieved_chunks: list[dict] | None = None,
    diagram_agent: DiagramAgent | None = None,
) -> dict:
    """Generate a diagram for the tutor response.

    1. Check if a diagram is needed (RAG trigger or topic-based)
    2. Look up the best-matching textbook figure caption
    3. Generate a diagram matching that caption

    Returns dict with diagram_svg, labels, title, textbook_ref,
    or empty dict if no diagram was generated.
    """
    if not should_generate_diagram(
        retrieved_chunks=retrieved_chunks,
        topic=topic,
        question=question,
    ):
        return {}

    prompt = question
    textbook_ref = ""
    figure_caption = ""

    if db_session is not None:
        try:
            match = await find_best_textbook_diagram(
                query=question,
                grade_level=grade_level,
                topic=topic,
                session=db_session,
            )
            if match and match.get("caption"):
                figure_caption = match["caption"]
                prompt = figure_caption
                ref_parts = []
                if match.get("grade_level"):
                    ref_parts.append(f"Grade {match['grade_level']}")
                if match.get("unit"):
                    ref_parts.append(match["unit"])
                if match.get("figure_number"):
                    ref_parts.append(f"Figure {match['figure_number']}")
                if ref_parts:
                    textbook_ref = ", ".join(ref_parts)
        except Exception as e:
            logger.warning("textbook_diagram_lookup_failed", error=str(e))

    agent = diagram_agent or _get_diagram_agent()

    try:
        result = await agent.generate(
            prompt=prompt,
            topic=topic or "science",
            difficulty="beginner",
            grade=grade_level or 10,
        )
    except Exception as e:
        logger.warning("tutor_diagram_generate_failed", error=str(e))
        return {}

    output = {
        "diagram_svg": result.get("diagram_svg", ""),
        "labels": result.get("labels", []),
        "title": result.get("title", prompt),
    }
    if textbook_ref:
        output["textbook_ref"] = textbook_ref

    return output
