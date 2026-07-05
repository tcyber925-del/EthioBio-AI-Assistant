from datetime import datetime

from pydantic import BaseModel


class PipelineEvent(BaseModel):
    event_type: str
    ko_id: str
    workspace_id: str
    payload: dict
    occurred_at: datetime
    correlation_id: str
