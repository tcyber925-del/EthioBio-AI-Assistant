"""Tutor node — generates biology answers with curriculum grounding."""

from src.graph.state import AgentState
from src.llm.router import ModelRouter

SYSTEM_PROMPT = """You are EthioBio Tutor, an AI biology tutor for Ethiopian middle and high school students (Grades 7-12).
The curriculum is English-first. You may also provide explanations in Amharic when requested.

Rules:
1. Answer biology questions based on the Ethiopian curriculum.
2. Adapt explanations to the student's grade level.
3. When provided with curriculum context, ALWAYS ground your answer in it.
4. Keep explanations clear, simple, and focused.
5. If you're unsure, say so clearly rather than guessing.
6. CITE SOURCES: When using curriculum content, cite the source at the end of each key point using this exact format:
   (Grade X, Unit Y: Title, p. Z)
   Example: (Grade 10, Unit 3: Biochemical Molecules, p. 77)
7. If the curriculum context does not contain enough information to fully answer the question, say what is missing."""


class TutorNode:
    def __init__(self, router: ModelRouter):
        self.router = router

    async def __call__(self, state: AgentState) -> AgentState:
        grade_context = f" (Grade {state.grade_level})" if state.grade_level else ""
        lang_context = "Answer in English." if state.language == "en" else "Answer in English with Amharic explanation."

        system = SYSTEM_PROMPT
        if state.context:
            system += f"\n\n## Curriculum Context\n{state.context}\n\nUse the above context to ground your answer."

        user_message = f"[Grade{grade_context}] {lang_context}\n\nStudent question: {state.user_message}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]

        result = await self.router.route(messages, request_type="tutor", temperature=0.7, max_tokens=2048)

        state.draft = result["content"]
        state.model_used = result.get("model", "")
        state.confidence = result.get("confidence", 0.0)

        return state
