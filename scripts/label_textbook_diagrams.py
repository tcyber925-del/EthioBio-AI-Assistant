"""Auto-generate ground truth labels from textbook diagrams using vision LLMs.

Usage:
    python scripts/label_textbook_diagrams.py
    python scripts/label_textbook_diagrams.py --grade 10
    python scripts/label_textbook_diagrams.py --model openrouter/anthropic/claude-3.5-sonnet
    python scripts/label_textbook_diagrams.py --dry-run
"""

import argparse
import asyncio
import base64
import glob
import json
import sys
from io import BytesIO
from typing import cast

import structlog
from PIL import Image as PILImage

from src.llm.router import ModelRouter

structlog.configure(
    processors=[structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger()

DIAGRAMS_BASE = "data/diagrams"
VISION_MODELS = [
    "openrouter/openai/gpt-4o",
    "openrouter/anthropic/claude-3.5-sonnet",
    "ollama/llava",
]

SYSTEM_PROMPT = (
    "You are a biology diagram analyzer. "
    "Identify each labeled structure in this textbook diagram."
)


def _build_vision_messages(base64_image: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "List all labeled structures in this diagram as JSON: "
                        "[{id: string, text: string, x: number, y: number}]. "
                        "Use the label numbers/letters as 'id', the label text as 'text', "
                        "and estimate the x,y position as fractions of diagram "
                        "width/height (0-1). "
                        "Include ALL visible labels. "
                        "Return ONLY the JSON array, no other text."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                    },
                },
            ],
        },
    ]


def _parse_labels_from_response(content: str) -> list[dict]:
    if not content or not content.strip():
        return []
    try:
        labels = json.loads(content)
        if isinstance(labels, list):
            return labels
        return []
    except (json.JSONDecodeError, TypeError):
        return []


async def _try_model_with_fallback(
    router: ModelRouter,
    messages: list[dict],
    preferred_model: str | None = None,
) -> tuple[list[dict], str | None]:
    models_to_try = []
    if preferred_model:
        models_to_try.append(preferred_model)
    models_to_try.extend(m for m in VISION_MODELS if m != preferred_model)

    for model in models_to_try:
        try:
            result = await router.route(
                messages,
                request_type="vision",
                temperature=0.1,
                max_tokens=2048,
                preferred_model=model,
            )
            content = result.get("content", "")
            labels = _parse_labels_from_response(content)
            if labels:
                return labels, result.get("model", model)
            logger.warning("vision_empty_response", model=model)
        except Exception:
            logger.warning("vision_model_failed", model=model, exc_info=True)

    return [], None


def _encode_image(image_path: str) -> str | None:
    try:
        img: PILImage.Image = PILImage.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((2048, 2048))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        logger.warning("image_encode_failed", path=image_path, exc_info=True)
        return None


async def label_diagram(
    image_path: str,
    grade: int,
    router: ModelRouter | None = None,
    preferred_model: str | None = None,
    dry_run: bool = False,
) -> dict | None:
    """Label a single diagram image using vision LLM.

    Returns dict with labels info, or None if image couldn't be processed.
    """
    b64 = _encode_image(image_path)
    if b64 is None:
        return None

    messages = _build_vision_messages(b64)
    close_router = router is None
    r: ModelRouter
    if close_router:
        r = ModelRouter()
    else:
        r = cast(ModelRouter, router)

    try:
        labels, model_used = await _try_model_with_fallback(r, messages, preferred_model)

        result = {
            "image_path": image_path,
            "labels": labels,
            "model_used": model_used,
            "label_count": len(labels),
        }

        if labels and not dry_run:
            ground_truth = {
                "labels": labels,
                "proposed": True,
                "human_reviewed": False,
                "model_used": model_used or "",
            }
            logger.info(
                "labels_generated",
                path=image_path,
                count=len(labels),
                model=model_used,
                ground_truth=ground_truth,
            )

        return result
    finally:
        if close_router:
            await r.close()


def _parse_metadata_from_path(image_path: str) -> dict:
    parts = image_path.split("/")
    grade = int(parts[2])
    stem = image_path.split("/")[-1].split(".")[0]
    fig_num = int(stem.split("_")[-1])
    return {"grade": grade, "fig_num": fig_num}


async def main_async():
    parser = _build_parser()
    args = parser.parse_args()

    pattern = f"{DIAGRAMS_BASE}/**/*.jpg"
    image_paths = sorted(glob.glob(pattern, recursive=True))

    if not image_paths:
        logger.info("no_diagrams_found")
        return 0

    total_labels = 0
    processed = 0
    skipped = 0

    for img_path_str in image_paths:
        meta = _parse_metadata_from_path(img_path_str)

        if args.grade and meta["grade"] != args.grade:
            continue

        if args.dry_run:
            logger.info("dry_run_found", path=img_path_str, **meta)
            processed += 1
            continue

        router = ModelRouter()
        try:
            result = await label_diagram(
                image_path=img_path_str,
                grade=meta["grade"],
                router=router,
                preferred_model=args.model,
            )
            if result and result["labels"]:
                total_labels += result["label_count"]
                processed += 1
                logger.info(
                    "labeled",
                    path=img_path_str,
                    label_count=result["label_count"],
                    model=result["model_used"],
                )
            else:
                skipped += 1
                logger.warning("no_labels", path=img_path_str)
        except Exception:
            skipped += 1
            logger.exception("label_error", path=img_path_str)
        finally:
            await router.close()

    logger.info(
        "labeling_complete",
        total_found=len(image_paths),
        processed=processed,
        skipped=skipped,
        total_labels=total_labels,
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Auto-generate ground truth labels from textbook diagrams using vision LLMs"
    )
    parser.add_argument(
        "--grade", type=int, choices=range(7, 13),
        help="Single grade to process",
    )
    parser.add_argument(
        "--model", type=str,
        help="Override primary vision model (e.g. openrouter/openai/gpt-4o)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Scan and log without calling LLMs or DB",
    )
    return parser


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
