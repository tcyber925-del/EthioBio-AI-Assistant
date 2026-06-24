"""MemoryService abstraction layer for Wave 0.

Defines the memory API contract without implementing against real storage.
Implementations will be built in Wave 2 backed by episodic memory tables.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class MemoryRecord:
    def __init__(
        self,
        memory_id: str,
        user_id: str,
        memory_type: str,
        content: str,
        metadata: dict | None = None,
        score: float = 0.0,
        created_at: str | None = None,
    ):
        self.memory_id = memory_id
        self.user_id = user_id
        self.memory_type = memory_type
        self.content = content
        self.metadata = metadata or {}
        self.score = score
        self.created_at = created_at


class TimelineEntry:
    def __init__(
        self,
        entry_id: str,
        timestamp: datetime,
        entry_type: str,
        summary: str,
        topic: str | None = None,
        metadata: dict | None = None,
    ):
        self.entry_id = entry_id
        self.timestamp = timestamp
        self.entry_type = entry_type
        self.summary = summary
        self.topic = topic
        self.metadata = metadata or {}


class MemoryService(ABC):
    @abstractmethod
    async def record_event(
        self,
        user_id: UUID,
        event_type: str,
        topic: str | None = None,
        metadata: dict | None = None,
    ) -> bool:
        ...

    @abstractmethod
    async def get_timeline(
        self,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[TimelineEntry]:
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        user_id: UUID | None = None,
        topic: str | None = None,
        n_results: int = 5,
    ) -> list[MemoryRecord]:
        ...

    @abstractmethod
    async def get_session_context(
        self,
        user_id: UUID,
        topic: str | None = None,
    ) -> str:
        ...
