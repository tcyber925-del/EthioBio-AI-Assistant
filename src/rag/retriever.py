from typing import Optional

import structlog

from src.rag.embedder import Embedder
from src.rag.vector_store import VectorStore

logger = structlog.get_logger()


class Retriever:
    def __init__(self, embedder: Embedder = None, vector_store: VectorStore = None):
        self.embedder = embedder or Embedder()
        self.vector_store = vector_store or VectorStore()

    async def retrieve(
        self,
        query: str,
        n_results: int = 5,
        grade_level: Optional[int] = None,
        topic: Optional[str] = None,
    ) -> list[dict]:
        query_embedding = await self.embedder.embed_text(query)

        filters = []
        if grade_level:
            filters.append({"grade_level": {"$eq": grade_level}})
        if topic:
            filters.append({"topic": {"$eq": topic}})

        where_clause = None
        if len(filters) == 1:
            where_clause = filters[0]
        elif len(filters) > 1:
            where_clause = {"$and": filters}

        results = await self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where_clause,
        )

        retrieved = []
        for i in range(len(results["documents"])):
            retrieved.append(
                {
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i] if i < len(results["metadatas"]) else {},
                    "score": 1.0 - results["distances"][i]
                    if i < len(results["distances"])
                    else 0.0,
                    "id": results["ids"][i] if i < len(results["ids"]) else "",
                }
            )

        if not retrieved and topic:
            logger.warning(
                "topic_filter_excluded_all",
                topic=topic,
                grade_level=grade_level,
                falling_back="no_topic_filter",
            )
            no_topic_where = {"grade_level": {"$eq": grade_level}} if grade_level else None
            results = await self.vector_store.query(
                query_embedding=query_embedding,
                n_results=n_results,
                where=no_topic_where,
            )
            retrieved = []
            for i in range(len(results["documents"])):
                retrieved.append(
                    {
                        "content": results["documents"][i],
                        "metadata": results["metadatas"][i]
                        if i < len(results["metadatas"])
                        else {},
                        "score": 1.0 - results["distances"][i]
                        if i < len(results["distances"])
                        else 0.0,
                        "id": results["ids"][i] if i < len(results["ids"]) else "",
                    }
                )

        logger.info("retrieved_documents", count=len(retrieved), query_preview=query[:50])
        return retrieved

    def format_context(self, documents: list[dict]) -> str:
        if not documents:
            return ""

        sections = []
        for i, doc in enumerate(documents, 1):
            meta = doc.get("metadata", {})
            grade = meta.get("grade_level", "")
            unit = meta.get("unit", "")
            topic = meta.get("topic", "")
            page = meta.get("page_number", "")

            header = f"[Source {i}]"
            if grade:
                header += f" Grade {grade} Biology"
            if unit:
                header += f" | {unit}"
            if topic:
                header += f" | {topic}"
            if page:
                header += f" | p.{page}"

            sections.append(f"{header}\n{doc['content']}")

        citation_instruction = (
            "IMPORTANT: When answering, cite the source for each key point using this exact format:\n"  # noqa: E501
            "(Grade X, Unit Y: Title, p. Z)\n"
            "Example: (Grade 10, Unit 3: Biochemical Molecules, p. 77)\n\n"
        )

        return citation_instruction + "\n\n".join(sections)
