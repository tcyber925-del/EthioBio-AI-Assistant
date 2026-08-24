"""Regression tests for persisting PipelineMonitor traces to Postgres.

Guards against the production failure where a non-JSON-safe value in
trace.metadata (a raw uuid.UUID from LangSmith's RunTree.id) crashed the
agent_traces INSERT with "Object of type UUID is not JSON serializable",
silently losing every sampled trace.
"""

import json
import uuid

import pytest

from src.core.monitoring import PipelineTrace


class _CapturingRepo:
    def __init__(self):
        self.kwargs = None

    async def save_trace(self, **kwargs):
        self.kwargs = kwargs


@pytest.mark.asyncio
async def test_event_metadata_is_json_serializable_with_uuid_run_id():
    from src.main import _save_trace_from_pipeline

    run_uuid = uuid.uuid4()
    trace = PipelineTrace(
        trace_id="trace_regtest",
        start_time=1000.0,
        end_time=1010.0,
        status="completed",
        nodes_visited=["orchestrator", "tutor"],
        node_timings={"orchestrator": 2500.0, "tutor": 5000.0},
        metadata={
            "user_message": "What is cell theory?",
            "response": "Cell theory states that all living things are made of cells.",
            "langsmith_run_id": run_uuid,
            "grade_level": 8,
            "coverage_score": 0.9,
        },
    )
    repo = _CapturingRepo()

    await _save_trace_from_pipeline(trace, repo)

    assert repo.kwargs is not None
    metadata = repo.kwargs["metadata"]
    json.dumps(metadata)  # must not raise
    assert metadata["langsmith_run_id"] == str(run_uuid)


@pytest.mark.asyncio
async def test_user_message_and_response_excluded_from_event_metadata():
    from src.main import _save_trace_from_pipeline

    trace = PipelineTrace(
        trace_id="trace_regtest2",
        start_time=1000.0,
        end_time=1011.0,
        status="completed",
        metadata={
            "user_message": "q",
            "response": "a",
            "intent": "tutor",
        },
    )
    repo = _CapturingRepo()

    await _save_trace_from_pipeline(trace, repo)

    metadata = repo.kwargs["metadata"]
    assert "user_message" not in metadata
    assert "response" not in metadata
    assert metadata["intent"] == "tutor"
