"""Regression tests: streaming must always terminate when the graph fails.

The web SSE consumer (ConversationService.process_stream) blocks on the
token_queue until a terminal chunk (None / done / error) arrives. If the
graph raises before any node emits a terminal chunk, the stream would hang
until the platform request timeout (150s in production). These tests pin the
contract:
- run_graph always puts a None sentinel on the token_queue in its finally
- process_stream surfaces the failure as an SSE error event and returns
- the finally block cancels an abandoned graph_task to prevent zombie tasks
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.conversation import ConversationRequest
from src.schemas.streaming import TokenChunk


@pytest.mark.asyncio
async def test_run_graph_puts_none_sentinel_on_failure():
    import src.graph.orchestrator as orch

    queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()

    failing_graph = MagicMock()
    failing_graph.ainvoke = AsyncMock(side_effect=RuntimeError("LLM down"))

    with (
        patch.object(orch, "ModelRouter") as router_cls,
        patch.object(orch, "VectorStoreAdapter"),
        patch.object(orch, "build_unified_graph", return_value=failing_graph),
        patch.object(orch.pipeline_monitor, "start_trace") as start_trace,
        patch.object(orch.pipeline_monitor, "finalize_trace", new_callable=AsyncMock),
    ):
        router_cls.return_value.close = AsyncMock()
        start_trace.return_value = SimpleNamespace(trace_id="trace-1")

        with pytest.raises(RuntimeError):
            await orch.run_graph(user_message="hi", token_queue=queue)

        assert router_cls.return_value.close.await_count == 1
        terminal = None
        while not queue.empty():
            terminal = queue.get_nowait()
        assert terminal is None


@pytest.mark.asyncio
async def test_run_graph_puts_none_sentinel_on_success():
    import src.graph.orchestrator as orch

    queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()

    ok_graph = MagicMock()
    ok_graph.ainvoke = AsyncMock(
        return_value={
            "draft": "Ok",
            "model_used": "t",
            "confidence": 0.9,
            "retrieval_iterations": 0,
            "coverage_score": 1.0,
            "groundedness_score": 1.0,
            "hallucination_rate": 0.0,
            "safety_action": "finalize",
            "requires_teacher_review": False,
            "evidence_ids": [],
            "retrieved_chunks": [],
            "status": "approved",
            "session_id": "",
            "socratic_mode": False,
            "guiding_question": "",
            "socratic_stage": "",
            "socratic_focus": "",
            "socratic_understanding": "",
            "socratic_next_question": "",
            "hint_level": 0,
            "reveal_answer": False,
            "misconception_detected": False,
            "misconception_correction": "",
        }
    )

    with (
        patch.object(orch, "ModelRouter") as router_cls,
        patch.object(orch, "VectorStoreAdapter"),
        patch.object(orch, "build_unified_graph", return_value=ok_graph),
        patch.object(orch.pipeline_monitor, "start_trace") as start_trace,
        patch.object(orch.pipeline_monitor, "finalize_trace", new_callable=AsyncMock),
    ):
        router_cls.return_value.close = AsyncMock()
        start_trace.return_value = SimpleNamespace(trace_id="trace-1")

        result = await orch.run_graph(user_message="hi", token_queue=queue)

        assert result.answer == "Ok"
        assert router_cls.return_value.close.await_count == 1
        terminal = None
        while not queue.empty():
            terminal = queue.get_nowait()
        assert terminal is None, "sentinel absent on success path"


@pytest.mark.asyncio
async def test_process_stream_returns_error_event_on_graph_failure():
    import src.core.conversation.service as svc_module

    async def failing_run_graph(**kwargs):
        queue = kwargs["token_queue"]
        queue.put_nowait(TokenChunk(delta="Analyzing...", node="orchestrator", status=True))
        queue.put_nowait(None)
        raise RuntimeError("LLM down")

    with patch.object(svc_module, "run_graph", new=failing_run_graph):
        service = svc_module.ConversationService()
        req = ConversationRequest(
            user_id="",
            conversation_id="",
            session_id="",
            transcript="Test question",
            language="en",
        )

        async def _collect():
            return [line async for line in service.process_stream(req, AsyncMock())]

        lines = await asyncio.wait_for(_collect(), timeout=5)

    assert lines, "expected at least an error event"
    payloads = []
    for line in lines:
        assert line.startswith("data: "), f"unexpected SSE line: {line}"
        payloads.append(line.strip()[len("data: ") :])
    error_payloads = [p for p in payloads if "LLM down" in p]
    assert error_payloads, payloads


@pytest.mark.asyncio
async def test_process_stream_streams_tokens_and_final_meta_on_success():
    import src.core.conversation.service as svc_module

    async def ok_run_graph(**kwargs):
        queue = kwargs["token_queue"]
        queue.put_nowait(TokenChunk(delta="Photosynthesis ", node="tutor"))
        queue.put_nowait(TokenChunk(delta="is great", node="tutor"))
        queue.put_nowait(TokenChunk(delta="", node="tutor", done=True))
        return SimpleNamespace(
            answer="Photosynthesis is great",
            model_used="ollama/gemma4:31b",
            confidence=0.9,
            sources=["Grade 10 Biology"],
            status="approved",
            requires_teacher_review=False,
            session_id="",
            socratic_mode=False,
            socratic_stage="",
            socratic_focus="",
            socratic_understanding="",
            socratic_next_question="",
            hint_level=0,
            reveal_answer=False,
            misconception_detected=False,
            misconception_correction="",
        )

    with patch.object(svc_module, "run_graph", new=ok_run_graph):
        service = svc_module.ConversationService()
        req = ConversationRequest(
            user_id="",
            conversation_id="",
            session_id="",
            transcript="What is photosynthesis?",
            language="en",
        )

        async def _collect():
            return [line async for line in service.process_stream(req, AsyncMock())]

        lines = await asyncio.wait_for(_collect(), timeout=5)

    payloads = [line.strip()[len("data: ") :] for line in lines]
    assert any("Photosynthesis " in p for p in payloads), payloads
    assert any('"done": true' in p and '"error": null' in p for p in payloads), payloads
