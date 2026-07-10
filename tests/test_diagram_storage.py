"""Tests for textbook diagram storage and retrieval."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
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


def test_textbook_reference_schema():
    from src.schemas.diagram import TextbookReference

    ref = TextbookReference(grade=10, unit="Unit 2", figure_number=1, caption="Animal cell")
    assert ref.grade == 10
    assert ref.caption == "Animal cell"


def test_diagram_generate_request_includes_grade():
    from src.schemas.diagram import DiagramGenerateRequest

    req = DiagramGenerateRequest(prompt="test", topic="cells")
    assert req.grade == 10

    req2 = DiagramGenerateRequest(prompt="test", topic="cells", grade=12)
    assert req2.grade == 12


def test_diagram_generate_response_includes_textbook_refs():
    from src.schemas.diagram import DiagramGenerateResponse, TextbookReference

    ref = TextbookReference(grade=10, unit="Unit 2", figure_number=1, caption="Animal cell")
    resp = DiagramGenerateResponse(
        title="Test",
        diagram_svg="<svg></svg>",
        labels=[],
        topic="cells",
        difficulty="beginner",
        model_used="test",
        textbook_references=[ref],
    )
    assert len(resp.textbook_references) == 1
    assert resp.textbook_references[0].caption == "Animal cell"


@pytest.mark.asyncio
async def test_rag_injects_context_when_found():
    from unittest.mock import AsyncMock, MagicMock

    from src.agents.diagram import DiagramAgent
    from src.llm.router import ModelRouter

    mock_router = AsyncMock(spec=ModelRouter)
    mock_router.route = AsyncMock(
        return_value={
            "content": '{"title":"Cell","diagram_svg":"<svg></svg>","labels":[]}',
            "model": "ollama/test",
        }
    )

    mock_adapter = MagicMock()
    mock_adapter.search = AsyncMock(
        return_value=[
            MagicMock(
                content="Diagram of an animal cell",
                metadata={
                    "source_type": "textbook_diagram",
                    "grade_level": 10,
                    "unit": "Unit 2",
                    "topic": "Cell Biology",
                    "figure_number": 1,
                    "image_path": "data/diagrams/10/animal_cell_1.jpg",
                },
                score=0.95,
                source_id="diagram_caption_1",
            ),
        ]
    )
    mock_adapter.format_context = MagicMock(return_value="[Grade 10] Diagram of an animal cell")

    agent = DiagramAgent(llm_router=mock_router, adapter=mock_adapter)
    result = await agent.generate(
        prompt="Draw a cell",
        topic="Cell Biology",
        grade=10,
    )

    assert len(result.get("textbook_references", [])) == 1
    assert result["textbook_references"][0]["caption"] == "Diagram of an animal cell"
    assert result["textbook_references"][0]["grade"] == 10
    assert "animal cell" in mock_router.route.call_args.kwargs["messages"][0]["content"]


@pytest.mark.asyncio
async def test_rag_fallback_when_not_found():
    from unittest.mock import AsyncMock, MagicMock

    from src.agents.diagram import DiagramAgent
    from src.llm.router import ModelRouter

    mock_router = AsyncMock(spec=ModelRouter)
    mock_router.route = AsyncMock(
        return_value={
            "content": '{"title":"Cell","diagram_svg":"<svg></svg>","labels":[]}',
            "model": "ollama/test",
        }
    )

    mock_adapter = MagicMock()
    mock_adapter.search = AsyncMock(return_value=[])
    mock_adapter.format_context = MagicMock(return_value="")

    agent = DiagramAgent(llm_router=mock_router, adapter=mock_adapter)
    result = await agent.generate(
        prompt="Draw a cell",
        topic="Cell Biology",
        grade=10,
    )

    assert result.get("textbook_references", []) == []
    msg = mock_router.route.call_args.kwargs["messages"][0]["content"]
    assert "Curriculum reference" not in msg


@pytest.mark.asyncio
async def test_rag_unavailable_graceful():
    from unittest.mock import AsyncMock, MagicMock

    from src.agents.diagram import DiagramAgent
    from src.llm.router import ModelRouter

    mock_router = AsyncMock(spec=ModelRouter)
    mock_router.route = AsyncMock(
        return_value={
            "content": '{"title":"Cell","diagram_svg":"<svg></svg>","labels":[]}',
            "model": "ollama/test",
        }
    )

    mock_adapter = MagicMock()
    mock_adapter.search = AsyncMock(side_effect=Exception("ChromaDB unavailable"))

    agent = DiagramAgent(llm_router=mock_router, adapter=mock_adapter)
    result = await agent.generate(
        prompt="Draw a cell",
        topic="Cell Biology",
        grade=10,
    )

    assert result.get("textbook_references", []) == []


@pytest.mark.asyncio
async def test_rag_respects_grade_filter():
    from unittest.mock import AsyncMock, MagicMock

    from src.agents.diagram import DiagramAgent

    mock_router = AsyncMock()
    mock_router.route = AsyncMock(
        return_value={
            "content": '{"title":"Cell","diagram_svg":"<svg></svg>","labels":[]}',
            "model": "ollama/test",
        }
    )

    mock_adapter = MagicMock()
    mock_adapter.search = AsyncMock(return_value=[])
    mock_adapter.format_context = MagicMock(return_value="")

    agent = DiagramAgent(llm_router=mock_router, adapter=mock_adapter)
    await agent.generate(prompt="test", topic="cells", grade=11)

    call_kwargs = mock_adapter.search.call_args.kwargs
    assert call_kwargs["filter_obj"].grade_level == 11
    assert call_kwargs["filter_obj"].source_type == "textbook_diagram"


def test_validate_request_accepts_textbook_diagram_id():
    from src.schemas.diagram import DiagramValidateRequest

    req = DiagramValidateRequest(
        user_id=uuid.uuid4(),
        correct_labels=[],
        submitted_labels=[],
        topic="cells",
        difficulty="beginner",
        textbook_diagram_id=uuid.uuid4(),
    )
    assert req.textbook_diagram_id is not None


def test_validate_response_includes_source():
    from src.schemas.diagram import DiagramLabelResult, DiagramValidateResponse

    resp = DiagramValidateResponse(
        score=100.0,
        total_labels=2,
        correct_count=2,
        results=[
            DiagramLabelResult(label_id="1", correct_text="X", submitted_text="X", is_correct=True),
        ],
        attempt_id=uuid.uuid4(),
        source="textbook",
    )
    assert resp.source == "textbook"


def test_validate_response_defaults_to_ai_generated():
    from src.schemas.diagram import DiagramLabelResult, DiagramValidateResponse

    resp = DiagramValidateResponse(
        score=100.0,
        total_labels=2,
        correct_count=2,
        results=[
            DiagramLabelResult(label_id="1", correct_text="X", submitted_text="X", is_correct=True),
        ],
        attempt_id=uuid.uuid4(),
    )
    assert resp.source == "ai_generated"


@pytest.mark.asyncio
async def test_validate_with_textbook_labels():
    from src.api.diagram import validate_diagram
    from src.schemas.diagram import DiagramLabel, DiagramValidateRequest

    fake_labels = [{"id": "1", "text": "Nucleus", "x": 0.5, "y": 0.3}]
    textbook_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_diagram = MagicMock()
    mock_diagram.ground_truth_labels = {
        "labels": fake_labels,
        "proposed": True,
        "human_reviewed": False,
    }
    mock_session.get = AsyncMock(return_value=mock_diagram)

    async def _fake_refresh(instance):
        instance.id = uuid.uuid4()

    mock_session.refresh = AsyncMock(side_effect=_fake_refresh)

    request = DiagramValidateRequest(
        user_id=uuid.uuid4(),
        correct_labels=[DiagramLabel(id="ignored", text="should not be used", x=0, y=0)],
        submitted_labels=[DiagramLabel(id="1", text="Nucleus", x=0.5, y=0.3)],
        topic="cells",
        difficulty="beginner",
        textbook_diagram_id=textbook_id,
    )

    result = await validate_diagram(request, session=mock_session)
    assert result.source == "textbook"
    assert result.score == 100.0
    assert result.correct_count == 1
    mock_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_validate_without_textbook_id():
    from src.api.diagram import validate_diagram
    from src.schemas.diagram import DiagramLabel, DiagramValidateRequest

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)

    async def _fake_refresh(instance):
        instance.id = uuid.uuid4()

    mock_session.refresh = AsyncMock(side_effect=_fake_refresh)

    request = DiagramValidateRequest(
        user_id=uuid.uuid4(),
        correct_labels=[DiagramLabel(id="1", text="Nucleus", x=0.5, y=0.3)],
        submitted_labels=[DiagramLabel(id="1", text="Nucleus", x=0.5, y=0.3)],
        topic="cells",
        difficulty="beginner",
    )

    result = await validate_diagram(request, session=mock_session)
    assert result.source == "ai_generated"
    assert result.score == 100.0


@pytest.mark.asyncio
async def test_validate_textbook_not_found():
    from src.api.diagram import validate_diagram
    from src.schemas.diagram import DiagramLabel, DiagramValidateRequest

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)

    request = DiagramValidateRequest(
        user_id=uuid.uuid4(),
        correct_labels=[DiagramLabel(id="1", text="N", x=0, y=0)],
        submitted_labels=[DiagramLabel(id="1", text="N", x=0, y=0)],
        topic="cells",
        difficulty="beginner",
        textbook_diagram_id=uuid.uuid4(),
    )

    with pytest.raises(HTTPException) as exc:
        await validate_diagram(request, session=mock_session)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_validate_textbook_no_ground_truth():
    from src.api.diagram import validate_diagram
    from src.schemas.diagram import DiagramLabel, DiagramValidateRequest

    mock_session = AsyncMock()
    mock_diagram = MagicMock()
    mock_diagram.ground_truth_labels = None
    mock_session.get = AsyncMock(return_value=mock_diagram)

    request = DiagramValidateRequest(
        user_id=uuid.uuid4(),
        correct_labels=[DiagramLabel(id="1", text="N", x=0, y=0)],
        submitted_labels=[DiagramLabel(id="1", text="N", x=0, y=0)],
        topic="cells",
        difficulty="beginner",
        textbook_diagram_id=uuid.uuid4(),
    )

    with pytest.raises(HTTPException) as exc:
        await validate_diagram(request, session=mock_session)
    assert exc.value.status_code == 400
