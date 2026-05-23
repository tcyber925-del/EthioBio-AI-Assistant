from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.export.docx_exporter import export_lesson_plan_to_docx, export_quiz_to_docx
from src.export.pdf_exporter import export_lesson_plan_to_pdf, export_quiz_to_pdf
from src.main import app


class TestDocxExporter:
    def test_export_quiz_to_docx_returns_bytes(self):
        quiz = {"title": "Test Quiz", "grade_level": 10, "topic": "Cell Biology"}
        questions = [
            {
                "question_type": "multiple_choice",
                "question_text": "What is a cell?",
                "options": ["A) Nucleus", "B) Membrane", "C) Cytoplasm"],
                "correct_answer": "A",
                "explanation": "The nucleus is the control center.",
            },
            {
                "question_type": "true_false",
                "question_text": "Mitochondria produce energy.",
                "options": None,
                "correct_answer": "True",
                "explanation": "Mitochondria are the powerhouses of the cell.",
            },
        ]
        result = export_quiz_to_docx(quiz, questions)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_lesson_plan_to_docx_returns_bytes(self):
        lesson = {
            "grade_level": 10,
            "topic": "Photosynthesis",
            "objective": "Understand photosynthesis",
            "prior_knowledge": "Basic plant parts",
            "explanation": "Photosynthesis is the process...",
            "activities": [{"title": "Lab experiment", "duration": "20 min"}],
            "assessment": "Quiz on photosynthesis",
            "homework": "Draw the process",
            "teacher_notes": "Prepare materials ahead",
        }
        result = export_lesson_plan_to_docx(lesson)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_quiz_to_docx_empty_questions(self):
        quiz = {"title": "Empty Quiz", "grade_level": 7, "topic": "Ecology"}
        result = export_quiz_to_docx(quiz, [])
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_lesson_plan_to_docx_minimal(self):
        lesson = {
            "grade_level": 9,
            "topic": "Genetics",
            "objective": "Basic genetics",
            "prior_knowledge": None,
            "explanation": "Genetics study...",
            "activities": [],
            "assessment": "",
            "homework": None,
            "teacher_notes": None,
        }
        result = export_lesson_plan_to_docx(lesson)
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestPdfExporter:
    def test_export_quiz_to_pdf_returns_bytes(self):
        quiz = {"title": "Test Quiz PDF", "grade_level": 10, "topic": "Cell Biology"}
        questions = [
            {
                "question_type": "multiple_choice",
                "question_text": "What is a cell?",
                "options": ["A) Nucleus", "B) Membrane", "C) Cytoplasm"],
                "correct_answer": "A",
                "explanation": "The nucleus is the control center.",
            },
        ]
        result = export_quiz_to_pdf(quiz, questions)
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(b"%PDF")

    def test_export_lesson_plan_to_pdf_returns_bytes(self):
        lesson = {
            "grade_level": 10,
            "topic": "Photosynthesis",
            "objective": "Understand photosynthesis",
            "prior_knowledge": "Basic plant parts",
            "explanation": "Photosynthesis is the process...",
            "activities": [],
            "assessment": "Quiz",
            "homework": "Draw the process",
            "teacher_notes": "Prepare materials",
        }
        result = export_lesson_plan_to_pdf(lesson)
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(b"%PDF")

    def test_export_quiz_to_pdf_empty_questions(self):
        quiz = {"title": "Empty Quiz", "grade_level": 7, "topic": "Ecology"}
        result = export_quiz_to_pdf(quiz, [])
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(b"%PDF")

    def test_export_lesson_plan_to_pdf_minimal(self):
        lesson = {
            "grade_level": 9,
            "topic": "Genetics",
            "objective": "Basic genetics",
            "prior_knowledge": None,
            "explanation": "Genetics study...",
            "activities": [],
            "assessment": "",
            "homework": None,
            "teacher_notes": None,
        }
        result = export_lesson_plan_to_pdf(lesson)
        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result.startswith(b"%PDF")


@pytest.mark.asyncio
class TestExportEndpoints:
    async def test_export_quiz_not_found(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            fake_id = str(uuid4())
            response = await client.get(f"/export/quiz/{fake_id}")
            assert response.status_code in (404, 500)

    async def test_export_quiz_invalid_uuid(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/export/quiz/not-a-uuid")
            assert response.status_code == 400

    async def test_export_lesson_plan_not_found(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            fake_id = str(uuid4())
            response = await client.get(f"/export/lesson-plan/{fake_id}")
            assert response.status_code in (404, 500)

    async def test_export_lesson_plan_invalid_uuid(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/export/lesson-plan/not-a-uuid")
            assert response.status_code == 400

    async def test_export_invalid_format(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            fake_id = str(uuid4())
            response = await client.get(f"/export/quiz/{fake_id}?format=html")
            assert response.status_code == 422
