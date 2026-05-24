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


def xp_for_current_level(total_xp: int) -> int:
    level = calculate_level(total_xp)
    return LEVEL_THRESHOLDS[level - 1]


def next_level_threshold(total_xp: int) -> int:
    level = calculate_level(total_xp)
    if level >= len(LEVEL_THRESHOLDS):
        return total_xp
    return LEVEL_THRESHOLDS[level]


def progress_pct(total_xp: int) -> float:
    current = xp_for_current_level(total_xp)
    next_t = next_level_threshold(total_xp)
    if next_t <= current:
        return 100.0
    return round((total_xp - current) / (next_t - current) * 100, 1)


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
    progress_pct: float = 0.0
    level_up: bool = False
    new_level: int = 0
    recent_events: list[XpEventResponse] = []
