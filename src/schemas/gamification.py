from datetime import datetime
from uuid import UUID

from src.schemas.base import SchemaModel

LEVEL_THRESHOLDS = [
    0, 100, 250, 500, 1000, 1750, 2750, 4000, 5500, 7500, 10000,
]


def calculate_level(total_xp: int) -> int:
    level = 1
    for threshold in LEVEL_THRESHOLDS[1:]:
        if total_xp >= threshold:
            level += 1
        else:
            break
    return level


def xp_for_next_level(total_xp: int) -> int:
    current_level = calculate_level(total_xp)
    if current_level >= len(LEVEL_THRESHOLDS):
        return 0
    return LEVEL_THRESHOLDS[current_level] - total_xp


class XpAwardRequest(SchemaModel):
    user_id: UUID
    source: str
    amount: int
    event_metadata: dict = {}


class XpEventResponse(SchemaModel):
    id: UUID
    source: str
    amount: int
    created_at: datetime


class GamificationProfileResponse(SchemaModel):
    user_id: UUID
    total_xp: int
    level: int
    current_streak: int
    longest_streak: int
    next_level_xp: int
    recent_events: list[XpEventResponse] = []
