"""Safety node — runs self-check on generated content."""

import json

from src.graph.state import AgentState
from src.llm.router import ModelRouter

SAFETY_PROMPT = """You are EthioBio Safety Agent. Review the following biology content for:
1. Factual accuracy
2. Grade-appropriateness
3. Safety (no harmful content)
4. Curriculum alignment
5. Clarity
6. Language quality (proper {language})

Respond with ONLY a JSON object:
{"safe": true/false, "issues": ["issue1"], "score": 0.0-1.0, "suggestions": ["suggestion"]}"""


class SafetyNode:
    def __init__(self, router: ModelRouter):
        self.router = router

    async def __call__(self, state: AgentState) -> AgentState:
        grade_context = f" (Grade {state.grade_level})" if state.grade_level else ""
        lang_names = {"en": "English", "am": "Amharic",
                       "both": "English/Amharic"}
        lang_name = lang_names.get(state.language, "English")
        safety_prompt = SAFETY_PROMPT.format(language=lang_name)

        messages = [
            {"role": "system", "content": safety_prompt},
            {
                "role": "user",
                "content": f"Review this biology content{grade_context}:\n\n{state.draft}",
            },
        ]

        result = await self.router.route(
            messages, request_type="safety_check", temperature=0.1, max_tokens=500
        )

        try:
            content = result["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            state.safe = parsed.get("safe", True)
            state.safety_issues = parsed.get("issues", [])
            state.safety_score = parsed.get("score", 1.0)
        except (json.JSONDecodeError, KeyError):
            state.safe = True
            state.safety_issues = []
            state.safety_score = 1.0

        if not state.safe or state.safety_score < 0.6:
            state.requires_teacher_review = True
            state.status = "needs_review"
        else:
            state.status = "approved"

        return state


def should_revise(state: AgentState) -> str:
    if not state.safe and state.safety_score < 0.4:
        return "reject"
    if not state.safe or state.safety_score < 0.7:
        return "revise"
    return "finalize"
