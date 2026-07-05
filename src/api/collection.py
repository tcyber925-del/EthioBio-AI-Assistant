import structlog
from fastapi import APIRouter, HTTPException, Query

from src.core.collection import CollectionService
from src.core.collection.models import Collection, NewCollection, UpdateCollection
from src.database.session import async_session_factory

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/collections", tags=["Collections"])

_service: CollectionService | None = None


def _get_service() -> CollectionService:
    global _service
    if _service is None:
        _service = CollectionService(async_session_factory())
    return _service


@router.post("/", response_model=Collection, status_code=201)
async def create_collection(
    data: NewCollection,
    created_by: str = Query(...),
):
    result = await _get_service().create(data, created_by)
    return result


@router.get("/{collection_id}", response_model=Collection)
async def get_collection(collection_id: str):
    result = await _get_service().get(collection_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return result


@router.get("/", response_model=list[Collection])
async def list_collections(workspace_id: str = Query(...)):
    return await _get_service().list_for_workspace(workspace_id)


@router.patch("/{collection_id}", response_model=Collection)
async def update_collection(collection_id: str, data: UpdateCollection):
    result = await _get_service().update(collection_id, data)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return result


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(collection_id: str):
    ok = await _get_service().soft_delete(collection_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Collection not found")


@router.post("/{collection_id}/items", status_code=201)
async def add_to_collection(collection_id: str, ko_id: str = Query(...)):
    ok = await _get_service().add_knowledge_object(collection_id, ko_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Collection or KnowledgeObject not found")
    return {"status": "added"}


@router.delete("/{collection_id}/items/{ko_id}", status_code=204)
async def remove_from_collection(collection_id: str, ko_id: str):
    ok = await _get_service().remove_knowledge_object(collection_id, ko_id)
    if not ok:
        raise HTTPException(status_code=404, detail="KnowledgeObject not found")


@router.get("/{collection_id}/items")
async def list_collection_items(collection_id: str):
    items = await _get_service().list_knowledge_objects(collection_id)
    return items
