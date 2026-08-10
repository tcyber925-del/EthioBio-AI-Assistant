import os

import httpx
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

    if not settings.telegram_bot_token:
        warnings.append("TELEGRAM_BOT_TOKEN is empty — bot will not start")

    allow_wildcard = "*" in getattr(settings, "dashboard_url", "") or "*" in getattr(
        settings, "dashboard_url", ""
    )
    if allow_wildcard:
        warnings.append("CORS allows wildcard origin (*) — restrict in production")

    if not settings.groq_api_key:
        logger.info("voice_stt_unavailable", reason="GROQ_API_KEY not set — Groq STT disabled")

    if not settings.azure_speech_key or not settings.azure_speech_region:
        logger.info("voice_azure_unavailable", reason="Azure speech key/region not set")

    if settings.addis_api_key:
        logger.info("voice_addis_available")
    else:
        logger.info("voice_addis_unavailable", reason="ADDIS_API_KEY not set")

    if settings.gemini_api_key:
        logger.info("voice_gemini_tts_available")
    else:
        logger.info("voice_gemini_tts_unavailable", reason="GEMINI_API_KEY not set")

    if not os.path.exists(DEFAULT_INDEX_PATH):
        logger.info("bm25_index_not_found_will_build_lazy")
    else:
        logger.info("bm25_index_exists_skipping_build")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            if r.status_code != 200:
                warnings.append(f"Ollama at {settings.ollama_base_url} returned {r.status_code}")
    except httpx.RequestError as e:
        warnings.append(f"Ollama at {settings.ollama_base_url} is unreachable: {e}")

    for w in warnings:
        logger.warning("startup_check_failed", check=w)

    if not warnings:
        logger.info("startup_checks_passed")

    return warnings
