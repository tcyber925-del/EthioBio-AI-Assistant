"""Monitoring, observability, and metrics for Agentic RAG pipeline.

Provides trace_id generation, performance metrics, pipeline tracing,
and aggregated health metrics for the observability endpoint.

5 key metrics (PRD-009):
1. Pipeline completion rate
2. Average iterations per query
3. Coverage score distribution
4. Claim groundedness rate
5. Teacher review flag rate
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger()

METRICS_WINDOW_SECONDS = 3600  # 1-hour rolling window


@dataclass
class PipelineTrace:
    """Trace for a single pipeline execution."""

    trace_id: str
    start_time: float
    end_time: Optional[float] = None
    nodes_visited: list[str] = field(default_factory=list)
    node_timings: dict[str, float] = field(default_factory=dict)
    status: str = "running"
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Total duration in milliseconds."""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def start_node(self, node_name: str) -> None:
        """Mark start of a node execution."""
        self.nodes_visited.append(node_name)
        self.node_timings[f"{node_name}_start"] = time.time()

    def end_node(self, node_name: str) -> float:
        """Mark end of a node execution. Returns duration in ms."""
        start_key = f"{node_name}_start"
        if start_key in self.node_timings:
            start = self.node_timings.pop(start_key)
            duration = (time.time() - start) * 1000
            self.node_timings[node_name] = duration
            return duration
        return 0.0

    def finish(self, status: str = "completed", error: Optional[str] = None) -> None:
        """Mark trace as finished."""
        self.end_time = time.time()
        self.status = status
        self.error = error

    def to_dict(self) -> dict:
        """Convert trace to dictionary for logging."""
        return {
            "trace_id": self.trace_id,
            "duration_ms": self.duration_ms,
            "nodes_visited": self.nodes_visited,
            "node_timings": {
                k: v for k, v in self.node_timings.items() if not k.endswith("_start")
            },
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class PipelineMetrics:
    """Aggregated metrics for the agentic RAG pipeline.

    Rolling window of the last METRICS_WINDOW_SECONDS.
    """

    total_traces: int = 0
    completed_traces: int = 0
    failed_traces: int = 0
    running_traces: int = 0

    # Metric 1: Pipeline health
    completion_rate: float = 0.0
    avg_duration_ms: float = 0.0

    # Metric 2: Retrieval efficiency
    avg_iterations: float = 0.0
    total_iterations: int = 0

    # Metric 3: Coverage quality
    avg_coverage_score: float = 0.0
    coverage_scores: list[float] = field(default_factory=list)

    # Metric 4: Claim groundedness
    avg_groundedness: float = 0.0
    avg_hallucination_rate: float = 0.0
    revision_rate: float = 0.0
    rejection_rate: float = 0.0

    # Metric 5: Teacher review
    teacher_review_rate: float = 0.0
    total_teacher_reviews: int = 0

    # Node-level timing
    avg_node_duration_ms: dict[str, float] = field(default_factory=dict)


class PipelineMonitor:
    """Monitors Agentic RAG pipeline execution.

    Tracks individual traces and aggregates rolling metrics.
    """

    def __init__(self):
        self.traces: dict[str, PipelineTrace] = {}
        self._metrics_interval = METRICS_WINDOW_SECONDS

    def start_trace(self, metadata: Optional[dict] = None) -> PipelineTrace:
        """Start a new trace."""
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        trace = PipelineTrace(
            trace_id=trace_id,
            start_time=time.time(),
            metadata=metadata or {},
        )
        self.traces[trace_id] = trace
        return trace

    def get_trace(self, trace_id: str) -> Optional[PipelineTrace]:
        """Get a trace by ID."""
        return self.traces.get(trace_id)

    def list_traces(self, limit: int = 50) -> list[dict]:
        """List recent traces, newest first."""
        sorted_traces = sorted(
            self.traces.values(),
            key=lambda t: t.start_time,
            reverse=True,
        )
        return [t.to_dict() for t in sorted_traces[:limit]]

    def log_trace(self, trace: PipelineTrace) -> None:
        """Log trace completion."""
        logger.info(
            "pipeline_trace",
            trace_id=trace.trace_id,
            duration_ms=trace.duration_ms,
            nodes=trace.nodes_visited,
            status=trace.status,
        )

    def get_metrics(self) -> PipelineMetrics:
        """Compute rolling metrics from recent traces.

        Returns aggregated metrics for the last METRICS_WINDOW_SECONDS.
        """
        cutoff = time.time() - self._metrics_interval
        recent = [
            t for t in self.traces.values()
            if t.start_time >= cutoff
        ]

        if not recent:
            return PipelineMetrics()

        completed = [t for t in recent if t.status == "completed"]
        failed = [t for t in recent if t.status == "failed"]
        running = [t for t in recent if t.status == "running"]

        total = len(recent)

        # Metric 1: Pipeline health
        completion_rate = len(completed) / max(total, 1)
        avg_duration = (
            sum(t.duration_ms for t in completed) / max(len(completed), 1)
        )

        # Metric 2: Iterations
        iterations_total = sum(
            t.metadata.get("retrieval_iterations", 0) for t in completed
        )
        avg_iterations = iterations_total / max(len(completed), 1)

        # Metric 3: Coverage scores
        coverage_scores = [
            t.metadata.get("coverage_score", 0.0)
            for t in completed
            if "coverage_score" in t.metadata
        ]
        avg_coverage = (
            sum(coverage_scores) / max(len(coverage_scores), 1)
            if coverage_scores else 0.0
        )

        # Metric 4: Claim groundedness
        groundedness_scores = [
            t.metadata.get("groundedness", 0.0)
            for t in completed
            if "groundedness" in t.metadata
        ]
        avg_groundedness = (
            sum(groundedness_scores) / max(len(groundedness_scores), 1)
            if groundedness_scores else 0.0
        )

        hallucination_rates = [
            t.metadata.get("hallucination_rate", 0.0)
            for t in completed
            if "hallucination_rate" in t.metadata
        ]
        avg_hallucination_rate = (
            sum(hallucination_rates) / max(len(hallucination_rates), 1)
            if hallucination_rates else 0.0
        )

        revisions = sum(
            1 for t in completed
            if t.metadata.get("verdict") == "revise"
        )
        rejections = sum(
            1 for t in completed
            if t.metadata.get("verdict") == "reject"
        )
        revision_rate = revisions / max(len(completed), 1)
        rejection_rate = rejections / max(len(completed), 1)

        # Metric 5: Teacher review
        teacher_reviews = sum(
            1 for t in completed
            if t.metadata.get("requires_teacher_review", False)
        )
        teacher_review_rate = teacher_reviews / max(len(completed), 1)

        # Node-level timing
        node_durations: dict[str, list[float]] = {}
        for t in recent:
            for node, duration in t.node_timings.items():
                if not node.endswith("_start"):
                    node_durations.setdefault(node, []).append(duration)

        avg_node_duration = {
            node: sum(durs) / len(durs)
            for node, durs in node_durations.items()
        }

        return PipelineMetrics(
            total_traces=total,
            completed_traces=len(completed),
            failed_traces=len(failed),
            running_traces=len(running),
            completion_rate=round(completion_rate, 3),
            avg_duration_ms=round(avg_duration, 1),
            avg_iterations=round(avg_iterations, 2),
            total_iterations=iterations_total,
            avg_coverage_score=round(avg_coverage, 3),
            coverage_scores=coverage_scores,
            avg_groundedness=round(avg_groundedness, 3),
            avg_hallucination_rate=round(avg_hallucination_rate, 3),
            revision_rate=round(revision_rate, 3),
            rejection_rate=round(rejection_rate, 3),
            teacher_review_rate=round(teacher_review_rate, 3),
            total_teacher_reviews=teacher_reviews,
            avg_node_duration_ms={
                k: round(v, 1) for k, v in sorted(
                    avg_node_duration.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            },
        )

    def cleanup_old_traces(self, max_age_seconds: int = 3600) -> int:
        """Remove traces older than max_age_seconds."""
        cutoff = time.time() - max_age_seconds
        to_remove = [
            tid
            for tid, t in self.traces.items()
            if t.start_time < cutoff
        ]
        for tid in to_remove:
            del self.traces[tid]
        return len(to_remove)


# Global monitor instance
pipeline_monitor = PipelineMonitor()


def generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return f"trace_{uuid.uuid4().hex[:12]}"
