"""
Files Router — File upload, listing, download, and deletion.
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security.auth import get_current_user
from app.schemas.file_record import FileRecordResponse, FileUploadResponse
from app.services import file_service

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: Optional[str] = Query(None, description="receipt, bill, document, screenshot, note"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file to storage."""
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    record = await file_service.upload_file(
        db=db,
        user_id=str(current_user["id"]),
        filename=file.filename or "unnamed",
        file_content=content,
        mime_type=file.content_type or "application/octet-stream",
        file_type=file_type,
    )

    return FileUploadResponse(
        message="File uploaded successfully",
        file=FileRecordResponse(**record),
    )


@router.get("", response_model=List[FileRecordResponse])
async def list_files(
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's uploaded files."""
    return await file_service.get_files(db, str(current_user["id"]), limit=limit)


@router.get("/{file_id}/download")
async def get_download_url(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a signed download URL for a file."""
    record = await file_service.get_file_by_id(db, str(current_user["id"]), file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File not found")

    url = file_service.get_download_url(record["storage_path"])
    return {"download_url": url, "filename": record["filename"]}


@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file from storage and database."""
    deleted = await file_service.delete_file(db, str(current_user["id"]), file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    return {"message": "File deleted"}
