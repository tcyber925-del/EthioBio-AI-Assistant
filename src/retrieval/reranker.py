"""Cross-encoder reranker for re-scoring retrieved passages.

Uses sentence-transformers cross-encoder to re-rank (query, passage) pairs
with much higher accuracy than bi-encoder embeddings alone.
"""


import structlog

logger = structlog.get_logger()

DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Reranker:
    """Cross-encoder reranker for passage re-scoring."""

    def __init__(self, model_name: str = DEFAULT_RERANKER_MODEL):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
                logger.info("reranker_model_loaded", model=self.model_name)
            except ImportError:
                logger.warning("sentence_transformers not available, reranker disabled")
            except Exception as e:
                logger.error("reranker_model_load_error", error=str(e))
        return self._model

    def rerank(
        self,
        query: str,
        passages: list[dict],
        top_k: int = 3,
        content_key: str = "content",
    ) -> list[dict]:
        """Re-rank passages by relevance to query using cross-encoder.

        Args:
            query: The search query.
            passages: List of dicts with at least a content key.
            top_k: Number of top results to return.
            content_key: Key in passage dict containing the text.

        Returns:
            Re-ranked list of passages with updated scores.
        """
        model = self._get_model()
        if model is None or not passages:
            return passages[:top_k]

        pairs = [(query, p[content_key]) for p in passages]
        scores = model.predict(pairs)

        scored = []
        for i, passage in enumerate(passages):
            passage_copy = dict(passage)
            passage_copy["rerank_score"] = float(scores[i])
            passage_copy["score"] = float(scores[i])
            scored.append(passage_copy)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        result = scored[:top_k]

        logger.info(
            "reranker_applied",
            query_preview=query[:50],
            input_count=len(passages),
            output_count=len(result),
        )
        return result
