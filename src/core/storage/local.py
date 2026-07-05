import asyncio
import os
import shutil
from pathlib import Path

from src.core.storage.interface import StorageAdapter


class LocalFileStorage(StorageAdapter):
    def __init__(self, base_path: Path = Path("./data/storage")):
        self.base_path = base_path

    async def store(self, file_path: Path, workspace_id: str, ko_id: str, filename: str) -> str:
        dest_dir = self.base_path / workspace_id / ko_id
        dest = dest_dir / filename

        await asyncio.to_thread(dest_dir.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copy2, str(file_path), str(dest))

        return f"{workspace_id}/{ko_id}/{filename}"

    async def retrieve(self, storage_key: str) -> Path:
        path = self.base_path / storage_key
        exists = await asyncio.to_thread(path.exists)
        if not exists:
            raise FileNotFoundError(f"Storage key not found: {storage_key}")
        return path

    async def delete(self, storage_key: str) -> None:
        path = self.base_path / storage_key
        await asyncio.to_thread(os.remove, str(path))

    async def exists(self, storage_key: str) -> bool:
        path = self.base_path / storage_key
        return await asyncio.to_thread(path.exists)
