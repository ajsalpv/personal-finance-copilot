"""Pydantic schemas for Timeline endpoints."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class TimelineEventCreate(BaseModel):
    event_type: str  # expense, income, task, note, file, meeting, location
    description: str
    timestamp: Optional[datetime] = None
    source: str = "manual"
    metadata: Dict[str, Any] = {}


class TimelineEventResponse(BaseModel):
    id: str
    event_type: str
    description: str
    timestamp: datetime
    source: str
    metadata: Dict[str, Any]
    created_at: datetime
