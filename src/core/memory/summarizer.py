import json
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.memory.safety import (
    sanitize_summary_content,
    validate_confidence,
    validate_summary_content,
    validate_understanding_level,
)
from src.database.models import MemoryEducationalSummary, MemorySession
from src.rag.embedder import Embedder

logger = structlog.get_logger()

SUMMARIZE_SYSTEM_PROMPT = """You are an educational summarizer. Given a tutoring session's
context, produce a concise educational summary in JSON format.

Extract only:
- understanding_level: one of "beginner", "intermediate", "advanced", "mastered"
- key_misconceptions: list of strings, each describing a specific misconception detected
- confidence: float 0.0-1.0 (how well you understand the student's grasp)
- next_learning_goal: string describing what the student should focus on next

Output ONLY valid JSON, no other text."""


class Summarizer:
    def __init__(self, llm_router=None):
        from src.llm.router import ModelRouter

        self.llm = llm_router or ModelRouter()
        self.embedder = Embedder()
        self.vector_store = None

    def _get_vector_store(self):
        if self.vector_store is None:
            from src.core.memory.vector_store import MemoryVectorStore

            self.vector_store = MemoryVectorStore()
        return self.vector_store

    async def summarize_session(
        self,
        session: MemorySession,
        conversation_context: str | None = None,
        db: AsyncSession | None = None,
    ) -> MemoryEducationalSummary | None:
        if db is None:
            logger.warning("summarize_skipped_no_db")
            return None

        topic = session.active_topic or "general"
        context_parts = []
        if conversation_context:
            context_parts.append(conversation_context)
        if session.educational_context:
            context_parts.append(f"Educational context: {session.educational_context}")
        if session.unresolved_questions:
            qs = session.unresolved_questions
            if isinstance(qs, list):
                context_parts.append(f"Unresolved questions: {', '.join(str(q) for q in qs[:5])}")

        if not context_parts:
            logger.info("summarize_no_context", session_id=str(session.session_id))
            return None

        user_message = (
            f"Topic: {topic}\n"
            f"Tutoring mode: {session.tutoring_mode}\n"
            f"Conversation:\n{chr(10).join(context_parts)}"
        )

        try:
            result = await self.llm.route(
                messages=[
                    {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                request_type="summarize",
                temperature=0.3,
                max_tokens=1024,
            )

            content = result["content"]
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                start = content.find("{")
                end = content.rfind("}")
                if start >= 0 and end > start:
                    data = json.loads(content[start : end + 1])
                else:
                    logger.error("summarize_json_parse_failed", content=content[:200])
                    return None

            understanding = validate_understanding_level(data.get("understanding_level"))
            misconceptions = data.get("key_misconceptions", [])
            if not isinstance(misconceptions, list):
                misconceptions = []
            confidence = validate_confidence(float(data.get("confidence", 0.0)))
            next_goal = data.get("next_learning_goal", "") or ""

            summary_text = (
                f"Topic: {topic} | Understanding: {understanding} | "
                f"Confidence: {confidence:.2f} | "
                f"Next goal: {next_goal}"
            )
            if misconceptions:
                parts = "; ".join(str(m) for m in misconceptions[:3])
                summary_text += f" | Misconceptions: {parts}"

            summary_text = sanitize_summary_content(summary_text)
            valid, reason = validate_summary_content(summary_text)
            if not valid:
                logger.warning("summary_validation_failed", reason=reason)
                return None

            embedding = await self.embedder.embed_text(summary_text)

            summary_id = uuid.uuid4()
            try:
                vs = self._get_vector_store()
                await vs.add_memory(
                    embedding=embedding,
                    text=summary_text,
                    metadata={
                        "user_id": str(session.user_id),
                        "topic": topic,
                        "understanding_level": understanding,
                        "confidence": confidence,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                    memory_id=str(summary_id),
                )
            except Exception as vs_e:
                logger.warning("summary_vector_store_unavailable", error=str(vs_e))

            db_summary = MemoryEducationalSummary(
                id=summary_id,
                user_id=session.user_id,
                topic=topic,
                understanding_level=understanding,
                key_misconceptions=misconceptions,
                confidence=confidence,
                next_learning_goal=next_goal,
                embedding_id=str(summary_id),
            )
            db.add(db_summary)

            session.summary = summary_text
            await db.flush()

            # Entity extraction hook — best-effort LLM consolidation
            try:
                from src.core.memory.entity_extractor import EntityExtractor

                extractor = EntityExtractor()
                conv_text = conversation_context or chr(10).join(context_parts)
                await extractor.extract_from_session(
                    user_id=session.user_id,
                    topic=topic,
                    conversation_text=conv_text,
                    db=db,
                )
                await db.flush()
            except Exception:
                logger.warning("entity_extract_summarize_error", exc_info=True)

            logger.info(
                "session_summarized",
                session_id=str(session.session_id),
                topic=topic,
                confidence=confidence,
            )
            return db_summary

        except Exception as e:
            logger.error("summarize_error", session_id=str(session.session_id), error=str(e))
            return None
