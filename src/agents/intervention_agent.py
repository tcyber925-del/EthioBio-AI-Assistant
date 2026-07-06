import structlog
from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()

class InterventionAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="intervention_agent")

    async def execute(self, **kwargs) -> str:
        task = kwargs.get("task", "")
        context = kwargs.get("context", {})
        
        prompt = f"""You are the Intervention Agent.
Your responsibility is to select, evaluate, and optimize educational interventions for students.
Context:
{context}

Task:
{task}

Provide your recommended interventions with historical success evidence."""
        
        result = await self._call_llm(
            system_prompt=prompt,
            user_message=task,
            temperature=0.3,
            max_tokens=1000,
            request_type="intervention_analysis"
        )
        return result["content"]

    async def reflect(self, past_intervention: dict, outcome_data: dict) -> dict:
        """
        Agent Reflection Loop: Evaluates a historical recommendation against actual student outcomes.
        Returns a JSON-parseable string containing effectiveness score and lessons learned.
        """
        prompt = f"""You are the Intervention Agent performing reflection.
Evaluate the effectiveness of a past intervention based on the student's outcome.

Past Intervention:
{past_intervention}

Student Outcome:
{outcome_data}

Provide a JSON response with:
- "effectiveness_score": 1-10 integer
- "lessons_learned": string analyzing why it worked or failed
- "suggested_adjustments": string advising future iterations
"""
        
        result = await self._call_llm(
            system_prompt="You evaluate educational interventions and always output valid JSON.",
            user_message=prompt,
            temperature=0.1,
            max_tokens=800,
            request_type="intervention_reflection"
        )
        
        # Parse JSON string from LLM result. In a real system, you might want strict structured outputs.
        import json
        try:
            return json.loads(result["content"])
        except Exception:
            return {
                "effectiveness_score": 5,
                "lessons_learned": "Failed to parse reflection. Raw output: " + result["content"],
                "suggested_adjustments": "Review raw output manually."
            }
