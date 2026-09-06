from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(tags=["Test"])


@router.get("/test")
async def test_endpoint():
    return {
        "status": "ok",
        "message": "Test endpoint from Telegram",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
