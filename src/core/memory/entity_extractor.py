import json
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import MemoryEntity

logger = structlog.get_logger()

BIOLOGY_TERMS = {
    "mitosis", "meiosis", "genetics", "dna", "rna", "chromosome", "gene",
    "allele", "phenotype", "genotype", "punnett", "photosynthesis",
    "cellular respiration", "protein", "enzyme", "mutation", "evolution",
    "natural selection", "cell division", "cytokinesis", "prophase",
    "metaphase", "anaphase", "telophase", "interphase", "gamete",
    "zygote", "homozygous", "heterozygous", "dominant", "recessive",
    "transcription", "translation", "codon", "anticodon",
}

DIFFICULTY_PATTERNS = [
    "struggles with", "struggling with", "confused by", "confused about",
    "difficulty with", "hard to understand", "don't understand",
    "doesn't understand", "can't grasp", "weak on", "needs help with",
]


class EntityExtractor:
    def __init__(self):
        self._nlp = None

    def _get_nlp(self):
        if self._nlp is None:
            import spacy
            try:
                self._nlp = spacy.load("en_core_web_sm")
            except OSError:
                import subprocess
                subprocess.run(
                    ["python", "-m", "spacy", "download", "en_core_web_sm"],
                    capture_output=True,
                )
                self._nlp = spacy.load("en_core_web_sm")
        return self._nlp

    def _extract_entities_from_text(self, text: str) -> list[dict]:
        nlp = self._get_nlp()
        doc = nlp(text)
        entities: list[dict] = []
        seen: set[str] = set()

        for ent in doc.ents:
            entity_text = ent.text.lower().strip()
            if entity_text in seen or len(entity_text) < 2:
                continue
            seen.add(entity_text)
            etype = "person" if ent.label_ == "PERSON" else "concept"
            entities.append({"text": entity_text, "type": etype})

        text_lower = text.lower()
        for term in BIOLOGY_TERMS:
            if term in text_lower and term not in seen:
                seen.add(term)
                entities.append({"text": term, "type": "concept"})

        for pattern in DIFFICULTY_PATTERNS:
            idx = text_lower.find(pattern)
            if idx >= 0:
                snippet = text[idx + len(pattern): idx + len(pattern) + 60].strip().rstrip(".,!?")
                if snippet and snippet not in seen:
                    seen.add(snippet)
                    entities.append({"text": snippet, "type": "difficulty"})

        return entities

    async def extract_from_turn(
        self,
        turn_text: str,
        user_id: uuid.UUID,
        session_id: uuid.UUID | None,
        db: AsyncSession,
    ) -> None:
        if not turn_text or not user_id:
            return
        try:
            entities = self._extract_entities_from_text(turn_text)
            if not entities:
                return

            for ent in entities:
                result = await db.execute(
                    select(MemoryEntity).where(
                        MemoryEntity.user_id == user_id,
                        MemoryEntity.entity_text == ent["text"],
                        MemoryEntity.entity_type == ent["type"],
                    )
                )
                existing = result.scalar_one_or_none()
                now = datetime.now(timezone.utc)

                if existing:
                    existing.mention_count += 1
                    existing.last_mentioned_at = now
                    if session_id and (existing.sessions_seen is None or session_id not in existing.sessions_seen):
                        if existing.sessions_seen is None:
                            existing.sessions_seen = []
                        existing.sessions_seen.append(session_id)
                else:
                    db.add(MemoryEntity(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        entity_text=ent["text"],
                        entity_type=ent["type"],
                        mention_count=1,
                        first_mentioned_at=now,
                        last_mentioned_at=now,
                        sessions_seen=[session_id] if session_id else [],
                    ))
            await db.flush()
        except Exception:
            logger.warning("entity_extract_turn_error", exc_info=True)

    async def extract_from_session(
        self,
        user_id: uuid.UUID,
        topic: str,
        conversation_text: str,
        db: AsyncSession,
    ) -> None:
        if not conversation_text or not user_id:
            return
        from src.llm.router import ModelRouter
        llm = ModelRouter()
        prompt = (
            "Extract key educational concepts, difficulties, and relationships "
            "from this tutoring session. Return ONLY valid JSON:\n"
            '{"entities": [{"text": "...", "type": "concept|difficulty"}]}\n\n'
            f"Topic: {topic}\nConversation:\n{conversation_text[:3000]}"
        )
        try:
            result = await llm.route(
                messages=[
                    {"role": "system", "content": "You extract educational entities from tutoring conversations. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
                request_type="entity_extraction",
                temperature=0.1,
                max_tokens=1024,
            )
            content = result["content"]
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                start = content.find("{")
                end = content.rfind("}")
                if start >= 0 and end > start:
                    data = json.loads(content[start: end + 1])
                else:
                    logger.warning("entity_extract_json_failed", content=content[:200])
                    return

            entities = data.get("entities", [])
            if not isinstance(entities, list):
                return

            for ent in entities:
                ent_text = str(ent.get("text", "")).lower().strip()
                ent_type = str(ent.get("type", "concept"))
                if not ent_text or len(ent_text) < 2:
                    continue
                result = await db.execute(
                    select(MemoryEntity).where(
                        MemoryEntity.user_id == user_id,
                        MemoryEntity.entity_text == ent_text,
                        MemoryEntity.entity_type == ent_type,
                    )
                )
                existing = result.scalar_one_or_none()
                now = datetime.now(timezone.utc)
                if existing:
                    existing.mention_count += 1
                    existing.last_mentioned_at = now
                else:
                    db.add(MemoryEntity(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        entity_text=ent_text,
                        entity_type=ent_type,
                        mention_count=1,
                        first_mentioned_at=now,
                        last_mentioned_at=now,
                    ))
            await db.flush()
        except Exception:
            logger.warning("entity_extract_session_error", exc_info=True)
