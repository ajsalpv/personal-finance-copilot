"""Pydantic schemas for Transaction endpoints."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class TransactionType(str, Enum):
    income = "income"
    expense = "expense"


class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0)
    transaction_type: TransactionType
    merchant_name: Optional[str] = None
    person_name: Optional[str] = None
    upi_id: Optional[str] = None
    category: Optional[str] = None
    payment_method: str = "cash"
    date: Optional[datetime] = None
    source: str = "manual"
    note: Optional[str] = None


class TransactionUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    transaction_type: Optional[TransactionType] = None
    merchant_name: Optional[str] = None
    person_name: Optional[str] = None
    upi_id: Optional[str] = None
    category: Optional[str] = None
    payment_method: Optional[str] = None
    date: Optional[datetime] = None
    note: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    amount: float
    transaction_type: str
    merchant_name: Optional[str] = None
    person_name: Optional[str] = None
    upi_id: Optional[str] = None  # masked
    category: Optional[str] = None
    payment_method: str
    date: datetime
    source: str
    note: Optional[str] = None
    created_at: datetime


class TransactionSummary(BaseModel):
    category: str
    total: float
    count: int
    percentage: float


class SpendingSummaryResponse(BaseModel):
    period: str
    total_income: float
    total_expense: float
    net: float
    by_category: List[TransactionSummary]
