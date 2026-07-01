import structlog

from src.config import settings

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

    for w in warnings:
        logger.warning("startup_check_failed", check=w)

    if not warnings:
        logger.info("startup_checks_passed")

    return warnings
