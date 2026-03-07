"""
Notification Service — Create and send notifications via DB + Telegram.
"""
from typing import Optional, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_notification(
    db: AsyncSession,
    user_id: str,
    type: str,
    title: str,
    message: str,
) -> dict:
    """Create a notification record."""
    result = await db.execute(
        text("""
            INSERT INTO notifications (user_id, type, title, message)
            VALUES (:user_id, :type, :title, :message)
            RETURNING id, type, title, message, is_read, created_at
        """),
        {"user_id": user_id, "type": type, "title": title, "message": message},
    )
    await db.commit()
    row = result.mappings().first()
    return {**dict(row), "id": str(row["id"])}


async def get_notifications(
    db: AsyncSession,
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
) -> List[dict]:
    query = "SELECT * FROM notifications WHERE user_id = :user_id"
    params: dict = {"user_id": user_id}

    if unread_only:
        query += " AND is_read = FALSE"

    query += " ORDER BY created_at DESC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(query), params)
    return [{**dict(r), "id": str(r["id"])} for r in result.mappings().all()]


async def mark_as_read(db: AsyncSession, user_id: str, notification_id: str) -> bool:
    result = await db.execute(
        text("""
            UPDATE notifications SET is_read = TRUE 
            WHERE id = :id AND user_id = :user_id
        """),
        {"id": notification_id, "user_id": user_id},
    )
    await db.commit()
    return result.rowcount > 0


async def delete_notification(db: AsyncSession, user_id: str, notification_id: str) -> bool:
    result = await db.execute(
        text("DELETE FROM notifications WHERE id = :id AND user_id = :user_id"),
        {"id": notification_id, "user_id": user_id},
    )
    await db.commit()
    return result.rowcount > 0
