"""Tests for textbook diagram storage and retrieval."""

import uuid

from sqlalchemy import inspect


def test_textbook_diagram_model_columns():
    from src.database.models import TextbookDiagram

    mapper = inspect(TextbookDiagram)
    columns = {c.name: c.type.python_type for c in mapper.columns}

    assert "id" in columns
    assert columns["id"] is uuid.UUID
    assert "grade_level" in columns
    assert columns["grade_level"] is int
    assert "unit" in columns
    assert columns["unit"] is str
    assert "topic" in columns
    assert columns["topic"] is str
    assert "caption" in columns
    assert columns["caption"] is str
    assert "image_path" in columns
    assert columns["image_path"] is str
    assert "figure_number" in columns
    assert columns["figure_number"] is int
    assert "page_number" in columns
    assert columns["page_number"] is int
    assert "source_file" in columns
    assert columns["source_file"] is str
    assert "ground_truth_labels" in columns
    assert columns["ground_truth_labels"] in (dict, type(None))
    assert "created_at" in columns
    assert "updated_at" in columns


def test_textbook_diagram_response_schema():
    from src.schemas.diagram import TextbookDiagramResponse

    data = {
        "id": "00000000-0000-0000-0000-000000000001",
        "image_url": "/diagrams/static/10/grade-10_1.jpg",
        "caption": "Figure 1: Cell structure",
        "grade_level": 10,
        "unit": "Unit 1",
        "topic": "Cell Biology",
        "figure_number": 1,
        "page_number": 5,
        "source_file": "grade-10.pdf",
    }
    resp = TextbookDiagramResponse(**data)
    assert resp.grade_level == 10
    assert resp.image_url == "/diagrams/static/10/grade-10_1.jpg"
    assert resp.topic == "Cell Biology"
