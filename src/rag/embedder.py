import asyncio

import structlog

from src.llm.router import ModelRouter

logger = structlog.get_logger()

_local_model = None
_local_backend = None


def _encode(model, texts, batch_size=16):
    """Encode texts through whichever local backend was loaded."""
    if _local_backend == "fastembed":
        return [v.tolist() for v in model.embed(texts, batch_size=batch_size)]
    return model.encode(texts, batch_size=batch_size, show_progress_bar=False).tolist()


def _get_or_create_local_model():
    """Load a local 384-dim embedder.

    Prefers fastembed (ONNX runtime, low memory footprint) over
    sentence-transformers + torch, which peaks well above the 512MB
    free-tier instance budget. Both produce identical all-MiniLM-L6-v2
    vectors (cosine ~1.0), so the pgvector store stays compatible.
    """
    global _local_model, _local_backend
    if _local_model is not None:
        return _local_model

    try:
        from fastembed import TextEmbedding

        _local_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        _local_backend = "fastembed"
        logger.info("local_embedder_loaded", backend="fastembed")
        return _local_model
    except Exception:
        logger.warning("fastembed unavailable, falling back to sentence-transformers")

    try:
        from sentence_transformers import SentenceTransformer

        _local_model = SentenceTransformer("all-MiniLM-L6-v2")
        _local_backend = "sentence-transformers"
        logger.info("local_embedder_loaded", backend="sentence-transformers")
    except ImportError:
        logger.warning("sentence-transformers not available, will use Ollama for embeddings")
    return _local_model


def _get_or_create_sentence_transformer():
    """Backwards-compatible alias for preloading the local embedder."""
    return _get_or_create_local_model()


class Embedder:
    def __init__(self, router: ModelRouter = None, force_ollama: bool = False):
        self.router = router or ModelRouter()
        self._force_ollama = force_ollama
        self._local_dim = 384

    @property
    def dimension(self) -> int:
        return self._local_dim

    def _get_local_model(self):
        return _get_or_create_local_model()

    async def embed_text(self, text: str, use_ollama: bool = False) -> list[float]:
        if use_ollama or self._force_ollama:
            return await self.router.generate_embedding(text)

        model = self._get_local_model()
        if model:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, lambda: _encode(model, [text], batch_size=1)[0]
            )

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
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, lambda: _encode(model, texts, batch_size=batch_size)
            )

        results = []
        for text in texts:
            emb = await self.embed_text(text, use_ollama=True)
            results.append(emb)
        return results
