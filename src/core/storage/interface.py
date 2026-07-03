from abc import ABC, abstractmethod
from pathlib import Path


class StorageAdapter(ABC):
    @abstractmethod
    async def store(self, file_path: Path, workspace_id: str, ko_id: str, filename: str) -> str:
        ...

    @abstractmethod
    async def retrieve(self, storage_key: str) -> Path:
        ...

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        ...

    @abstractmethod
    async def exists(self, storage_key: str) -> bool:
        ...
