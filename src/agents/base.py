from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.llm.router import ModelRouter
import structlog

logger = structlog.get_logger()


class BaseAgent:
    def __init__(self, llm_router: ModelRouter, name: str = "base"):
        self.llm_router = llm_router
        self.name = name

    async def _call_llm(
        self,
        system_prompt: str,
        user_message: str,
        session: Optional[AsyncSession] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        request_type: str = "chat",
    ) -> dict:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        return await self.llm_router.route(
            messages=messages,
            request_type=request_type,
            session=session,
            temperature=temperature,
            max_tokens=max_tokens,
        )
