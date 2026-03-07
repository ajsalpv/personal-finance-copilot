"""Pydantic schemas for Category endpoints."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    type: str  # income or expense
    icon: str = "📌"


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    type: str
    icon: str
    is_default: bool
    created_at: datetime
