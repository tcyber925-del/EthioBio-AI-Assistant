"""CLI to run LangSmith offline evaluation experiments.

Usage:
    ethiobio-langsmith --dataset ethiobio-curriculum --evaluators all
    ethiobio-langsmith --dataset ethiobio-gold --evaluators faithfulness,relevance --limit 3

Exits non-zero when any evaluator's average score falls below --threshold
(regression gate for CI / nightly runs).
"""

import argparse
import asyncio
import os
from typing import Optional

import structlog

from src.config import settings

logger = structlog.get_logger()


async def run_evaluation(
    dataset: str,
    evaluators: Optional[list[str]] = None,
    max_concurrency: int = 4,
    limit: Optional[int] = None,
) -> dict[str, float]:
    """Run an async evaluation over a LangSmith dataset and return avg scores."""
    from langsmith import Client, aevaluate

    from src.evaluation.langsmith.eval_target import eval_target
    from src.evaluation.langsmith.evaluators import (
        default_evaluators,
        llm_judge_evaluator,
        topic_coverage_evaluator,
    )

    if not os.environ.get("LANGSMITH_API_KEY"):
        from src.observability.langsmith import get_client

        get_client()  # configures env from settings

    client = Client()
    examples = list(client.list_examples(dataset_name=dataset))
    if limit:
        examples = examples[:limit]
    if not examples:
        logger.error("langsmith_dataset_empty", dataset=dataset)
        return {}

    evals: list = []
    for name in evaluators or ["all"]:
        if name == "all":
            evals.extend(default_evaluators())
        elif name == "topic_coverage":
            evals.append(topic_coverage_evaluator)
        else:
            from src.observability.evaluation.dimensions import DIMENSIONS

            dim = next((d for d in DIMENSIONS if d.name == name), None)
            if dim is None:
                raise ValueError(f"Unknown evaluator: {name}")
            evals.append(llm_judge_evaluator(dim))

    results = await aevaluate(
        eval_target,
        data=examples,
        evaluators=evals,
        max_concurrency=max_concurrency,
    )

    scores: dict[str, list[float]] = {}
    async for res in results:
        for er in res.evaluation_results:
            scores.setdefault(er.key, []).append(float(er.score))
    return {key: round(sum(v) / len(v), 3) for key, v in scores.items()}


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run LangSmith agent evaluation")
    parser.add_argument("--dataset", default="ethiobio-curriculum")
    parser.add_argument("--evaluators", default="all", help="comma-separated names or 'all'")
    parser.add_argument("--max-concurrency", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=0.7)
    args = parser.parse_args()

    settings.langsmith_tracing_enabled = True
    settings.langsmith_sampling_rate = 1.0
    os.environ["LANGSMITH_TRACING"] = "true"

    evals = [e.strip() for e in args.evaluators.split(",") if e.strip()]
    avgs = await run_evaluation(
        dataset=args.dataset,
        evaluators=evals,
        max_concurrency=args.max_concurrency,
        limit=args.limit,
    )

    if not avgs:
        logger.error("langsmith_eval_no_results", dataset=args.dataset)
        return 1

    print("=== LangSmith Evaluation Results ===")
    failed = []
    for key in sorted(avgs):
        flag = "" if avgs[key] >= args.threshold else "  <-- FAIL"
        print(f"  {key}: {avgs[key]:.3f}{flag}")
        if avgs[key] < args.threshold:
            failed.append(key)

    return 1 if failed else 0


def main() -> int:
    """Sync entrypoint for the ethiobio-langsmith console script."""
    return asyncio.run(_main())


if __name__ == "__main__":
    exit(main())
