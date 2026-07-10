import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.diagram import DiagramLabel

# ── svg_render tests ──────────────────────────────────────────────────


class TestRenderSvgToPng:
    def test_returns_bytes_for_valid_svg(self):
        from src.utils.svg_render import render_svg_to_png

        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'>"
            "<rect width='100' height='100' fill='red'/></svg>"
        )
        result = render_svg_to_png(svg, width=100, height=100)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_respects_dimensions(self):
        from src.utils.svg_render import render_svg_to_png

        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' width='50' height='50'>"
            "<rect width='50' height='50' fill='blue'/></svg>"
        )
        result = render_svg_to_png(svg, width=50, height=50)
        assert isinstance(result, bytes)

    def test_raises_on_invalid_svg(self):
        from src.utils.svg_render import render_svg_to_png

        with pytest.raises(ValueError, match="Failed to render SVG"):
            render_svg_to_png("not valid svg", width=100, height=100)


# ── svg_render integration with real SVG ──────────────────────────────


class TestRenderSvgToPngIntegration:
    def test_renders_complex_svg(self):
        from src.utils.svg_render import render_svg_to_png

        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
            "<circle cx='400' cy='300' r='50' fill='#ff0000'/>"
            "<text x='400' y='300' font-family='Arial'>Nucleus</text>"
            "</svg>"
        )
        result = render_svg_to_png(svg, width=400, height=300)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_defaults_to_800x600(self):
        from src.utils.svg_render import render_svg_to_png

        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
            "<rect width='800' height='600' fill='green'/></svg>"
        )
        result = render_svg_to_png(svg)
        assert isinstance(result, bytes)
        assert len(result) > 0


# ── DiagramCritic tests ────────────────────────────────────────────────


class TestDiagramCriticXMLValidity:
    def test_xml_validity_valid_svg(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
            "<circle cx='400' cy='300' r='50'/></svg>"
        )
        assert critic.check_xml_validity(svg) is True

    def test_xml_validity_invalid_svg(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        assert critic.check_xml_validity("not valid") is False

    def test_xml_validity_malformed_tags(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        assert critic.check_xml_validity("<svg><unclosed>") is False

    def test_xml_validity_empty_string(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        assert critic.check_xml_validity("") is False


class TestDiagramCriticLabelBounds:
    def test_labels_all_within_viewbox(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        labels = [
            DiagramLabel(id="l1", text="Nucleus", x=400, y=300),
            DiagramLabel(id="l2", text="Cell Wall", x=200, y=100),
        ]
        issues = critic.check_label_bounds(labels, viewbox=(800, 600))
        assert len(issues) == 0

    def test_labels_out_of_bounds(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        labels = [
            DiagramLabel(id="l1", text="Nucleus", x=900, y=300),
        ]
        issues = critic.check_label_bounds(labels, viewbox=(800, 600))
        assert len(issues) == 1
        assert "l1" in issues[0] or "Nucleus" in issues[0]

    def test_labels_negative_coordinates(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        labels = [
            DiagramLabel(id="l1", text="Bad", x=-10, y=50),
        ]
        issues = critic.check_label_bounds(labels, viewbox=(800, 600))
        assert len(issues) == 1

    def test_labels_empty_list_returns_no_issues(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        issues = critic.check_label_bounds([], viewbox=(800, 600))
        assert len(issues) == 0


class TestDiagramCriticScore:
    def test_score_returns_float_between_0_and_10(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
            "<circle cx='400' cy='300' r='50'/></svg>"
        )
        score = critic.score(svg=svg, labels=[])
        assert isinstance(score, float)
        assert 0 <= score <= 10

    def test_score_penalizes_invalid_xml(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
            "<circle cx='400' cy='300' r='50'/></svg>"
        )
        good_score = critic.score(svg=svg, labels=[])
        bad_score = critic.score(svg="bad xml", labels=[])
        assert bad_score < good_score

    def test_score_penalizes_out_of_bounds_labels(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        valid_labels = [DiagramLabel(id="l1", text="A", x=400, y=300)]
        bad_labels = [DiagramLabel(id="l1", text="A", x=9999, y=300)]

        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
            "<circle cx='400' cy='300' r='50'/></svg>"
        )
        score_valid = critic.score(svg=svg, labels=valid_labels)
        score_bad = critic.score(svg=svg, labels=bad_labels)
        assert score_bad < score_valid


class TestDiagramCriticCritique:
    @pytest.mark.asyncio
    async def test_critique_returns_score_and_issues(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
            "<circle cx='400' cy='300' r='50'/></svg>"
        )
        result = await critic.critique(svg=svg, labels=[], prompt="Draw a cell")
        assert "score" in result
        assert "issues" in result
        assert isinstance(result["score"], float)
        assert isinstance(result["issues"], list)

    @pytest.mark.asyncio
    async def test_critique_includes_issues_for_bad_diagram(self):
        from src.agents.diagram_critic import DiagramCritic

        critic = DiagramCritic(llm_router=MagicMock())
        result = await critic.critique(svg="bad", labels=[], prompt="test")
        assert result["score"] < 7
        assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_critique_uses_llm_when_enabled(self):
        from src.agents.diagram_critic import DiagramCritic

        router = AsyncMock()
        router.route = AsyncMock(
            return_value={
                "content": json.dumps({"score": 6, "issues": ["labels unclear"]}),
                "model": "test",
            }
        )
        critic = DiagramCritic(llm_router=router)
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
            "<circle cx='400' cy='300' r='50'/></svg>"
        )
        result = await critic.critique(svg=svg, labels=[], prompt="test", use_llm=True)
        assert "score" in result
        assert isinstance(result["score"], float)


class TestDiagramCriticRefine:
    @pytest.mark.asyncio
    async def test_refine_loops_up_to_max_iterations(self):
        from src.agents.diagram import DiagramAgent
        from src.agents.diagram_critic import DiagramCritic

        router = AsyncMock()
        router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "title": "Cell",
                        "diagram_svg": (
                            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
                            "<circle cx='400' cy='300' r='50'/></svg>"
                        ),
                        "labels": [],
                    }
                ),
                "model": "test",
            }
        )
        mock_adapter = MagicMock()
        mock_adapter.search = AsyncMock(return_value=[])
        agent = DiagramAgent(llm_router=router, adapter=mock_adapter)

        critic = DiagramCritic(llm_router=router)
        result = await critic.refine(
            agent=agent,
            prompt="Draw a cell",
            topic="cells",
            difficulty="beginner",
            grade=10,
            max_iterations=2,
        )
        assert "svg" in result
        assert "labels" in result
        assert "score" in result
        assert isinstance(result["score"], float)

    @pytest.mark.asyncio
    async def test_refine_stops_when_score_high(self):
        from src.agents.diagram import DiagramAgent
        from src.agents.diagram_critic import DiagramCritic

        router = AsyncMock()
        router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "title": "Perfect Cell",
                        "diagram_svg": (
                            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
                            "<circle cx='400' cy='300' r='50'/>"
                            "<rect x='10' y='10' width='100' height='50'/></svg>"
                        ),
                        "labels": [{"id": "l1", "text": "Nucleus", "x": 400, "y": 300}],
                    }
                ),
                "model": "test",
            }
        )
        mock_adapter = MagicMock()
        mock_adapter.search = AsyncMock(return_value=[])
        agent = DiagramAgent(llm_router=router, adapter=mock_adapter)

        critic = DiagramCritic(llm_router=router)
        result = await critic.refine(
            agent=agent,
            prompt="Draw a cell",
            topic="cells",
            difficulty="beginner",
            grade=10,
            max_iterations=5,
        )
        assert result["score"] >= 7

    @pytest.mark.asyncio
    async def test_refine_returns_best_result(self):
        from src.agents.diagram import DiagramAgent
        from src.agents.diagram_critic import DiagramCritic

        router = AsyncMock()
        router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "title": "Best Cell",
                        "diagram_svg": (
                            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 800 600'>"
                            "<circle cx='400' cy='300' r='50'/>"
                            "<rect x='10' y='10' width='100' height='50'/>"
                            "<text x='50' y='50'>Label</text></svg>"
                        ),
                        "labels": [{"id": "l1", "text": "Nucleus", "x": 400, "y": 300}],
                    }
                ),
                "model": "test",
            }
        )
        mock_adapter = MagicMock()
        mock_adapter.search = AsyncMock(return_value=[])
        agent = DiagramAgent(llm_router=router, adapter=mock_adapter)

        critic = DiagramCritic(llm_router=router)

        result = await critic.refine(
            agent=agent,
            prompt="Draw a cell",
            topic="cells",
            difficulty="beginner",
            grade=10,
            max_iterations=3,
        )
        assert result["score"] >= 0

    @pytest.mark.asyncio
    async def test_refine_includes_issues_in_revision_prompt(self):
        from src.agents.diagram import DiagramAgent
        from src.agents.diagram_critic import DiagramCritic

        router = AsyncMock()
        router.route = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "title": "Bad Cell",
                        "diagram_svg": "bad",
                        "labels": [{"id": "l1", "text": "Nucleus", "x": 9999, "y": 300}],
                    }
                ),
                "model": "test",
            }
        )
        mock_adapter = MagicMock()
        mock_adapter.search = AsyncMock(return_value=[])
        agent = DiagramAgent(llm_router=router, adapter=mock_adapter)

        critic = DiagramCritic(llm_router=router)
        await critic.refine(
            agent=agent,
            prompt="Draw a cell",
            topic="cells",
            difficulty="beginner",
            grade=10,
            max_iterations=2,
        )
        route_calls = router.route.call_args_list
        last_call_messages = route_calls[-1][1]["messages"]
        user_msg = last_call_messages[-1]["content"]
        assert any(word in user_msg.lower() for word in ["revis", "improve", "fix", "issue"])
