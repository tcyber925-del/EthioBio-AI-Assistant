import os

import structlog

from src.config import settings
from src.retrieval.bm25 import DEFAULT_INDEX_PATH

logger = structlog.get_logger()


async def run_startup_checks() -> list[str]:
    warnings: list[str] = []

    if settings.jwt_secret in ("change-me-jwt-secret", "dev-jwt-secret"):
        raise SystemExit(
            "FATAL: JWT_SECRET is set to a default value. "
            "Generate a strong secret: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )

    if settings.secret_key in ("change-me", "dev-secret-key-change-in-production"):
        raise SystemExit(
            "FATAL: SECRET_KEY is set to a default value. "
            "Generate a strong secret: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )

    if settings.telegram_webhook_url and not settings.telegram_webhook_secret:
        warnings.append("TELEGRAM_WEBHOOK_URL is set but TELEGRAM_WEBHOOK_SECRET is empty")

    allow_wildcard = "*" in getattr(settings, "dashboard_url", "") or "*" in getattr(
        settings, "dashboard_url", ""
    )
    if allow_wildcard:
        warnings.append("CORS allows wildcard origin (*) — restrict in production")

    if not os.path.exists(DEFAULT_INDEX_PATH):
        logger.info("bm25_index_not_found_will_build_lazy")
    else:
        logger.info("bm25_index_exists_skipping_build")

    for w in warnings:
        logger.warning("startup_check_failed", check=w)

    if not warnings:
        logger.info("startup_checks_passed")

    return warnings
