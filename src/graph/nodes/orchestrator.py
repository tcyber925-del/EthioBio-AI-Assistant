"""Orchestrator node — classifies intent and routes to the right agent."""

import json

from src.graph.state import AgentState
from src.llm.router import ModelRouter


class OrchestratorNode:
    def __init__(self, router: ModelRouter):
        self.router = router

    async def __call__(self, state: AgentState) -> AgentState:
        prompt = f"""You are an intent classifier for an Ethiopian biology education assistant.
Classify the user's message into exactly one of these intents:
- "tutor": biology question, concept explanation, homework help
- "quiz": wants a quiz, test, practice questions
- "lesson_plan": wants a lesson plan created
- "progress": wants to check progress or performance
- "translation": wants content translated to/from Amharic
- "admin": administrative or system question
- "general": greeting, chitchat, or unclear

User message: "{state.user_message}"

Respond with ONLY a JSON object: {{"intent": "tutor", "confidence": 0.95}}"""

        messages = [
            {"role": "system", "content": "You are a precise intent classifier."},
            {"role": "user", "content": prompt},
        ]

        result = await self.router.route(messages, request_type="intent_classification", temperature=0.1, max_tokens=200)

        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = json.loads(content)
            state.intent = parsed.get("intent", "tutor")
            state.intent_confidence = parsed.get("confidence", 0.5)
        except (json.JSONDecodeError, KeyError):
            state.intent = "tutor"
            state.intent_confidence = 0.5

        return state


def needs_retrieval(state: AgentState) -> str:
    if state.intent in ("tutor", "quiz", "lesson_plan"):
        return "retrieve"
    return "skip_retrieval"
