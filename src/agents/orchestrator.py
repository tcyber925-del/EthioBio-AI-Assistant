import structlog

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()


class OrchestratorAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="orchestrator")

    async def classify_intent(self, user_message: str) -> dict:
        system_prompt = """You are an intent classifier for an Ethiopian biology education assistant.
Classify the user's message into exactly one of these intents:
- "tutor": biology question, concept explanation, homework help
- "quiz": wants a quiz, test, practice questions
- "lesson_plan": wants a lesson plan created
- "progress": wants to check progress or performance
- "translation": wants content translated to/from Amharic
- "admin": administrative or system question
- "general": greeting, chitchat, or unclear

Respond with ONLY a JSON object: {"intent": "tutor", "confidence": 0.95, "reason": "brief reason"}"""

        result = await self._call_llm(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=0.1,
            max_tokens=200,
            request_type="intent_classification",
        )

        import json
        try:
            parsed = json.loads(result["content"])
            return parsed
        except (json.JSONDecodeError, KeyError):
            logger.warning("intent_parse_fallback", content=result["content"][:100])
            return {"intent": "tutor", "confidence": 0.5, "reason": "parse_fallback"}

    async def route_to_agent(self, intent: str, user_message: str, **kwargs) -> str:
        agent_map = {
            "tutor": "tutor_agent",
            "quiz": "quiz_agent",
            "lesson_plan": "lesson_planner_agent",
            "progress": "student_progress_agent",
            "translation": "translator_agent",
            "admin": "admin",
        }
        return agent_map.get(intent, "tutor_agent")
