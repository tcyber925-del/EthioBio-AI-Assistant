from datetime import datetime

from src.schemas.base import SchemaModel


class ActivityItem(SchemaModel):
    activity_type: str
    title: str
    description: str
    icon: str
    timestamp: datetime
    metadata: dict = {}


class ActivityFeedResponse(SchemaModel):
    activities: list[ActivityItem] = []
