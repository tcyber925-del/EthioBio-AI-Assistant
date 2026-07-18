import structlog

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.retrieval.adapter import VectorStoreAdapter

logger = structlog.get_logger()


class ResearchAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter, adapter: VectorStoreAdapter | None = None):
        super().__init__(llm_router, name="research_agent")
        self.adapter = adapter

    async def execute(self, **kwargs) -> str:
        task = kwargs.get("task", "")
        context = kwargs.get("context", {})

        # Retrieve extra knowledge if adapter is available
        retrieved_context = ""
        if self.adapter:
            query = kwargs.get("query", task)
            try:
                results = await self.adapter.search(query, k=3)
                if results:
                    retrieved_context = "\n".join([r.content for r in results])
            except Exception as e:
                logger.warning("research_agent_retrieval_failed", error=str(e))

        prompt = f"""You are the Research Agent.
Your responsibility is to retrieve and analyze educational literature, best practices, and external knowledge to support educational decisions.
Provided Context:
{context}

Retrieved Knowledge:
{retrieved_context}

Task:
{task}

Provide your research summary with evidence and references."""

        result = await self._call_llm(
            system_prompt=prompt,
            user_message=task,
            temperature=0.2,
            max_tokens=1000,
            request_type="research_analysis",
        )
        return result["content"]
