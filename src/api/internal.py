import hmac

from fastapi import APIRouter, Depends, Header

from src.core.errors import AuthError

router = APIRouter(prefix="/internal", tags=["Internal"])


async def verify_internal_api_key(x_api_key: str | None = Header(None)):
    from src.config import settings

    if not settings.internal_api_key:
        raise AuthError("internal_api_key_not_configured", "Internal API key not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.internal_api_key):
        raise AuthError("invalid_internal_api_key", "Invalid internal API key")
    return True


@router.get("/health")
async def internal_health(_: bool = Depends(verify_internal_api_key)):
    return {"status": "ok"}
