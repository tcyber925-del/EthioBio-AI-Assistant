"""Clerk session-token verification via JWKS (python-jose)."""

import time

import httpx
from jose import jwt as jose_jwt

from src.config import settings
from src.core.errors import AuthError

_JWKS_URL = None
_JWKS_CACHE: dict | None = None
_JWKS_LOADED_AT = 0.0
_JWKS_TTL = 12 * 3600


def _jwks_url() -> str:
    global _JWKS_URL
    if _JWKS_URL is None:
        base = settings.clerk_frontend_api.rstrip("/")
        if not base:
            raise AuthError("clerk_not_configured", "Clerk frontend API not configured")
        _JWKS_URL = f"{base}/.well-known/jwks.json"
    return _JWKS_URL


async def _get_jwks() -> dict:
    global _JWKS_CACHE, _JWKS_LOADED_AT
    if _JWKS_CACHE is not None and time.time() - _JWKS_LOADED_AT < _JWKS_TTL:
        return _JWKS_CACHE
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(_jwks_url())
        resp.raise_for_status()
    _JWKS_CACHE = resp.json()
    _JWKS_LOADED_AT = time.time()
    return _JWKS_CACHE


async def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk session JWT and return its claims."""
    jwks = await _get_jwks()
    try:
        header = jose_jwt.get_unverified_header(token)
    except Exception as exc:
        raise AuthError("invalid_token", "Token is malformed or invalid") from exc

    kid = header.get("kid")
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if key is None:
        raise AuthError("invalid_token", "Unknown token signing key")

    try:
        claims = jose_jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.clerk_frontend_api.rstrip("/"),
            options={"verify_aud": False},
        )
    except Exception as exc:
        raise AuthError("invalid_token", "Token is malformed or invalid") from exc

    if not claims.get("sub"):
        raise AuthError("invalid_token", "Token missing subject")
    return claims


async def extract_user_id_unverified(token: str) -> str | None:
    """Extract the sub claim without verifying (rate-limit keying only)."""
    try:
        payload = jose_jwt.get_unverified_claims(token)
    except Exception:
        return None
    return payload.get("sub")
