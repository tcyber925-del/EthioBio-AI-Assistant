from unittest.mock import AsyncMock, MagicMock

from src.core.retrieval.models import RetrievalResult, TextMatch
from src.graph.nodes.retrieval import RetrievalNode
from src.graph.state import AgentState
from src.retrieval.adapter import RetrievalResult as AdapterResult


def _kml_result(ko_id: str, text: str, score: float = 0.9) -> RetrievalResult:
    return RetrievalResult(
        ko_id=ko_id,
        title=f"Title {ko_id}",
        content_type="application/pdf",
        score=score,
        matches=[TextMatch(text=text, chunk_index=0, score=score)],
        workspace_id="ws-1",
    )


def _adapter_result(content: str, score: float = 0.8) -> AdapterResult:
    return AdapterResult(
        content=content,
        metadata={"grade_level": 10, "subject": "biology"},
        score=score,
        source_id="legacy-1",
    )


class FakeRouter:
    def __init__(self, results):
        self.results = results

    async def route_and_search(self, query, workspace_id=None, limit=10):
        return self.results


class TestRetrievalNodeWorkspace:
    async def test_workspace_results_used_when_present(self):
        adapter = MagicMock()
        router = FakeRouter(
            [_kml_result("ko-1", "mitochondria are the powerhouse of the cell")]
        )
        node = RetrievalNode(adapter, retrieval_router=router)

        state = AgentState(user_message="what are mitochondria", workspace_id="ws-1")
        out = await node(state)

        assert out.retrieved_chunks
        assert out.retrieved_chunks[0]["source_id"] == "ko-1"
        assert "mitochondria are the powerhouse" in out.retrieved_chunks[0]["content"]
        assert out.retrieved_chunks[0]["metadata"]["workspace_id"] == "ws-1"
        assert out.context
        adapter.search.assert_not_called()

    async def test_falls_back_to_curriculum_when_workspace_empty(self):
        adapter = MagicMock()
        adapter.search = AsyncMock(return_value=[_adapter_result("cell division basics")])
        adapter.format_context = lambda results: "curriculum context"
        router = FakeRouter([])
        node = RetrievalNode(adapter, retrieval_router=router)

        state = AgentState(user_message="cell division", grade_level=10, workspace_id="ws-1")
        out = await node(state)

        adapter.search.assert_awaited()
        assert out.retrieved_chunks[0]["source_id"] == "legacy-1"

    async def test_no_workspace_uses_curriculum_only(self):
        adapter = MagicMock()
        adapter.search = AsyncMock(return_value=[_adapter_result("legacy content")])
        adapter.format_context = lambda results: "curriculum context"
        node = RetrievalNode(adapter)

        state = AgentState(user_message="hello", grade_level=11)
        out = await node(state)

        adapter.search.assert_awaited()
        assert out.retrieved_chunks[0]["source_id"] == "legacy-1"

    async def test_kml_converter_uses_best_match_text(self):
        from src.graph.nodes.retrieval import kml_result_to_adapter

        r = _kml_result("ko-1", "best match text", score=0.9)
        converted = kml_result_to_adapter(r)
        assert converted.content == "best match text"
        assert converted.source_id == "ko-1"
        assert converted.metadata["workspace_id"] == "ws-1"

    async def test_missing_workspace_results_still_pass_through(self):
        r = _kml_result("ko-1", "content without workspace")
        r.workspace_id = None
        from src.graph.nodes.retrieval import kml_result_to_adapter

        converted = kml_result_to_adapter(r)
        assert converted.metadata["workspace_id"] == ""
