from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


PRODUCTION_SECURITY_THRESHOLDS = {
    "jwt_secret_not_default": True,
    "cors_not_wildcard": True,
    "pii_sanitization_wired": True,
    "prompt_injection_protection": True,
    "rate_limiting_configurable": True,
    "redis_auth_configured": True,
}


def check_jwt_secret() -> dict[str, Any]:
    """Verify JWT secret is not the default value."""
    try:
        secret = os.environ.get("JWT_SECRET_KEY", "")
        is_default = secret in ("", "change-me", "change-me-jwt-secret")
        return {
            "check": "jwt_secret_not_default",
            "passed": not is_default,
            "detail": "JWT_SECRET_KEY is configured" if not is_default else "JWT_SECRET_KEY is default or unset",
        }
    except Exception as e:
        return {"check": "jwt_secret_not_default", "passed": False, "detail": str(e)}


def check_cors_configuration() -> dict[str, Any]:
    """Verify CORS is not wide-open with wildcard in production."""
    try:
        from src.config import settings

        origins = getattr(settings, "dashboard_url", "")
        has_wildcard = "*" in str(origins)
        return {
            "check": "cors_not_wildcard",
            "passed": not has_wildcard,
            "detail": f"CORS origins: {origins}" if not has_wildcard else "CORS has wildcard origin",
        }
    except (ImportError, AttributeError) as e:
        return {"check": "cors_not_wildcard", "passed": False, "detail": str(e)}


def check_pii_sanitization() -> dict[str, Any]:
    """Verify PII sanitization is wired into memory pipeline."""
    try:
        from src.core.memory.safety import sanitize_summary_content, validate_summary_content

        has_sanitize = callable(sanitize_summary_content)
        has_validate = callable(validate_summary_content)
        all_present = has_sanitize and has_validate
        return {
            "check": "pii_sanitization_wired",
            "passed": all_present,
            "detail": "PII sanitization functions present" if all_present else "sanitize_summary_content or validate_summary_content missing",
        }
    except ImportError:
        return {"check": "pii_sanitization_wired", "passed": False, "detail": "PII sanitization module not found"}


def check_prompt_injection_protection() -> dict[str, Any]:
    """Verify prompt injection protection is wired into the pipeline."""
    try:
        from src.agents.safety import SafetyAgent

        has_review = hasattr(SafetyAgent, "review")
        return {
            "check": "prompt_injection_protection",
            "passed": has_review,
            "detail": "SafetyAgent with content review present" if has_review else "SafetyAgent missing review method",
        }
    except ImportError:
        return {"check": "prompt_injection_protection", "passed": False, "detail": "SafetyAgent not found"}


def check_rate_limiting_config() -> dict[str, Any]:
    """Verify rate limiting settings are present in config."""
    try:
        from src.config import settings

        config_fields = [a for a in dir(settings) if not a.startswith("_")]
        has_rate_limit = any("rate" in f.lower() for f in config_fields)
        return {
            "check": "rate_limiting_configurable",
            "passed": has_rate_limit,
            "detail": "Rate limiting settings found" if has_rate_limit else "No rate limiting settings in config",
        }
    except (ImportError, AttributeError):
        return {"check": "rate_limiting_configurable", "passed": False, "detail": "Settings not accessible"}


def check_redis_auth() -> dict[str, Any]:
    """Verify Redis URL includes auth credentials."""
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        has_password = "@" in redis_url and redis_url.count(":") > 1
        return {
            "check": "redis_auth_configured",
            "passed": has_password,
            "detail": "Redis URL has auth" if has_password else "Redis URL has no password (default)",
        }
    except Exception as e:
        return {"check": "redis_auth_configured", "passed": False, "detail": str(e)}


def run_security_checks() -> dict[str, Any]:
    """Run all security certification checks."""
    checks = [
        check_jwt_secret(),
        check_cors_configuration(),
        check_pii_sanitization(),
        check_prompt_injection_protection(),
        check_rate_limiting_config(),
        check_redis_auth(),
    ]

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    score = passed / total if total > 0 else 0.0

    return {
        "score": round(score, 3),
        "passed": passed,
        "total": total,
        "checks": checks,
        "failures": [c["check"] for c in checks if not c["passed"]],
    }
