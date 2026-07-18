import asyncio
from pathlib import Path

from src.config import settings
from src.llm.router import ModelRouter
from src.observability.evaluation.dimensions import DIMENSIONS
from src.observability.evaluation.judge import LLMJudge


def load_dataset(path: Path) -> list[dict]:
    cases: list[dict] = []
    if not path.exists():
        return cases
    for line in path.read_text().strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|||")
        if len(parts) >= 3:
            cases.append(
                {
                    "label": parts[0].strip(),
                    "query": parts[1].strip(),
                    "response": parts[2].strip(),
                    "context": parts[3].strip() if len(parts) > 3 else "",
                }
            )
    return cases


async def run_evals(dataset_path: Path | None = None) -> dict:
    router = ModelRouter(preferred_model=settings.eval_judge_model)
    judge = LLMJudge(router=router)
    results: dict[str, list[float]] = {}

    base = dataset_path or Path(__file__).parent / "datasets"
    for dim in DIMENSIONS:
        path = base / f"{dim.name}_cases.txt"
        cases = load_dataset(path)
        if not cases:
            continue
        scores: list[float] = []
        for case in cases:
            ctx = case.get("context", "")
            result = await judge.score(dim, case["query"], case["response"], ctx)
            scores.append(result["score"])
        results[dim.name] = scores

    await router.close()
    return results


def compute_averages(results: dict[str, list[float]]) -> dict[str, float]:
    return {dim: (sum(scores) / len(scores)) if scores else 0.0 for dim, scores in results.items()}


async def main() -> int:
    results = await run_evals()
    avgs = compute_averages(results)
    overall = sum(avgs.values()) / len(avgs) if avgs else 0.0

    print("=== Evaluation Results ===")
    for dim, avg in sorted(avgs.items()):
        print(f"  {dim}: {avg:.3f}")
    print(f"  overall: {overall:.3f}")

    return 0 if overall >= 0.7 else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
