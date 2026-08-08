"""OAuth 2.0 sign-in (Google) with the Authorization Code + PKCE flow.

Flow (browser):

    /auth/oauth/{provider}/login?redirect=/classroom
        -> 307 to the provider's authorization URL (state + PKCE challenge)
    provider -> /auth/oauth/{provider}/callback?code=..&state=..
        -> validates state, exchanges the code for an id_token, verifies it
           against the provider's JWKS, finds/creates/links the local user,
           and 307s to {dashboard_url}/auth/oauth/callback?ticket=..
    dashboard -> POST /auth/oauth/claim  {"ticket": ".."}
        -> one-time exchange of the ticket for the normal application session
           (same access/refresh cookie pair used by /auth/token)

Security properties:

 - state is random, stored in Redis (TTL-bounded), single-use, and bound to
   the provider, so a callback can never be replayed or cross-wired.
 - the PKCE verifier is stored server-side with the state; the code exchange
   supplies it, so an intercepted authorization code cannot be redeemed.
 - the provider id_token is signature-verified against the provider JWKS and
   checked for audience and issuer before any account is created or reused.
 - OAuth identities are never merged by email alone: if the provider email
   already belongs to a local account, login fails with a conflict rather
   than silently linking (registration is unverified, so email alone cannot
   be trusted).
 - a logged-in user can explicitly link their provider identity via
   /auth/oauth/{provider}/login?link=1 (used from the dashboard).
 - client secrets and provider tokens never leave the server; the session
   issued on claim is the same HttpOnly cookie pair as password login.
"""

import base64
import hashlib
import json
import secrets
import time
import uuid
from typing import Callable, TypedDict
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import (
    _create_access_token,
    _create_refresh_token,
    _set_auth_cookies,
    get_current_user,
)
from src.config import settings
from src.core.errors import AppError, AuthError, ConflictError, NotFoundError
from src.database.models import OAuthAccount, User, UserRole
from src.database.session import get_session
from src.redis_client import get_redis

logger = structlog.get_logger()
router = APIRouter(prefix="/auth/oauth", tags=["OAuth"])

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 (bandit: URL, not secret)
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")

STATE_TTL_SECONDS = 600  # time allowed between the authorize redirect and the callback
TICKET_TTL_SECONDS = 300  # time allowed between the callback and the session claim
JWKS_CACHE_SECONDS = 12 * 3600

ProviderConfig = TypedDict(
    "ProviderConfig",
    {
        "authorize_url": str,
        "token_url": str,
        "jwks_url": str,
        "scopes": str,
        "client_id": Callable[[], str],
        "client_secret": Callable[[], str],
    },
)

PROVIDERS: dict[str, ProviderConfig] = {
    "google": {
        "authorize_url": GOOGLE_AUTHORIZE_URL,
        "token_url": GOOGLE_TOKEN_URL,
        "jwks_url": GOOGLE_JWKS_URL,
        "scopes": "openid email",
        "client_id": lambda: settings.oauth_google_client_id,
        "client_secret": lambda: settings.oauth_google_client_secret,
    },
}

_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0


class ClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticket: str


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _oauth_callback_url(provider: str) -> str:
    base = settings.oauth_callback_base_url or settings.api_base_url
    return f"{base.rstrip('/')}/auth/oauth/{provider}/callback"


def _validate_redirect_target(target: str | None) -> str:
    """Allow only same-origin redirects to prevent open-redirect attacks."""
    if not target:
        return "/classroom"
    if target.startswith(settings.dashboard_url):
        suffix = target[len(settings.dashboard_url) :]
        if suffix.startswith("/"):
            return suffix
        raise AppError(
            "invalid_redirect", "Redirect target must be a path on the dashboard", status=400
        )
    if target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    raise AppError(
        "invalid_redirect", "Redirect target must be a path on the dashboard", status=400
    )


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


async def _exchange_code_for_tokens(
    code: str, verifier: str, client_id: str, client_secret: str, redirect_uri: str
) -> dict | None:
    """Exchange the authorization code for tokens. Returns None on any failure
    so the caller can surface a user-safe error."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "code_verifier": verifier,
                },
            )
    except httpx.RequestError as exc:
        logger.error("oauth_token_exchange_network_error", error=str(exc))
        return None
    if response.status_code != 200:
        logger.warning("oauth_token_exchange_failed", status=response.status_code)
        return None
    data = response.json()
    if not data.get("id_token"):
        logger.warning("oauth_token_exchange_missing_id_token")
        return None
    return data


def _verify_google_id_token(
    id_token: str, client_id: str, jwks: dict, access_token: str
) -> dict:
    """Verify a Google id_token against the current Google JWKS.

    Google id_tokens carry an at_hash claim; python-jose verifies it against
    the access_token from the same code exchange, so it must be supplied.
    Raises ValueError when the token is not a valid, unexpired token signed by
    Google for this client."""
    try:
        payload = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=client_id,
            access_token=access_token,
            options={"verify_aud": True, "verify_exp": True, "require_exp": True},
        )
    except JWTError as exc:
        raise ValueError("id_token signature or claims invalid") from exc
    if payload.get("iss") not in GOOGLE_ISSUERS:
        raise ValueError("id_token issued by unexpected issuer")
    return payload


async def _load_google_jwks() -> dict:
    """Google public signing keys, cached server-side (12h)."""
    global _jwks_cache, _jwks_fetched_at
    if _jwks_cache is not None and time.time() - _jwks_fetched_at < JWKS_CACHE_SECONDS:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(GOOGLE_JWKS_URL)
        response.raise_for_status()
    _jwks_cache = response.json()
    _jwks_fetched_at = time.time()
    return _jwks_cache


async def _optional_current_user(
    request: Request, session: AsyncSession = Depends(get_session)
) -> User | None:
    """The logged-in user if any, else None (used for the explicit link flow)."""
    try:
        return await get_current_user(request, session)
    except AuthError:
        return None


def _error_redirect(code: str) -> RedirectResponse:
    url = f"{settings.dashboard_url}/login/oauth/callback?oauth_error={code}"
    return RedirectResponse(url, status_code=307)


# ---------------------------------------------------------------------------
# endpoints
# ---------------------------------------------------------------------------


@router.get("/{provider}/login")
async def oauth_login(
    provider: str,
    redirect: str | None = None,
    link: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Begin the authorization-code flow against the provider."""
    provider_config = PROVIDERS.get(provider)
    if not provider_config:
        raise NotFoundError("provider", f"OAuth provider '{provider}' is not supported")
    client_id = provider_config["client_id"]()
    if not client_id:
        raise AppError(
            "not_configured", f"OAuth provider '{provider}' is not configured", status=400
        )

    redirect_target = _validate_redirect_target(redirect)

    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)

    record = {
        "provider": provider,
        "verifier": verifier,
        "redirect": redirect_target,
        "link": bool(link),
    }
    redis_conn = await get_redis()
    await redis_conn.setex(
        f"oauth_state:{provider}:{state}", STATE_TTL_SECONDS, json.dumps(record)
    )

    params = {
        "client_id": client_id,
        "redirect_uri": _oauth_callback_url(provider),
        "response_type": "code",
        "scope": provider_config["scopes"],
        "state": state,
        "code_challenge": _pkce_challenge(verifier),
        "code_challenge_method": "S256",
    }
    authorize_url = f"{provider_config['authorize_url']}?{urlencode(params)}"
    logger.info("oauth_login_start", provider=provider)
    return RedirectResponse(authorize_url, status_code=307)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(_optional_current_user),
):
    """Second leg: the provider bounces the browser here with a one-time code."""
    provider_config = PROVIDERS.get(provider)
    if not provider_config:
        raise NotFoundError("provider", f"OAuth provider '{provider}' is not supported")

    if error:
        logger.info("oauth_authorization_denied", provider=provider, error=error)
        return _error_redirect("access_denied")

    if not code or not state:
        return _error_redirect("invalid_state")

    redis_conn = await get_redis()
    state_key = f"oauth_state:{provider}:{state}"
    raw = await redis_conn.get(state_key)
    await redis_conn.delete(state_key)  # single-use: one callback per authorization

    stored: dict = json.loads(raw) if raw else {}
    if not raw or stored.get("provider") != provider:
        return _error_redirect("invalid_state")

    tokens = await _exchange_code_for_tokens(
        code,
        stored["verifier"],
        provider_config["client_id"](),
        provider_config["client_secret"](),
        _oauth_callback_url(provider),
    )
    if not tokens:
        return _error_redirect("token_exchange")

    try:
        jwks = await _load_google_jwks()
        claims = _verify_google_id_token(
            tokens["id_token"], provider_config["client_id"](), jwks, tokens["access_token"]
        )
    except ValueError as exc:
        unverified_header = jwt.get_unverified_header(tokens["id_token"])
        try:
            unverified_claims = jwt.get_unverified_claims(tokens["id_token"])
        except Exception:  # noqa: BLE001
            unverified_claims = {}
        logger.warning(
            "oauth_id_token_rejected",
            error=str(exc),
            cause=(
                f"{type(exc.__cause__).__name__}: {exc.__cause__}"
                if exc.__cause__ is not None
                else "unknown"
            ),
            kid=unverified_header.get("kid"),
            alg=unverified_header.get("alg"),
            aud=unverified_claims.get("aud"),
            iss=unverified_claims.get("iss"),
            iat_age_seconds=time.time() - float(unverified_claims.get("iat", 0)),
            exp_age_seconds=float(unverified_claims.get("exp", 0)) - time.time(),
            jwks_kids=sorted(j["kid"] for j in jwks.get("keys", [])),
        )
        return _error_redirect("profile_invalid")

    if not claims.get("email_verified"):
        return _error_redirect("unverified_email")

    email = str(claims.get("email", "")).strip().lower()
    provider_sub = str(claims.get("sub", "")).strip()
    if not email or not provider_sub:
        return _error_redirect("profile_invalid")

    try:
        user = await _resolve_user(
            session=session,
            provider=provider,
            provider_user_id=provider_sub,
            email=email,
            link_mode=bool(stored.get("link")),
            current_user=current_user,
        )
    except ConflictError as exc:
        code = "email_conflict" if exc.code.endswith("email_conflict") else "conflict"
        logger.info("oauth_user_conflict", code=exc.code, provider=provider)
        return _error_redirect(code)
    except AuthError:
        return _error_redirect("login_required")

    ticket = secrets.token_urlsafe(32)
    ticket_payload = {
        "user_id": str(user.id),
        "redirect": stored.get("redirect", "/classroom"),
        "link": bool(stored.get("link")),
    }
    await redis_conn.setex(f"oauth_ticket:{ticket}", TICKET_TTL_SECONDS, json.dumps(ticket_payload))

    target = f"{settings.dashboard_url}/login/oauth/callback?ticket={ticket}"
    logger.info("oauth_callback_success", provider=provider, user_id=str(user.id))
    return RedirectResponse(target, status_code=307)


async def _resolve_user(
    session, provider: str, provider_user_id: str, email: str, link_mode: bool, current_user
):
    """Find or create the local user for a verified provider identity.

    Never links by email alone: an identity is only created for a brand-new
    email or, in link_mode, attached to the authenticated user."""
    identity_user = await session.scalar(
        select(User)
        .join(OAuthAccount, OAuthAccount.user_id == User.id)
        .where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id,
        )
    )

    if identity_user is not None:
        if link_mode and current_user is not None and identity_user.id != current_user.id:
            raise ConflictError(
                "oauth_identity",
                "This Google account is already linked to a different user.",
            )
        return identity_user

    if link_mode:
        if current_user is None:
            raise AuthError("login_required", "Sign in before linking a Google account")
        email_owner = await session.scalar(
            select(User).where(User.email == email, User.id != current_user.id)
        )
        if email_owner is not None:
            raise ConflictError(
                "email", f"The email {email} already belongs to a different account."
            )
        user = current_user
    else:
        email_user = await session.scalar(select(User).where(User.email == email))
        if email_user is not None:
            raise ConflictError(
                "email_conflict",
                "An account with this email already exists. Sign in with it and "
                "link your Google account from the dashboard.",
            )
        user = User(email=email, role=UserRole.teacher, is_active=True)
        session.add(user)
        await session.flush()

    session.add(
        OAuthAccount(user_id=user.id, provider=provider, provider_user_id=provider_user_id)
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError("oauth_identity_conflict", "This Google account is already in use")
    await session.refresh(user)
    return user


@router.post("/claim")
async def claim_session(
    body: ClaimRequest,
    session: AsyncSession = Depends(get_session),
):
    """One-time redemption of the callback's ticket: creates the application
    session (same access/refresh pair as /auth/token) and returns the token to
    the client to mirror the existing frontend login flow."""
    redis_conn = await get_redis()
    key = f"oauth_ticket:{body.ticket}"
    raw = await redis_conn.get(key)
    await redis_conn.delete(key)  # single-use
    if not raw:
        raise AuthError("invalid_ticket", "OAuth ticket is invalid or expired")

    try:
        payload = json.loads(raw)
        user_id = uuid.UUID(str(payload["user_id"]))
    except (json.JSONDecodeError, KeyError, ValueError):
        raise AuthError("invalid_ticket", "OAuth ticket is malformed")

    user = await session.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise AuthError("user_inactive", "User not found or inactive")

    access_token = _create_access_token(str(user.id), user.role.value)
    refresh_token, jti = _create_refresh_token(str(user.id))
    await redis_conn.setex(
        f"refresh:{jti}", settings.refresh_token_expire_days * 86400, str(user.id)
    )
    await redis_conn.sadd(f"refresh_tokens:{str(user.id)}", jti)

    response = JSONResponse(
        status_code=200,
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "redirect": payload.get("redirect", "/classroom"),
        },
    )
    _set_auth_cookies(response, access_token, refresh_token)
    return response
