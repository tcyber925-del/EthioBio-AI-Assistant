import json
from unittest.mock import AsyncMock

from src.agents.diagnostic_assessment import DiagnosticAgent

SAMPLE_ASSESSMENT = {
    "assessments": [
        {
            "topic": "Cell Biology",
            "questions": [
                {
                    "question_type": "multiple_choice",
                    "question_text": "What is the powerhouse of the cell?",
                    "options": ["A) Nucleus", "B) Mitochondria", "C) Ribosome", "D) Golgi"],
                    "correct_answer": "B) Mitochondria",
                    "explanation": "Mitochondria generate ATP through cellular respiration.",
                    "difficulty": "easy",
                }
            ],
        }
    ],
    "answer_key": "1. B",
}

VALID_JSON = json.dumps(SAMPLE_ASSESSMENT)


class TestDiagnosticAgent:
    def setup_method(self):
        self.router = AsyncMock()
        self.router.route.return_value = {
            "content": VALID_JSON,
            "model": "ollama/test-model",
        }
        self.agent = DiagnosticAgent(llm_router=self.router)

    async def test_generates_valid_assessment(self):
        result = await self.agent.generate(
            grade_level=10,
            topics=["Cell Biology"],
            questions_per_topic=3,
            language="en",
        )
        assert "assessments" in result
        assert "answer_key" in result
        assert "model_used" in result
        assert len(result["assessments"]) == 1
        assert result["assessments"][0]["topic"] == "Cell Biology"
        assert result["answer_key"] == "1. B"
        assert result["model_used"] == "ollama/test-model"

    async def test_parses_json_from_markdown_code_block(self):
        self.router.route.return_value = {
            "content": f"Here is the assessment:\n\n```json\n{VALID_JSON}\n```\n\nEnd.",
            "model": "ollama/test-model",
        }
        result = await self.agent.generate(grade_level=10, topics=["Cell Biology"])
        assert len(result["assessments"]) == 1

    async def test_parses_json_from_generic_code_block(self):
        self.router.route.return_value = {
            "content": f"```\n{VALID_JSON}\n```",
            "model": "ollama/test-model",
        }
        result = await self.agent.generate(grade_level=10, topics=["Cell Biology"])
        assert len(result["assessments"]) == 1

    async def test_replaces_questions_per_topic_in_prompt(self):
        self.router.route.return_value = {
            "content": VALID_JSON,
            "model": "ollama/test-model",
        }
        await self.agent.generate(
            grade_level=10,
            topics=["Cell Biology"],
            questions_per_topic=5,
            language="en",
        )
        _, kwargs = self.router.route.await_args
        system_prompt = kwargs["messages"][0]["content"]
        assert "{questions_per_topic}" not in system_prompt
        assert "5" in system_prompt

    async def test_returns_empty_on_invalid_json(self):
        self.router.route.return_value = {
            "content": "This is not JSON at all",
            "model": "ollama/test-model",
        }
        result = await self.agent.generate(grade_level=10, topics=["Cell Biology"])
        assert result["assessments"] == []
        assert "Error parsing" in result["answer_key"]
        assert result["model_used"] == "ollama/test-model"

    async def test_returns_empty_on_partial_json(self):
        self.router.route.return_value = {
            "content": '{"answer_key": "only key"}',
            "model": "ollama/test-model",
        }
        result = await self.agent.generate(grade_level=10, topics=["Cell Biology"])
        assert result["assessments"] == []
        assert result["answer_key"] == "only key"

    async def test_sets_amharic_language_instruction(self):
        self.router.route.return_value = {
            "content": VALID_JSON,
            "model": "ollama/test-model",
        }
        await self.agent.generate(
            grade_level=10,
            topics=["Cell Biology"],
            language="am",
        )
        _, kwargs = self.router.route.await_args
        user_msg = kwargs["messages"][1]["content"]
        assert "Amharic" in user_msg or "አማርክ" in user_msg

    async def test_sets_both_language_instruction(self):
        self.router.route.return_value = {
            "content": VALID_JSON,
            "model": "ollama/test-model",
        }
        await self.agent.generate(
            grade_level=10,
            topics=["Cell Biology"],
            language="both",
        )
        _, kwargs = self.router.route.await_args
        user_msg = kwargs["messages"][1]["content"]
        assert "Amharic" in user_msg

    async def test_sets_english_language_instruction(self):
        self.router.route.return_value = {
            "content": VALID_JSON,
            "model": "ollama/test-model",
        }
        await self.agent.generate(
            grade_level=10,
            topics=["Cell Biology"],
            language="en",
        )
        _, kwargs = self.router.route.await_args
        user_msg = kwargs["messages"][1]["content"]
        assert "English" in user_msg

    async def test_passes_correct_parameters_to_router(self):
        self.router.route.return_value = {
            "content": VALID_JSON,
            "model": "ollama/test-model",
        }
        await self.agent.generate(
            grade_level=10,
            topics=["Cell Biology", "Genetics"],
            questions_per_topic=3,
            language="en",
        )
        self.router.route.assert_awaited_once()
        _, kwargs = self.router.route.await_args
        assert kwargs["request_type"] == "diagnostic_generation"
        assert kwargs["temperature"] == 0.7
        assert kwargs["max_tokens"] == 4096
        assert "Grade 10" in kwargs["messages"][1]["content"]
        assert "Cell Biology, Genetics" in kwargs["messages"][1]["content"]

    async def test_generates_multiple_topics(self):
        sample = dict(SAMPLE_ASSESSMENT)
        sample["assessments"] = [
            {
                "topic": "Cell Biology",
                "questions": [{
                    "question_type": "multiple_choice",
                    "question_text": "Q1",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": "Exp",
                    "difficulty": "easy",
                }],
            },
            {
                "topic": "Genetics",
                "questions": [{
                    "question_type": "true_false",
                    "question_text": "Q2",
                    "options": ["True", "False"],
                    "correct_answer": "True",
                    "explanation": "Exp",
                    "difficulty": "easy",
                }],
            },
        ]
        self.router.route.return_value = {
            "content": json.dumps(sample),
            "model": "ollama/test-model",
        }
        result = await self.agent.generate(
            grade_level=10,
            topics=["Cell Biology", "Genetics"],
        )
        assert len(result["assessments"]) == 2
        assert result["assessments"][0]["topic"] == "Cell Biology"
        assert result["assessments"][1]["topic"] == "Genetics"
