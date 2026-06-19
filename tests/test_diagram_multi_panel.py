"""TDD tests for Phase 3 — Multi-panel diagram support.

Write tests first, then implement to make them pass.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError


# ── Schema tests (src/schemas/diagram.py) ──────────────────────────────

class TestDiagramPanelSchema:
    def test_diagram_panel_minimal(self):
        from src.schemas.diagram import DiagramPanel
        panel = DiagramPanel(id="panel_1", caption="Nucleus diagram", svg="<svg></svg>", labels=[])
        assert panel.id == "panel_1"
        assert panel.caption == "Nucleus diagram"
        assert panel.svg == "<svg></svg>"
        assert panel.labels == []

    def test_diagram_panel_requires_id(self):
        from src.schemas.diagram import DiagramPanel
        with pytest.raises(ValidationError):
            DiagramPanel(caption="test", svg="<svg></svg>", labels=[])

    def test_diagram_panel_requires_caption(self):
        from src.schemas.diagram import DiagramPanel
        with pytest.raises(ValidationError):
            DiagramPanel(id="p1", svg="<svg></svg>", labels=[])

    def test_diagram_panel_with_labels(self):
        from src.schemas.diagram import DiagramPanel, DiagramLabel
        labels = [
            DiagramLabel(id="l1", text="Nucleus", x=100, y=200),
            DiagramLabel(id="l2", text="Membrane", x=300, y=400),
        ]
        panel = DiagramPanel(id="p1", caption="Test", svg="<svg></svg>", labels=labels)
        assert len(panel.labels) == 2
        assert panel.labels[0].text == "Nucleus"

    def test_diagram_panel_default_labels_empty(self):
        from src.schemas.diagram import DiagramPanel
        panel = DiagramPanel(id="p1", caption="Test", svg="<svg></svg>", labels=[])
        assert panel.labels == []


class TestDiagramGenerateResponseMultiPanel:
    def test_response_with_panels(self):
        from src.schemas.diagram import DiagramGenerateResponse, DiagramLabel, DiagramPanel
        labels = [DiagramLabel(id="l1", text="A", x=10, y=20)]
        panel = DiagramPanel(id="p1", caption="Panel 1", svg="<svg>1</svg>", labels=labels)
        resp = DiagramGenerateResponse(
            title="Test",
            topic="cells",
            difficulty="beginner",
            diagram_svg="<svg>1</svg>",
            labels=labels,
            panels=[panel],
        )
        assert len(resp.panels) == 1
        assert resp.panels[0].id == "p1"
        assert resp.panels[0].caption == "Panel 1"

    def test_response_backward_compat_single_panel_via_diagram_svg(self):
        from src.schemas.diagram import DiagramGenerateResponse, DiagramLabel
        labels = [DiagramLabel(id="l1", text="Nucleus", x=100, y=200)]
        resp = DiagramGenerateResponse(
            title="Test",
            topic="cells",
            difficulty="beginner",
            diagram_svg="<svg></svg>",
            labels=labels,
        )
        assert resp.diagram_svg == "<svg></svg>"
        assert len(resp.labels) == 1
        assert resp.panels == []

    def test_response_panels_defaults_empty(self):
        from src.schemas.diagram import DiagramGenerateResponse, DiagramLabel
        labels = [DiagramLabel(id="l1", text="A", x=10, y=20)]
        resp = DiagramGenerateResponse(
            title="T", topic="cells", difficulty="beginner",
            diagram_svg="<svg></svg>", labels=labels,
        )
        assert resp.panels == []


# ── Agent tests (src/agents/diagram.py) ────────────────────────────────

class TestDetectPanelCount:
    def test_single_topic_no_connective(self):
        from src.agents.diagram import DiagramAgent
        agent = DiagramAgent(llm_router=MagicMock())
        count = agent.detect_panel_count("Draw a plant cell")
        assert count == 1

    @pytest.mark.parametrize("prompt", [
        "Compare plant cell and animal cell",
        "Animal cell vs plant cell",
        "Show external and internal structure of the heart",
        "Mitosis and meiosis comparison",
    ])
    def test_two_panel_prompts(self, prompt):
        from src.agents.diagram import DiagramAgent
        agent = DiagramAgent(llm_router=MagicMock())
        assert agent.detect_panel_count(prompt) == 2

    @pytest.mark.parametrize("prompt", [
        "Draw the structure of DNA",
        "Label the parts of a flower",
        "Diagram of the digestive system",
    ])
    def test_single_panel_prompts(self, prompt):
        from src.agents.diagram import DiagramAgent
        agent = DiagramAgent(llm_router=MagicMock())
        assert agent.detect_panel_count(prompt) == 1

    def test_empty_prompt_defaults_one(self):
        from src.agents.diagram import DiagramAgent
        agent = DiagramAgent(llm_router=MagicMock())
        assert agent.detect_panel_count("") == 1


class TestGeneratePanel:
    @pytest.mark.asyncio
    async def test_generate_panel_returns_valid_panel(self):
        from src.agents.diagram import DiagramAgent

        router = AsyncMock()
        router.route = AsyncMock(return_value={
            "content": json.dumps({
                "title": "Panel Test",
                "diagram_svg": "<svg viewBox='0 0 800 600'><circle cx='400' cy='300' r='50'/></svg>",
                "labels": [{"id": "l1", "text": "Center", "x": 400, "y": 300}],
            }),
            "model": "test",
        })

        agent = DiagramAgent(llm_router=router)
        panel = await agent.generate_panel(
            sub_prompt="Draw the nucleus",
            panel_index=0,
            topic="cells",
            difficulty="beginner",
            grade=10,
        )

        assert panel.id == "panel_0"
        assert "nucleus" in panel.caption.lower()
        assert "<svg" in panel.svg
        assert len(panel.labels) == 1
        assert panel.labels[0].text == "Center"

    @pytest.mark.asyncio
    async def test_generate_panel_injects_panel_number(self):
        from src.agents.diagram import DiagramAgent

        router = AsyncMock()
        router.route = AsyncMock(return_value={
            "content": json.dumps({
                "title": "Test",
                "diagram_svg": "<svg></svg>",
                "labels": [],
            }),
            "model": "test",
        })

        agent = DiagramAgent(llm_router=router)
        await agent.generate_panel("test", panel_index=2, topic="cells", difficulty="beginner", grade=10)

        call_args = router.route.call_args
        messages = call_args[1]["messages"]
        user_msg = messages[-1]["content"]
        assert "Panel 3" in user_msg or "panel 3" in user_msg.lower()

    @pytest.mark.asyncio
    async def test_generate_panel_fallback_on_parse_error(self):
        from src.agents.diagram import DiagramAgent

        router = AsyncMock()
        router.route = AsyncMock(return_value={
            "content": "not valid json",
            "model": "test",
        })

        agent = DiagramAgent(llm_router=router)
        panel = await agent.generate_panel("test", panel_index=0, topic="cells", difficulty="beginner", grade=10)

        assert panel.id == "panel_0"
        assert panel.svg == "not valid json"
        assert panel.labels == []


class TestMultiPanelGenerate:
    @pytest.mark.asyncio
    async def test_single_panel_generates_normally(self):
        from src.agents.diagram import DiagramAgent
        from src.retrieval.adapter import VectorStoreAdapter

        router = AsyncMock()
        router.route = AsyncMock(return_value={
            "content": json.dumps({
                "title": "Cell Structure",
                "diagram_svg": "<svg viewBox='0 0 800 600'><circle cx='400' cy='300' r='50'/></svg>",
                "labels": [{"id": "l1", "text": "Nucleus", "x": 400, "y": 300}],
            }),
            "model": "test",
        })

        mock_adapter = MagicMock(spec=VectorStoreAdapter)
        mock_adapter.search = AsyncMock(return_value=[])
        agent = DiagramAgent(llm_router=router, adapter=mock_adapter)
        result = await agent.generate(
            prompt="Draw a cell",
            topic="cells",
            difficulty="beginner",
            grade=10,
        )

        assert result["title"] == "Cell Structure"
        assert "<svg" in result["diagram_svg"]
        assert len(result["labels"]) == 1
        assert len(result.get("panels", [])) == 0

    @pytest.mark.asyncio
    async def test_two_panel_generates_two_panels(self):
        from src.agents.diagram import DiagramAgent

        router = AsyncMock()
        router.route = AsyncMock(return_value={
            "content": json.dumps({
                "title": "Panel Test",
                "diagram_svg": "<svg></svg>",
                "labels": [{"id": "l1", "text": "A", "x": 0, "y": 0}],
            }),
            "model": "test",
        })

        agent = DiagramAgent(llm_router=router)
        result = await agent.generate(
            prompt="Compare plant cell and animal cell",
            topic="cells",
            difficulty="beginner",
            grade=10,
        )

        assert len(result.get("panels", [])) == 2
        assert result["diagram_svg"] == result["panels"][0]["svg"]
        for panel in result["panels"]:
            assert "svg" in panel
            assert "caption" in panel
            assert "labels" in panel

    @pytest.mark.asyncio
    async def test_two_panel_sets_master_title(self):
        router = AsyncMock()
        router.route = AsyncMock(return_value={
            "content": json.dumps({
                "title": "Comparison",
                "diagram_svg": "<svg></svg>",
                "labels": [],
            }),
            "model": "test",
        })

        from src.agents.diagram import DiagramAgent
        agent = DiagramAgent(llm_router=router)
        result = await agent.generate(
            prompt="Plant cell vs animal cell",
            topic="cells",
            difficulty="beginner",
        )

        assert result["title"] == "Plant cell vs animal cell"

    @pytest.mark.asyncio
    async def test_two_panel_each_panel_calls_llm_separately(self):
        router = AsyncMock()
        router.route = AsyncMock(return_value={
            "content": json.dumps({
                "title": "Panel",
                "diagram_svg": "<svg></svg>",
                "labels": [],
            }),
            "model": "test",
        })

        from src.agents.diagram import DiagramAgent
        agent = DiagramAgent(llm_router=router)
        result = await agent.generate(
            prompt="External and internal structure of the heart",
            topic="anatomy",
            difficulty="intermediate",
        )

        # First call should be for the first panel, second for the second
        assert router.route.call_count == 2


# ── API tests (src/api/diagram.py) ─────────────────────────────────────

class TestGenerateEndpointMultiPanel:
    def test_endpoint_returns_panels_in_response(self):
        from src.schemas.diagram import DiagramGenerateResponse, DiagramPanel, DiagramLabel

        panel = DiagramPanel(
            id="panel_0",
            caption="First panel",
            svg="<svg></svg>",
            labels=[DiagramLabel(id="l1", text="Label", x=10, y=20)],
        )
        resp = DiagramGenerateResponse(
            title="Multi Test",
            topic="cells",
            difficulty="beginner",
            diagram_svg="<svg></svg>",
            labels=[],
            panels=[panel],
        )
        data = resp.model_dump()
        assert len(data["panels"]) == 1
        assert data["panels"][0]["id"] == "panel_0"
        assert data["panels"][0]["caption"] == "First panel"
