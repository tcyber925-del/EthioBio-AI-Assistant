import httpx
import structlog

from src.config import settings

logger = structlog.get_logger()


class OllamaClient:
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_chat_model
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))

    async def chat(
        self,
        messages: list[dict],
        model: str = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict:
        model_name = model or self.model
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            logger.info("ollama_chat_success", model=model_name, input_tokens=len(str(messages)))
            return {
                "content": result["message"]["content"],
                "model": model_name,
                "usage": {
                    "total_tokens": result.get("eval_count", 0)
                    + result.get("prompt_eval_count", 0),
                },
            }
        except httpx.HTTPStatusError as e:
            logger.error(
                "ollama_chat_error", model=model_name, status=e.response.status_code, error=str(e)
            )
            if e.response.status_code == 404:
                raise ConnectionError(
                    f"Model '{model_name}' not found in Ollama. Run: ollama pull {model_name}"
                )
            raise
        except httpx.RequestError as e:
            logger.error("ollama_connection_error", model=model_name, error=str(e))
            raise ConnectionError(f"Could not reach Ollama at {self.base_url}")

    async def generate_embedding(self, text: str, model: str = None) -> list[float]:
        model_name = model or settings.ollama_embed_model
        try:
            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model_name, "prompt": text},
            )
            response.raise_for_status()
            result = response.json()
            return result["embedding"]
        except Exception as e:
            logger.error("ollama_embed_error", model=model_name, error=str(e))
            raise

    async def check_health(self) -> bool:
        try:
            response = await self.client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.is_success
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()
