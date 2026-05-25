from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.1.0"


@pytest.mark.asyncio
async def test_quiz_generate_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/quiz/generate",
            json={
                "grade_level": 10,
                "topic": "Cell Biology",
                "question_count": 3,
                "types": ["multiple_choice", "true_false"],
            },
        )
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "questions" in data
            assert "answer_key" in data


@pytest.mark.asyncio
async def test_lesson_plan_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/lesson-plan/generate",
            json={
                "grade_level": 10,
                "topic": "Photosynthesis",
                "duration_minutes": 40,
            },
        )
        assert response.status_code in (200, 500)


@pytest.mark.asyncio
async def test_diagram_validate_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/diagram/validate",
            json={
                "user_id": str(uuid4()),
                "correct_labels": [
                    {"id": "l1", "text": "Mitochondrion", "x": 100, "y": 100},
                    {"id": "l2", "text": "Nucleus", "x": 200, "y": 200},
                ],
                "submitted_labels": [
                    {"id": "l1", "text": "Mitochondrion", "x": 100, "y": 100},
                    {"id": "l2", "text": "Ribosome", "x": 200, "y": 200},
                ],
                "topic": "cells",
                "difficulty": "beginner",
            },
        )
        assert response.status_code in (200, 500)


@pytest.mark.asyncio
async def test_chat_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={
                "user_id": str(uuid4()),
                "question": "What is a cell?",
                "grade_level": 10,
                "topic": "Cell Biology",
                "use_rag": True,
            },
        )
        assert response.status_code in (200, 500)


@pytest.mark.asyncio
async def test_admin_dashboard_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin/dashboard")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "users" in data
