import structlog

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()


class CurriculumAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="curriculum_agent")

    async def execute(self, **kwargs) -> str:
        task = kwargs.get("task", "")
        context = kwargs.get("context", {})

        prompt = f"""You are the Curriculum Agent.
Your responsibility is to map curriculums, analyze topic dependencies and prerequisites, and evaluate learning objectives coverage.
Context:
{context}

Task:
{task}

Provide your curriculum insights and mapping."""

        result = await self._call_llm(
            system_prompt=prompt,
            user_message=task,
            temperature=0.3,
            max_tokens=1000,
            request_type="curriculum_analysis",
        )
        return result["content"]
