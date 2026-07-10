#!/usr/bin/env python
"""Audit required env vars for production deployment. Exit 1 if any are missing or weak."""

import os
import sys

REQUIRED = {
    "DATABASE_URL": "PostgreSQL connection string (Railway plugin or external)",
    "REDIS_URL": "Redis connection string (Upstash or Railway plugin)",
    "OLLAMA_BASE_URL": "Ollama API URL (http://localhost:11434 or https://ollama.com for Cloud)",
    "OLLAMA_CHAT_MODEL": "Ollama chat model name (e.g. glm-5.2, deepseek-v4-flash)",
    "OLLAMA_API_KEY": "Ollama Cloud API key (required if OLLAMA_BASE_URL is https://ollama.com)",
    "SECRET_KEY": "App secret key for sessions",
    "JWT_SECRET": "JWT signing secret",
    "TELEGRAM_BOT_TOKEN": "Telegram bot token from @BotFather",
}

WEAK_VALUES = {
    "SECRET_KEY": {
        "change-me",
        "change-me-in-production",
        "dev-secret-key-change-in-production",
        "",
    },
    "JWT_SECRET": {"change-me-jwt-secret", "dev-jwt-secret", ""},
    "OLLAMA_API_KEY": {""},
}


def main() -> int:
    missing = []
    weak = []

    for var, desc in REQUIRED.items():
        val = os.environ.get(var, "")
        if not val:
            missing.append((var, desc))
            continue

        weak_values = WEAK_VALUES.get(var, set())
        if val in weak_values:
            weak.append((var, val))

    if missing:
        print("MISSING REQUIRED ENV VARS:")
        for var, desc in missing:
            print(f"  {var}: {desc}")
        print()

    if weak:
        print("WEAK/PLACEHOLDER VALUES DETECTED:")
        for var, val in weak:
            display = val[:8] + "..." if len(val) > 8 else val
            print(f"  {var} = {display} (replace with a strong, unique value)")
        print()

    if missing or weak:
        print("Set these in Railway env vars (or .env for local dev).")
        print(
            'Generate strong secrets with: '
            'python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
        return 1

    print("All required env vars present and non-placeholder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
