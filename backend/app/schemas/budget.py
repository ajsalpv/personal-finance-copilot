"""Pydantic schemas for Budget endpoints."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float = Field(..., gt=0)


class BudgetUpdate(BaseModel):
    monthly_limit: float = Field(..., gt=0)


class BudgetResponse(BaseModel):
    id: str
    category: str
    monthly_limit: float
    created_at: datetime


class BudgetStatusResponse(BaseModel):
    category: str
    monthly_limit: float
    spent: float
    remaining: float
    percentage_used: float
    is_over_budget: bool
