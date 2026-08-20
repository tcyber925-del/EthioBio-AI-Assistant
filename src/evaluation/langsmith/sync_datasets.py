"""Upsert benchmark scenarios and the gold set into LangSmith datasets.

The LangGraph agent's live traces are captured automatically; this module
creates the offline evaluation datasets the ``evaluate``/``aevaluate``
experiments run against.
"""

import json
import uuid
from pathlib import Path
from typing import Optional

import structlog
import yaml

from src.observability.langsmith import get_client

logger = structlog.get_logger()

BASE_DIR = Path(__file__).resolve().parents[3]  # repo root
SCENARIOS_DIR = BASE_DIR / "src" / "evaluation" / "benchmark" / "scenarios"
GOLD_SET_PATH = BASE_DIR / "data" / "evaluation" / "gold_set.json"

DATASETS = [
    {
        "name": "ethiobio-curriculum",
        "description": "Grade 8 biology curriculum questions from the Ethiopian curriculum",
        "source": "scenarios",
        "tag": "curriculum",
    },
    {
        "name": "ethiobio-adversarial",
        "description": "Adversarial edge cases to stress-test pipeline behavior",
        "source": "scenarios",
        "tag": "adversarial",
    },
    {
        "name": "ethiobio-gold",
        "description": "Gold QA pairs from data/evaluation/gold_set.json",
        "source": "gold_set",
    },
]


def _stable_id(prefix: str, key: str) -> str:
    """Deterministic example id so re-syncing upserts instead of duplicating."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ethiobio:{prefix}:{key}"))


def _load_scenarios() -> list[dict]:
    scenarios: list[dict] = []
    for f in sorted(SCENARIOS_DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        for s in data.get("scenarios", []):
            s.setdefault("grade_level", data.get("grade_level", 8))
            s.setdefault("language", data.get("language", "en"))
            scenarios.append(s)
    return scenarios


def _load_gold_set() -> list[dict]:
    if not GOLD_SET_PATH.exists():
        return []
    return json.loads(GOLD_SET_PATH.read_text())


def _examples_for(spec: dict, client) -> tuple[str, list[dict]]:
    dataset = client.create_dataset(spec["name"], description=spec["description"])
    if spec["source"] == "gold_set":
        items = _load_gold_set()
        examples = [
            {
                "id": _stable_id("gold", item["id"]),
                "inputs": {
                    "question": item["question"],
                    "grade_level": item.get("grade_level"),
                    "language": item.get("language", "en"),
                },
                "outputs": {
                    "expected_answer": item["expected_answer"],
                    "topic": item.get("topic", ""),
                    "type": item.get("type", "tutor"),
                },
            }
            for item in items
        ]
    else:
        items = [s for s in _load_scenarios() if spec["tag"] in s.get("tags", [])]
        examples = [
            {
                "id": _stable_id(spec["name"], s["id"]),
                "inputs": {
                    "question": s["question"],
                    "grade_level": s.get("grade_level", 8),
                    "language": s.get("language", "en"),
                },
                "outputs": {"expected_topics": s.get("expected_topics", [])},
            }
            for s in items
        ]
    return dataset.id, examples


def sync_datasets_to_langsmith(client: Optional[object] = None) -> dict[str, int]:
    """Create/refresh all LangSmith datasets. Returns {dataset_name: example_count}."""
    client = client or get_client()
    if client is None:
        raise RuntimeError("LangSmith client unavailable — set LANGSMITH_API_KEY")

    counts: dict[str, int] = {}
    for spec in DATASETS:
        dataset_id, examples = _examples_for(spec, client)
        if not examples:
            logger.warning("langsmith_dataset_empty", dataset=spec["name"])
            continue
        client.create_examples(dataset_id=dataset_id, examples=examples)
        counts[spec["name"]] = len(examples)
        logger.info("langsmith_dataset_synced", dataset=spec["name"], examples=len(examples))
    return counts


def sync_all() -> dict[str, int]:
    """Sync all datasets from the CLI entrypoint."""
    import asyncio

    return asyncio.run(sync_datasets_to_langsmith())


if __name__ == "__main__":
    import asyncio

    asyncio.run(sync_datasets_to_langsmith())
