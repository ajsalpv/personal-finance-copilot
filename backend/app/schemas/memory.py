"""Pydantic schemas for Memory/Knowledge endpoints."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    content: str
    type: str = "general"  # general, personal, preference, fact, event
    tags: List[str] = []
    importance_score: int = Field(5, ge=1, le=10)


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    importance_score: Optional[int] = Field(None, ge=1, le=10)


class MemoryResponse(BaseModel):
    id: str
    content: str
    type: str
    tags: List[str]
    importance_score: int
    created_at: datetime


class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 5
