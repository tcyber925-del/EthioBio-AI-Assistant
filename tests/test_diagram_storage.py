"""Tests for textbook diagram storage and retrieval."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import inspect

from src.database.models import TextbookDiagram


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


def test_get_textbook_diagrams_endpoint_signature():
    from src.api.diagram import router

    textbok_routes = [r for r in router.routes if r.path == "/diagram/textbook"]
    assert len(textbok_routes) == 1
    assert "GET" in textbok_routes[0].methods


def test_index_script_imports():
    import importlib.util
    spec = importlib.util.find_spec("scripts.index_diagrams")
    if spec is not None:
        import scripts.index_diagrams
        assert callable(scripts.index_diagrams.main)


@pytest.mark.asyncio
async def test_index_script_upserts_to_chromadb():
    """index_diagrams.py wires PostgreSQL -> ChromaDB embedding + upsert."""
    from scripts.index_diagrams import index_diagram_captions

    records = [
        TextbookDiagram(
            id="11111111-1111-1111-1111-111111111111",
            grade_level=10,
            unit="Unit 2",
            topic="Cell Biology",
            caption="Diagram of an animal cell",
            image_path="data/diagrams/10/animal_cell_1.jpg",
            figure_number=1,
            page_number=42,
            source_file="biology_grade10.pdf",
        ),
        TextbookDiagram(
            id="22222222-2222-2222-2222-222222222222",
            grade_level=10,
            unit="Unit 3",
            topic="Genetics",
            caption="DNA replication fork showing leading and lagging strands",
            image_path="data/diagrams/10/dna_replication_1.jpg",
            figure_number=1,
            page_number=78,
            source_file="biology_grade10.pdf",
        ),
    ]

    mock_adapter = MagicMock()
    mock_adapter.embedder.embed_batch = AsyncMock(return_value=[[0.1] * 384, [0.2] * 384])
    mock_adapter.vector_store.add_documents = AsyncMock()

    result = await index_diagram_captions(records, adapter=mock_adapter, dry_run=False)

    assert result["indexed"] == 2
    assert result["skipped"] == 0
    mock_adapter.vector_store.add_documents.assert_called_once()
    call_args = mock_adapter.vector_store.add_documents.call_args
    assert len(call_args.kwargs["texts"]) == 2
    assert call_args.kwargs["metadatas"][0] == {
        "source_type": "textbook_diagram",
        "grade_level": 10,
        "unit": "Unit 2",
        "topic": "Cell Biology",
        "figure_number": 1,
        "image_path": "data/diagrams/10/animal_cell_1.jpg",
    }
    assert "animal cell" in call_args.kwargs["texts"][0]
    assert "DNA" in call_args.kwargs["texts"][1]
    assert call_args.kwargs["ids"] == [
        "diagram_caption_11111111-1111-1111-1111-111111111111",
        "diagram_caption_22222222-2222-2222-2222-222222222222",
    ]


@pytest.mark.asyncio
async def test_index_dry_run():
    from scripts.index_diagrams import index_diagram_captions

    records = [
        TextbookDiagram(
            id="11111111-1111-1111-1111-111111111111",
            grade_level=9,
            unit="Unit 1",
            topic="Biology",
            caption="test",
            image_path="test.jpg",
            figure_number=1,
            page_number=1,
            source_file="test.pdf",
        ),
    ]

    mock_adapter = MagicMock()
    result = await index_diagram_captions(records, adapter=mock_adapter, dry_run=True)

    assert result["indexed"] == 0
    assert result["skipped"] == 1
    mock_adapter.vector_store.add_documents.assert_not_called()
