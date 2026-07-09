import json
import structlog
from src.agents.base import BaseAgent
from src.llm.router import ModelRouter

logger = structlog.get_logger()

class MisconceptionAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="misconception_agent")

    async def execute(self, **kwargs) -> str:
        task = kwargs.get("task", "")
        context = kwargs.get("context", {})
        
        prompt = f"""You are the Misconception Agent.
Your responsibility is to detect and analyze student misconceptions, and determine root causes.
Context:
{context}

Task:
{task}

Provide your analysis in a structured format."""
        
        result = await self._call_llm(
            system_prompt=prompt,
            user_message=task,
            temperature=0.3,
            max_tokens=1000,
            request_type="misconception_analysis"
        )
        return result["content"]

    async def reflect(self, past_diagnosis: dict, outcome_data: dict) -> dict:
        """
        Agent Reflection Loop: Evaluates a historical misconception diagnosis against later student performance.
        Returns a JSON-parseable string containing diagnosis accuracy and required model updates.
        """
        prompt = f"""You are the Misconception Agent performing reflection.
Evaluate if your past diagnosis of a student's misconception was accurate based on their subsequent performance outcome.

Past Diagnosis:
{past_diagnosis}

Subsequent Student Outcome:
{outcome_data}

Provide a JSON response with:
- "diagnosis_accuracy": 1-10 integer
- "lessons_learned": string analyzing why the diagnosis was correct or incorrect
- "model_updates": string advising on how to update your internal misconception logic
"""
        
        result = await self._call_llm(
            system_prompt="You evaluate educational diagnoses and always output valid JSON.",
            user_message=prompt,
            temperature=0.1,
            max_tokens=800,
            request_type="misconception_reflection"
        )
        
        try:
            return json.loads(result["content"])
        except json.JSONDecodeError:
            return {
                "diagnosis_accuracy": 5,
                "lessons_learned": "Failed to parse reflection. Raw output: " + result["content"],
                "model_updates": "Review raw output manually."
            }
