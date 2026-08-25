from fastapi import APIRouter

router = APIRouter(tags=["Config"])


@router.get("/config/validate")
async def validate_config():
    return {"status": "valid", "service": "ethiosci"}
