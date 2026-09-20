import asyncio
import os
import shutil
from pathlib import Path

from src.core.storage.interface import StorageAdapter
from src.core.storage.safe import safe_resolved, safe_storage_parts


class LocalFileStorage(StorageAdapter):
    def __init__(self, base_path: Path = Path("./data/storage")):
        self.base_path = base_path

    async def store(self, file_path: Path, workspace_id: str, ko_id: str, filename: str) -> str:
        ws_id, ko_id, safe_name = safe_storage_parts(workspace_id, ko_id, filename)
        dest_dir = safe_resolved(self.base_path, f"{ws_id}/{ko_id}")
        dest = dest_dir / safe_name
        safe_resolved(self.base_path, f"{ws_id}/{ko_id}/{safe_name}")

        await asyncio.to_thread(dest_dir.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, str(file_path), str(dest))

        return f"{ws_id}/{ko_id}/{safe_name}"

    async def retrieve(self, storage_key: str) -> Path:
        path = safe_resolved(self.base_path, storage_key)
        exists = await asyncio.to_thread(path.exists)
        if not exists:
            raise FileNotFoundError(f"Storage key not found: {storage_key}")
        return path

    async def delete(self, storage_key: str) -> None:
        path = safe_resolved(self.base_path, storage_key)
        await asyncio.to_thread(os.remove, str(path))

    async def exists(self, storage_key: str) -> bool:
        path = safe_resolved(self.base_path, storage_key)
        return await asyncio.to_thread(path.exists)
