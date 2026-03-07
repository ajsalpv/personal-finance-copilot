"""Pydantic schemas for User endpoints."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    telegram_id: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    telegram_id: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class VoiceEnrollResponse(BaseModel):
    message: str
    samples_processed: int


class VoiceVerifyResponse(BaseModel):
    verified: bool
    similarity: float
