import asyncio
import json
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.base import BaseAgent
from src.llm.router import ModelRouter
from src.schemas.streaming import TokenChunk

logger = structlog.get_logger()

DIAGNOSTIC_SYSTEM_PROMPT = (
    "You are EthioSci Diagnostic Assessor, creating a baseline diagnostic "
    "assessment for Ethiopian science students (Grades 7-12).\n\n"
    "CRITICAL RULE: Generate questions BASED STRICTLY on the Ethiopian "
    "science curriculum. Do NOT use general science knowledge. Every "
    "question must be directly derivable from the curriculum.\n\n"
    "For each topic, generate {questions_per_topic} questions at EASY "
    "difficulty to establish baseline knowledge.\n\n"
    "Output a JSON object with:\n"
    "{\n"
    '  "assessments": [\n'
    "    {{\n"
    '      "topic": "topic name",\n'
    '      "questions": [\n'
    "        {{\n"
    '          "question_type": "multiple_choice" | "true_false",\n'
    '          "question_text": "the question",\n'
    '          "options": ["A) ...", "B) ...", "C) ...", "D) ..."],\n'
    '          "correct_answer": "the correct answer",\n'
    '          "explanation": "brief explanation",\n'
    '          "difficulty": "easy"\n'
    "        }}\n"
    "      ]\n"
    "    }}\n"
    "  ],\n"
    '  "answer_key": "Concise answer key for all topics"\n'
    "}"
)


class DiagnosticAgent(BaseAgent):
    def __init__(self, llm_router: ModelRouter):
        super().__init__(llm_router, name="diagnostic")

    async def generate(
        self,
        grade_level: int,
        topics: list[str],
        questions_per_topic: int = 3,
        language: str = "en",
        session: Optional[AsyncSession] = None,
        token_queue: asyncio.Queue[TokenChunk | None] | None = None,
    ) -> dict:
        if language == "am":
            lang_instruction = "Generate all content in Amharic (አማርክ)."
        elif language == "both":
            lang_instruction = "Generate content in English with key terms also in Amharic."
        else:
            lang_instruction = "Generate all content in English."

        system_prompt = DIAGNOSTIC_SYSTEM_PROMPT.replace(
            "{questions_per_topic}", str(questions_per_topic)
        )

        user_message = (
            f"Generate a baseline diagnostic assessment for Grade {grade_level} science.\n"
            f"Topics to assess: {', '.join(topics)}\n"
            f"Questions per topic: {questions_per_topic}\n"
            f"All questions at EASY difficulty.\n"
            f"{lang_instruction}\n\n"
            f"Respond with valid JSON only."
        )

        content: str
        model_used: str = ""

        if token_queue is not None:
            token_queue.put_nowait(
                TokenChunk(
                    delta="Generating diagnostic assessment...", node="diagnostic", status=True
                )
            )
            buf: list[str] = []
            async for token in self._call_llm_stream(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.7,
                max_tokens=4096,
                request_type="diagnostic_generation",
            ):
                buf.append(token)
                token_queue.put_nowait(TokenChunk(delta=token, node="diagnostic"))
            content = "".join(buf)
            token_queue.put_nowait(TokenChunk(delta="", node="diagnostic", done=True))
        else:
            result = await self._call_llm(
                system_prompt=system_prompt,
                user_message=user_message,
                session=session,
                temperature=0.7,
                max_tokens=4096,
                request_type="diagnostic_generation",
            )
            content = result["content"]
            model_used = result.get("model", "")

        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            parsed = json.loads(content)
            return {
                "assessments": parsed.get("assessments", []),
                "answer_key": parsed.get("answer_key", ""),
                "model_used": model_used,
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("diagnostic_parse_error", error=str(e), content=content[:200])
            return {
                "assessments": [],
                "answer_key": "Error parsing diagnostic assessment",
                "model_used": model_used,
            }
