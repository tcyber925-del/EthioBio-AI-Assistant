import structlog
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from src.config import settings

logger = structlog.get_logger()


class FallbackProvider:
    def __init__(self):
        self.provider = settings.fallback_provider
        self.api_key = settings.fallback_api_key
        self.model = settings.fallback_model
        self._client = None

    async def _get_client(self):
        if self._client:
            return self._client
        if self.provider == "openai":
            self._client = AsyncOpenAI(api_key=self.api_key)
        elif self.provider == "anthropic":
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def chat(
        self, messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048
    ) -> dict:
        client = await self._get_client()
        if not client:
            raise ValueError(f"Unsupported fallback provider: {self.provider}")

        try:
            if self.provider == "openai":
                response = await client.chat.completions.create(
                    model=self.model or "gpt-4o-mini",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                result = response.choices[0].message.content
                usage = {
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
            elif self.provider == "anthropic":
                system_msg = None
                chat_messages = messages
                if messages and messages[0].get("role") == "system":
                    system_msg = messages[0]["content"]
                    chat_messages = messages[1:]

                response = await client.messages.create(
                    model=self.model or "claude-3-haiku-20240307",
                    messages=chat_messages,
                    system=system_msg,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                result = response.content[0].text
                usage = {"total_tokens": response.usage.input_tokens + response.usage.output_tokens}
            else:
                raise ValueError(f"Provider {self.provider} not implemented")

            logger.info("fallback_success", provider=self.provider, model=self.model)
            return {"content": result, "model": f"{self.provider}/{self.model}", "usage": usage}

        except Exception as e:
            logger.error("fallback_error", provider=self.provider, error=str(e))
            raise

    async def is_available(self) -> bool:
        return bool(self.api_key and self.provider)
