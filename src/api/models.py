import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from src.llm.manager import ProviderManager
from src.llm.registry import ModelRegistry

logger = structlog.get_logger()
router = APIRouter(prefix="/models", tags=["Models"])

_manager: ProviderManager | None = None
_registry: ModelRegistry | None = None


def _get_manager() -> ProviderManager:
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager


def _get_registry() -> ModelRegistry:
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
    return _registry


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    is_default: bool


class ProviderHealth(BaseModel):
    name: str
    provider_type: str
    is_healthy: bool
    available_models: list[str]


class SetModelRequest(BaseModel):
    model: str


@router.get("", response_model=list[ModelInfo])
async def list_models():
    manager = _get_manager()
    models = await manager.list_available_models()
    return [ModelInfo(**m) for m in models]


@router.get("/providers", response_model=list[ProviderHealth])
async def list_providers():
    manager = _get_manager()
    return await manager.get_provider_info()


@router.get("/active")
async def get_active_model():
    manager = _get_manager()
    return {"model": manager.active_model}


@router.post("/active")
async def set_active_model(request: SetModelRequest):
    manager = _get_manager()
    manager.set_active_model(request.model)
    return {"model": request.model, "status": "ok"}


@router.get("/health")
async def models_health():
    manager = _get_manager()
    return await manager.check_health()


@router.post("/refresh")
async def refresh_models():
    manager = _get_manager()
    await manager.refresh_models()
    return {"status": "ok"}
