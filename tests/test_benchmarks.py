"""Performance benchmarks for Agentic RAG pipeline.

Measures node execution times, memory usage, and throughput.
"""

import statistics
import time
from dataclasses import dataclass, field


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""

    name: str
    iterations: int
    durations: list[float] = field(default_factory=list)
    memory_usage: list[float] = field(default_factory=list)

    @property
    def mean_duration_ms(self) -> float:
        """Mean duration in milliseconds."""
        return statistics.mean(self.durations) * 1000 if self.durations else 0.0

    @property
    def median_duration_ms(self) -> float:
        """Median duration in milliseconds."""
        return statistics.median(self.durations) * 1000 if self.durations else 0.0

    @property
    def p95_duration_ms(self) -> float:
        """95th percentile duration in milliseconds."""
        if not self.durations:
            return 0.0
        sorted_durations = sorted(self.durations)
        idx = int(len(sorted_durations) * 0.95)
        return sorted_durations[idx] * 1000

    @property
    def min_duration_ms(self) -> float:
        """Minimum duration in milliseconds."""
        return min(self.durations) * 1000 if self.durations else 0.0

    @property
    def max_duration_ms(self) -> float:
        """Maximum duration in milliseconds."""
        return max(self.durations) * 1000 if self.durations else 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "iterations": self.iterations,
            "mean_ms": round(self.mean_duration_ms, 2),
            "median_ms": round(self.median_duration_ms, 2),
            "p95_ms": round(self.p95_duration_ms, 2),
            "min_ms": round(self.min_duration_ms, 2),
            "max_ms": round(self.max_duration_ms, 2),
        }


class BenchmarkSuite:
    """Suite of performance benchmarks."""

    def __init__(self):
        self.results: list[BenchmarkResult] = []

    def run(self, name: str, func, iterations: int = 100) -> BenchmarkResult:
        """Run a benchmark."""
        result = BenchmarkResult(name=name, iterations=iterations)

        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            result.durations.append(end - start)

        self.results.append(result)
        return result

    def run_async(self, name: str, func, iterations: int = 50) -> BenchmarkResult:
        """Run an async benchmark."""
        import asyncio

        result = BenchmarkResult(name=name, iterations=iterations)

        async def _run():
            for _ in range(iterations):
                start = time.perf_counter()
                await func()
                end = time.perf_counter()
                result.durations.append(end - start)

        asyncio.run(_run())
        self.results.append(result)
        return result

    def summary(self) -> dict:
        """Get summary of all benchmarks."""
        return {
            "benchmarks": [r.to_dict() for r in self.results],
            "total_benchmarks": len(self.results),
        }


# ─── Node Benchmarks ──────────────────────────────────────────────────


def benchmark_sufficient_context():
    """Benchmark SufficientContextNode evaluation."""
    from src.graph.nodes.sufficient_context import evaluate_sufficiency
    from src.graph.state import AgentState

    state = AgentState(user_message="test")
    state.evidence_ids = ["id1", "id2", "id3"]
    state.coverage_score = 0.8
    state.missing_information = []

    evaluate_sufficiency(state)


def benchmark_claim_extraction():
    """Benchmark claim extraction."""
    from src.graph.nodes.claim_verifier import extract_claims_simple

    response = (
        "DNA is a double helix structure composed of nucleotides. "
        "It contains four bases: adenine, thymine, guanine, and cytosine. "
        "The two strands are held together by hydrogen bonds. "
        "DNA replication occurs during the S phase of the cell cycle. "
        "Each nucleotide consists of a sugar, phosphate group, and base."
    )

    extract_claims_simple(response)


def benchmark_query_expansion():
    """Benchmark query expansion."""
    from unittest.mock import MagicMock

    from src.agents.query_rewriter.query_rewriter import QueryRewriterAgent

    agent = QueryRewriterAgent(MagicMock())
    agent._build_fallback("What is photosynthesis and how does it work?")


def benchmark_groundedness_calculation():
    """Benchmark groundedness calculation."""
    from src.graph.nodes.claim_verifier import Claim, calculate_groundedness

    claims = [
        Claim(text=f"claim_{i}", claim_type="fact", is_grounded=i % 2 == 0)
        for i in range(10)
    ]

    calculate_groundedness(claims)


def benchmark_chunk_deduplication():
    """Benchmark chunk deduplication."""
    from src.graph.nodes.search_fanout import IndexResult, deduplicate_chunks

    results = [
        IndexResult(
            index_name="curriculum",
            query="test",
            chunks=[
                {"content": f"content_{i}", "metadata": {}, "score": 0.8 - i * 0.1}
                for i in range(10)
            ],
            score=0.7,
        )
        for _ in range(3)
    ]

    deduplicate_chunks(results)


def benchmark_chunk_ranking():
    """Benchmark chunk ranking."""
    from src.graph.nodes.search_fanout import rank_chunks

    chunks = [
        {"content": f"content_{i}", "score": 0.9 - i * 0.05}
        for i in range(20)
    ]

    rank_chunks(chunks, max_results=10)


# ─── Model Benchmarks ─────────────────────────────────────────────────


def benchmark_plan_model_creation():
    """Benchmark Plan model creation."""
    from src.agents.planner.models import Plan, ReasoningType, SubTask

    plan = Plan(
        objective="Test objective",
        reasoning_type=ReasoningType.MULTI_HOP,
        subtasks=[
            SubTask(
                id=f"task_{i}",
                type="curriculum",
                objective=f"Objective {i}",
                retrieval_sources=["curriculum"],
            )
            for i in range(3)
        ],
    )

    assert plan.objective == "Test objective"


def benchmark_evidence_model_creation():
    """Benchmark Evidence model creation."""
    from src.core.evidence.graph import Evidence

    for i in range(10):
        Evidence(
            id=f"evidence_{i}",
            source_type="curriculum",
            source_name="Grade 9 Biology",
            chunk_id=f"chunk_{i}",
            content=f"Content {i}",
            original_query="test query",
            retrieval_query="test retrieval",
            retrieval_score=0.8,
            rerank_score=0.9,
            confidence=0.85,
            retrieved_by="search_fanout",
        )


# ─── Benchmark Tests ──────────────────────────────────────────────────


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_sufficient_context_benchmark(self):
        """Benchmark SufficientContextNode."""
        suite = BenchmarkSuite()
        result = suite.run("sufficient_context", benchmark_sufficient_context, iterations=1000)

        assert result.mean_duration_ms < 1.0  # Should be < 1ms
        print(f"SufficientContext: mean={result.mean_duration_ms:.3f}ms")

    def test_claim_extraction_benchmark(self):
        """Benchmark claim extraction."""
        suite = BenchmarkSuite()
        result = suite.run("claim_extraction", benchmark_claim_extraction, iterations=1000)

        assert result.mean_duration_ms < 1.0
        print(f"ClaimExtraction: mean={result.mean_duration_ms:.3f}ms")

    def test_query_expansion_benchmark(self):
        """Benchmark query expansion."""
        suite = BenchmarkSuite()
        result = suite.run("query_expansion", benchmark_query_expansion, iterations=1000)

        assert result.mean_duration_ms < 1.0
        print(f"QueryExpansion: mean={result.mean_duration_ms:.3f}ms")

    def test_groundedness_benchmark(self):
        """Benchmark groundedness calculation."""
        suite = BenchmarkSuite()
        result = suite.run(
            "groundedness_calculation", benchmark_groundedness_calculation, iterations=1000
        )

        assert result.mean_duration_ms < 1.0
        print(f"Groundedness: mean={result.mean_duration_ms:.3f}ms")

    def test_chunk_deduplication_benchmark(self):
        """Benchmark chunk deduplication."""
        suite = BenchmarkSuite()
        result = suite.run(
            "chunk_deduplication", benchmark_chunk_deduplication, iterations=1000
        )

        assert result.mean_duration_ms < 5.0
        print(f"ChunkDedup: mean={result.mean_duration_ms:.3f}ms")

    def test_chunk_ranking_benchmark(self):
        """Benchmark chunk ranking."""
        suite = BenchmarkSuite()
        result = suite.run("chunk_ranking", benchmark_chunk_ranking, iterations=1000)

        assert result.mean_duration_ms < 5.0
        print(f"ChunkRanking: mean={result.mean_duration_ms:.3f}ms")

    def test_plan_model_benchmark(self):
        """Benchmark Plan model creation."""
        suite = BenchmarkSuite()
        result = suite.run("plan_model", benchmark_plan_model_creation, iterations=1000)

        assert result.mean_duration_ms < 1.0
        print(f"PlanModel: mean={result.mean_duration_ms:.3f}ms")

    def test_evidence_model_benchmark(self):
        """Benchmark Evidence model creation."""
        suite = BenchmarkSuite()
        result = suite.run("evidence_model", benchmark_evidence_model_creation, iterations=1000)

        assert result.mean_duration_ms < 5.0
        print(f"EvidenceModel: mean={result.mean_duration_ms:.3f}ms")

    def test_full_benchmark_suite(self):
        """Run full benchmark suite and generate report."""
        suite = BenchmarkSuite()

        suite.run("sufficient_context", benchmark_sufficient_context, iterations=500)
        suite.run("claim_extraction", benchmark_claim_extraction, iterations=500)
        suite.run("query_expansion", benchmark_query_expansion, iterations=500)
        suite.run("groundedness", benchmark_groundedness_calculation, iterations=500)
        suite.run("chunk_dedup", benchmark_chunk_deduplication, iterations=500)
        suite.run("chunk_ranking", benchmark_chunk_ranking, iterations=500)

        summary = suite.summary()

        print("\n=== Benchmark Summary ===")
        for bench in summary["benchmarks"]:
            print(
                f"{bench['name']}: mean={bench['mean_ms']:.3f}ms, "
                f"p95={bench['p95_ms']:.3f}ms"
            )

        assert summary["total_benchmarks"] == 6
