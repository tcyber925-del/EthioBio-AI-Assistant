from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()

TRANSLATOR_SYSTEM_PROMPT = """You are EthioBio Translator, supporting English-Amharic bilingual biology education.

Rules:
1. Translate biology content between English and Amharic.
2. Keep scientific terms in English when appropriate.
3. Provide bilingual explanations when requested.
4. Maintain curriculum accuracy in both languages.
5. For Amharic text, use standard orthography."""


class TranslatorAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="translator")

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "am",
        session: Optional[AsyncSession] = None,
    ) -> dict:
        direction = f"{source_lang} to {target_lang}"
        user_message = f"""Translate from {direction}.
Source text: {text}

If target is Amharic, provide the Amharic translation. Keep scientific biology terms in English.
If target is English, translate the Amharic text to English."""

        result = await self._call_llm(
            system_prompt=TRANSLATOR_SYSTEM_PROMPT,
            user_message=user_message,
            session=session,
            temperature=0.3,
            max_tokens=2048,
            request_type="translation",
        )

        return {
            "translated_text": result["content"],
            "source_lang": source_lang,
            "target_lang": target_lang,
            "model_used": result.get("model", ""),
        }

    async def bilingual_summary(
        self,
        text: str,
        session: Optional[AsyncSession] = None,
    ) -> dict:
        user_message = f"""Create a bilingual summary in English and Amharic of the following biology content.
First provide English, then Amharic. Keep scientific terms in English.

Content: {text}"""

        result = await self._call_llm(
            system_prompt=TRANSLATOR_SYSTEM_PROMPT,
            user_message=user_message,
            session=session,
            temperature=0.4,
            max_tokens=2048,
            request_type="bilingual_summary",
        )

        return {
            "content": result["content"],
            "model_used": result.get("model", ""),
        }
