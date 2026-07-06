import structlog
from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()

class ForecastAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="forecast_agent")

    async def execute(self, **kwargs) -> str:
        task = kwargs.get("task", "")
        context = kwargs.get("context", {})
        
        prompt = f"""You are the Forecast Agent.
Your responsibility is to analyze student digital twins and provide outcome predictions, simulations, and risk analyses.
Context:
{context}

Task:
{task}

Provide your forecast and scenario analyses."""
        
        result = await self._call_llm(
            system_prompt=prompt,
            user_message=task,
            temperature=0.3,
            max_tokens=1000,
            request_type="forecast_analysis"
        )
        return result["content"]
