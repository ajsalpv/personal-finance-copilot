"""
File Service — Business logic for file uploads and storage via Supabase Storage.
"""
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_supabase_client


async def upload_file(
    db: AsyncSession,
    user_id: str,
    filename: str,
    file_content: bytes,
    mime_type: str,
    file_type: Optional[str] = None,
) -> dict:
    """Upload a file to Supabase Storage and record it in the database."""
    settings = get_settings()
    supabase = get_supabase_client()

    # Create unique storage path
    file_id = str(uuid4())
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    storage_path = f"{user_id}/{file_id}.{ext}" if ext else f"{user_id}/{file_id}"

    # Upload to Supabase Storage
    supabase.storage.from_(settings.STORAGE_BUCKET).upload(
        path=storage_path,
        file=file_content,
        file_options={"content-type": mime_type},
    )

    # Save record in database
    result = await db.execute(
        text("""
            INSERT INTO file_records 
            (user_id, filename, storage_path, file_type, file_size, mime_type)
            VALUES (:user_id, :filename, :path, :type, :size, :mime)
            RETURNING id, filename, storage_path, file_type, file_size, mime_type, 
                      extracted_text, metadata, created_at
        """),
        {
            "user_id": user_id, "filename": filename, "path": storage_path,
            "type": file_type, "size": len(file_content), "mime": mime_type,
        },
    )
    await db.commit()
    row = result.mappings().first()
    return {**dict(row), "id": str(row["id"])}


async def get_files(db: AsyncSession, user_id: str, limit: int = 50) -> List[dict]:
    result = await db.execute(
        text("""
            SELECT * FROM file_records WHERE user_id = :user_id 
            ORDER BY created_at DESC LIMIT :limit
        """),
        {"user_id": user_id, "limit": limit},
    )
    return [{**dict(r), "id": str(r["id"])} for r in result.mappings().all()]


async def get_file_by_id(db: AsyncSession, user_id: str, file_id: str) -> Optional[dict]:
    result = await db.execute(
        text("SELECT * FROM file_records WHERE id = :id AND user_id = :user_id"),
        {"id": file_id, "user_id": user_id},
    )
    row = result.mappings().first()
    return {**dict(row), "id": str(row["id"])} if row else None


def get_download_url(storage_path: str, expires_in: int = 3600) -> str:
    """Generate a signed download URL for a file."""
    settings = get_settings()
    supabase = get_supabase_client()
    response = supabase.storage.from_(settings.STORAGE_BUCKET).create_signed_url(
        path=storage_path, expires_in=expires_in
    )
    return response["signedURL"]


async def delete_file(db: AsyncSession, user_id: str, file_id: str) -> bool:
    """Delete file from storage and database."""
    file_record = await get_file_by_id(db, user_id, file_id)
    if not file_record:
        return False

    # Delete from Supabase Storage
    settings = get_settings()
    supabase = get_supabase_client()
    supabase.storage.from_(settings.STORAGE_BUCKET).remove([file_record["storage_path"]])

    # Delete from database
    await db.execute(
        text("DELETE FROM file_records WHERE id = :id AND user_id = :user_id"),
        {"id": file_id, "user_id": user_id},
    )
    await db.commit()
    return True
