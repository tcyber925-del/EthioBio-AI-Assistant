import os

import structlog

from src.config import settings
from src.retrieval.adapter import VectorStoreAdapter
from src.retrieval.bm25 import DEFAULT_INDEX_PATH

logger = structlog.get_logger()


async def run_startup_checks() -> list[str]:
    warnings: list[str] = []

    if settings.jwt_secret in ("change-me-jwt-secret", "dev-jwt-secret"):
        warnings.append("JWT_SECRET is set to a default/development value — change in production")

    if settings.secret_key in ("change-me", "dev-secret-key-change-in-production"):
        warnings.append("SECRET_KEY is set to a default/development value — change in production")

    if settings.telegram_webhook_url and not settings.telegram_webhook_secret:
        warnings.append("TELEGRAM_WEBHOOK_URL is set but TELEGRAM_WEBHOOK_SECRET is empty")

    allow_wildcard = "*" in getattr(settings, "dashboard_url", "") or "*" in getattr(
        settings, "dashboard_url", ""
    )
    if allow_wildcard:
        warnings.append("CORS allows wildcard origin (*) — restrict in production")

    if not os.path.exists(DEFAULT_INDEX_PATH):
        logger.info("bm25_index_not_found_building")
        try:
            adapter = VectorStoreAdapter()
            await adapter.build_bm25_index()
            logger.info("bm25_index_built_at_startup")
        except Exception:
            logger.exception("bm25_index_build_failed_at_startup")
            warnings.append("BM25 index build failed — hybrid search falls back to dense-only")
    else:
        logger.info("bm25_index_exists_skipping_build")

    for w in warnings:
        logger.warning("startup_check_failed", check=w)

    if not warnings:
        logger.info("startup_checks_passed")

    return warnings
