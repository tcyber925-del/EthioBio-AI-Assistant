"""Tests for LLM streaming response support."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.agents.diagnostic_assessment import DiagnosticAgent
from src.agents.quiz import QuizAgent
from src.graph.state import AgentState
from src.llm.providers.base import LLMProvider
from src.schemas.streaming import TokenChunk

# ---------------------------------------------------------------------------
# TokenChunk
# ---------------------------------------------------------------------------

class TestTokenChunk:
    def test_basic_chunk(self):
        tc = TokenChunk(delta="hello", node="tutor")
        assert tc.delta == "hello"
        assert tc.node == "tutor"
        assert tc.done is False
        assert tc.error is None
        assert tc.status is False

    def test_status_chunk(self):
        tc = TokenChunk(delta="Searching...", node="orchestrator", status=True)
        assert tc.delta == "Searching..."
        assert tc.status is True

    def test_done_chunk(self):
        tc = TokenChunk(delta="", done=True)
        assert tc.done is True

    def test_error_chunk(self):
        tc = TokenChunk(delta="", error="something broke")
        assert tc.error == "something broke"

    def test_json_serialization(self):
        import json

        tc = TokenChunk(delta="Photosynthesis", node="tutor", done=False)
        parsed = json.loads(tc.model_dump_json())
        assert parsed["delta"] == "Photosynthesis"
        assert parsed["node"] == "tutor"
        assert parsed["done"] is False
        assert parsed["error"] is None
        assert parsed["status"] is False

    def test_json_roundtrip(self):
        import json

        tc = TokenChunk(delta="test", node="tutor", done=True, error=None, status=False)
        raw = tc.model_dump_json()
        parsed = json.loads(raw)
        assert parsed["delta"] == "test"
        assert parsed["done"] is True
        assert parsed["error"] is None
        assert parsed["status"] is False

    def test_status_json_roundtrip(self):
        import json

        tc = TokenChunk(delta="Searching...", status=True)
        raw = tc.model_dump_json()
        parsed = json.loads(raw)
        assert parsed["status"] is True


# ---------------------------------------------------------------------------
# LLMProvider chat_stream fallback
# ---------------------------------------------------------------------------

class TestProviderStreamFallback:
    async def test_fallback_to_chat(self):
        """When a provider doesn't override chat_stream, it should fall back to chat()."""

        class SimpleProvider(LLMProvider):
            @property
            def name(self) -> str:
                return "simple"

            async def chat(self, messages, temperature=0.7, max_tokens=2048):
                from src.llm.providers.base import ChatResponse, UsageInfo
                return ChatResponse(content="Hello world", model="simple/test", usage=UsageInfo(), provider="simple")

            async def is_available(self) -> bool:
                return True

            async def get_available_models(self) -> list[str]:
                return ["test"]

            async def check_health(self) -> bool:
                return True

            def get_info(self):
                from src.llm.providers.base import ProviderInfo
                return ProviderInfo(name="simple", provider_type="test", base_url="", available_models=["test"], is_healthy=True)

        provider = SimpleProvider()
        tokens = []
        async for token in provider.chat_stream(messages=[{"role": "user", "content": "hi"}]):
            tokens.append(token)
        assert "".join(tokens) == "Hello world"


# ---------------------------------------------------------------------------
# TutorNode streaming path
# ---------------------------------------------------------------------------

class TestTutorNodeStreaming:
    async def test_legacy_pushes_tokens_to_queue(self, mock_router):
        """TutorNode._legacy_call should push TokenChunks to the queue when present."""
        from src.graph.nodes.tutor import TutorNode

        # Mock route_stream to yield tokens
        async def mock_stream(*args, **kwargs):
            yield "Hello "
            yield "world!"

        mock_router.route_stream = mock_stream

        node = TutorNode(mock_router)
        queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()

        state = AgentState(
            user_message="Say hi",
            grade_level=10,
            token_queue=queue,
        )

        await node(state)

        # Read all chunks from queue
        chunks = []
        while True:
            try:
                chunk = queue.get_nowait()
                chunks.append(chunk)
            except asyncio.QueueEmpty:
                break

        assert len(chunks) >= 2  # at least content + done
        deltas = [c.delta for c in chunks if not c.done and c.error is None]
        assert "".join(deltas) == "Hello world!"

        # Verify done chunk
        done_chunks = [c for c in chunks if c.done]
        assert len(done_chunks) >= 1

        # Verify state is populated
        assert state.draft == "Hello world!"

    async def test_legacy_no_queue_falls_back(self, mock_router):
        """When no token_queue is present, route() is used instead of route_stream()."""
        from src.graph.nodes.tutor import TutorNode

        node = TutorNode(mock_router)
        state = AgentState(user_message="Say hi", grade_level=10)

        await node(state)
        assert state.draft == "Test response"

    async def test_agentic_skips_streaming(self, mock_router):
        """Agentic call path should be used when evidence_items exist and no queue."""
        from src.graph.nodes.tutor import TutorNode

        node = TutorNode(mock_router)
        state = AgentState(
            user_message="Explain photosynthesis",
            evidence_items=[{"id": "1", "content": "Photosynthesis..."}],
            grade_level=10,
        )

        await node(state)

        # Should use route() (agentic path uses the router through TutorSynthesisAgent)
        assert mock_router.route.called


# ---------------------------------------------------------------------------
# route_stream integration
# ---------------------------------------------------------------------------

class TestRouteStream:
    async def test_mock_router_streams(self):
        """ModelRouter.route_stream should yield tokens from the provider chain."""
        from src.llm.manager import ProviderManager
        from src.llm.router import ModelRouter

        mock_provider = AsyncMock(spec=LLMProvider)
        mock_provider.is_available = AsyncMock(return_value=True)
        mock_provider.chat_stream.return_value.__aiter__.return_value = iter(
            ["mock ", "token ", "stream"]
        )

        router = ModelRouter()
        router._manager = ProviderManager()
        router._manager._providers = {"mock_test": mock_provider}
        router._manager._fallback_chain = ["mock_test"]
        tokens = []
        async for token in router.route_stream(
            messages=[{"role": "user", "content": "Say hello in 3 words"}],
            temperature=0.7,
            max_tokens=50,
        ):
            tokens.append(token)

        assert len(tokens) > 0
        assert isinstance(tokens[0], str)
        assert "".join(tokens) == "mock token stream"


# ---------------------------------------------------------------------------
# SSE format validation
# ---------------------------------------------------------------------------

class TestSSEFormat:
    async def test_sse_event_format(self):
        """SSE events should follow the 'data: {...}\\n\\n' format."""
        queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()

        async def _simulate_events(q):
            while True:
                chunk = await q.get()
                if chunk is None:
                    break
                if chunk.error:
                    yield f"data: {chunk.model_dump_json()}\n\n"
                    break
                yield f"data: {chunk.model_dump_json()}\n\n"
                if chunk.done:
                    break

        queue.put_nowait(TokenChunk(delta="Hello", node="tutor"))
        queue.put_nowait(TokenChunk(delta="", node="tutor", done=True))
        queue.put_nowait(None)

        chunks = [c async for c in _simulate_events(queue)]
        assert len(chunks) == 2
        assert chunks[0].startswith("data: ")
        assert chunks[0].endswith("\n\n")
        assert '"delta": "Hello"' in chunks[0]
        assert chunks[1].startswith("data: ") and chunks[1].endswith("\n\n")


# ---------------------------------------------------------------------------
# QuizAgent streaming
# ---------------------------------------------------------------------------

class TestQuizAgentStreaming:
    async def test_quiz_agent_streams_tokens(self, mock_router, monkeypatch):
        """QuizAgent.generate with token_queue pushes tokens via _call_llm_stream."""
        async def mock_stream(*args, **kwargs):
            yield '{"quiz'
            yield '": "test"}'

        monkeypatch.setattr(QuizAgent, "_call_llm_stream", mock_stream)

        agent = QuizAgent(llm_router=mock_router)
        agent.adapter = MagicMock()
        agent.adapter.search = AsyncMock(return_value=[])
        agent.adapter.format_context = MagicMock(return_value="context")

        queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()

        result = await agent.generate(
            grade_level=10,
            topic="Cell Biology",
            question_count=2,
            token_queue=queue,
        )

        # Verify tokens were pushed to the queue
        tokens = []
        while True:
            try:
                chunk = queue.get_nowait()
                tokens.append(chunk)
            except asyncio.QueueEmpty:
                break

        assert len(tokens) >= 2  # content + done
        deltas = [c.delta for c in tokens if not c.done and c.error is None and not c.status]
        assert "".join(deltas) == '{"quiz": "test"}'

        # Verify done chunk
        done_chunks = [c for c in tokens if c.done]
        assert len(done_chunks) == 1

        # Verify result is parsed
        assert result["title"] == "Grade 10 - Cell Biology"


    async def test_quiz_agent_no_queue_falls_back(self, mock_router):
        """QuizAgent.generate without token_queue uses _call_llm."""
        agent = QuizAgent(llm_router=mock_router)
        agent.adapter = MagicMock()
        agent.adapter.search = AsyncMock(return_value=[])
        agent.adapter.format_context = MagicMock(return_value="context")
        result = await agent.generate(
            grade_level=10,
            topic="Cell Biology",
            question_count=2,
        )
        assert result["title"] == "Grade 10 - Cell Biology"


# ---------------------------------------------------------------------------
# DiagnosticAgent streaming
# ---------------------------------------------------------------------------

class TestDiagnosticAgentStreaming:
    async def test_diagnostic_agent_streams_tokens(self, mock_router, monkeypatch):
        """DiagnosticAgent.generate with token_queue pushes tokens via _call_llm_stream."""
        async def mock_stream(*args, **kwargs):
            yield '{"asses'
            yield 'sments": []}'

        monkeypatch.setattr(DiagnosticAgent, "_call_llm_stream", mock_stream)

        agent = DiagnosticAgent(llm_router=mock_router)
        queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()

        result = await agent.generate(
            grade_level=10,
            topics=["Cell Biology"],
            questions_per_topic=2,
            token_queue=queue,
        )

        # Verify tokens were pushed to the queue
        tokens = []
        while True:
            try:
                chunk = queue.get_nowait()
                tokens.append(chunk)
            except asyncio.QueueEmpty:
                break

        assert len(tokens) >= 2  # status + content + done
        deltas = [c.delta for c in tokens if not c.done and c.error is None and not c.status]
        assert "".join(deltas) == '{"assessments": []}'

        # Verify done chunk
        done_chunks = [c for c in tokens if c.done]
        assert len(done_chunks) == 1

        # Verify result is parsed
        assert result["assessments"] == []


    async def test_diagnostic_agent_no_queue_falls_back(self, mock_router):
        """DiagnosticAgent.generate without token_queue uses _call_llm."""
        agent = DiagnosticAgent(llm_router=mock_router)
        result = await agent.generate(
            grade_level=10,
            topics=["Cell Biology"],
            questions_per_topic=2,
        )
        assert result["assessments"] == []
