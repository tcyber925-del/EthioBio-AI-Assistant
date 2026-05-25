"""Auto-generate ground truth labels from textbook diagrams using vision LLMs.

Usage:
    python scripts/label_textbook_diagrams.py
    python scripts/label_textbook_diagrams.py --grade 10
    python scripts/label_textbook_diagrams.py --model openrouter/anthropic/claude-3.5-sonnet
    python scripts/label_textbook_diagrams.py --dry-run
"""

import base64
import json
from io import BytesIO

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
