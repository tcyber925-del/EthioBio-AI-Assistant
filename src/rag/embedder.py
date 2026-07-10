import structlog

from src.llm.router import ModelRouter

logger = structlog.get_logger()

_sentence_transformer_model = None


def _get_or_create_sentence_transformer():
    global _sentence_transformer_model
    if _sentence_transformer_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _sentence_transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("sentence_transformer_loaded")
        except ImportError:
            logger.warning("sentence_transformers not available, will use Ollama for embeddings")
    return _sentence_transformer_model


class Embedder:
    def __init__(self, router: ModelRouter = None, force_ollama: bool = False):
        self.router = router or ModelRouter()
        self._force_ollama = force_ollama
        self._local_dim = 384

    @property
    def dimension(self) -> int:
        return self._local_dim

    def _get_local_model(self):
        return _get_or_create_sentence_transformer()

    async def embed_text(self, text: str, use_ollama: bool = False) -> list[float]:
        if use_ollama or self._force_ollama:
            return await self.router.generate_embedding(text)

        model = self._get_local_model()
        if model:
            return model.encode(text).tolist()

        return await self.router.generate_embedding(text)

    async def embed_batch(
        self, texts: list[str], batch_size: int = 16, use_ollama: bool = False
    ) -> list[list[float]]:
        if use_ollama or self._force_ollama:
            results = []
            for text in texts:
                emb = await self.embed_text(text, use_ollama=True)
                results.append(emb)
            return results

        model = self._get_local_model()
        if model:
            embeddings = model.encode(texts, batch_size=batch_size, show_progress_bar=False)
            return embeddings.tolist()

        results = []
        for text in texts:
            emb = await self.embed_text(text, use_ollama=True)
            results.append(emb)
        return results
