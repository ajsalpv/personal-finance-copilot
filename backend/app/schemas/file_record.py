"""Pydantic schemas for File endpoints."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class FileRecordResponse(BaseModel):
    id: str
    filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    extracted_text: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime


class FileUploadResponse(BaseModel):
    message: str
    file: FileRecordResponse
