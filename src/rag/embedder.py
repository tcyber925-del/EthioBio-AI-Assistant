import asyncio
import gc

import structlog

from src.llm.router import ModelRouter

logger = structlog.get_logger()

_local_model = None
_local_backend = None

_LOCAL_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_LOCAL_BATCH_SIZE = 16


def _encode(model, texts, batch_size=_LOCAL_BATCH_SIZE):
    """Encode texts through the fastembed (ONNX runtime) backend."""
    return [v.tolist() for v in model.embed(texts, batch_size=batch_size)]


def _get_or_create_local_model():
    """Load a local 384-dim embedder.

    Uses fastembed (ONNX runtime, low memory footprint) which fits the
    512MB free-tier instance budget. sentence-transformers/torch is NOT
    installed in the image; on failure, embeddings fall through to Ollama.
    """
    global _local_model, _local_backend
    if _local_model is not None:
        return _local_model

    try:
        from fastembed import TextEmbedding

        # threads=1: onnxruntime allocates per-thread workspaces; the
        # Render free tier has multiple vCPUs but only 512Mi RAM, so the
        # default thread count OOMs the process during batch embedding.
        _local_model = TextEmbedding(model_name=_LOCAL_MODEL_NAME, threads=1)
        _local_backend = "fastembed"
        logger.info("local_embedder_loaded", backend="fastembed")
    except Exception:
        logger.warning("fastembed unavailable, will use Ollama for embeddings", exc_info=True)
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
            return await loop.run_in_executor(None, lambda: _encode(model, [text], batch_size=1)[0])

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
            out: list[list[float]] = []
            for i in range(0, len(texts), batch_size):
                chunk = texts[i : i + batch_size]
                emb = await loop.run_in_executor(
                    None, lambda c=chunk: _encode(model, c, batch_size=_LOCAL_BATCH_SIZE)
                )
                out.extend(emb)
                if i % (batch_size * 8) == 0:
                    gc.collect()
            return out

        results = []
        for text in texts:
            emb = await self.embed_text(text, use_ollama=True)
            results.append(emb)
        return results
