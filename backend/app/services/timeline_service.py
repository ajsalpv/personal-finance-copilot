"""
Timeline Service — Business logic for the daily life timeline.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_timeline_event(
    db: AsyncSession,
    user_id: str,
    event_type: str,
    description: str,
    timestamp: Optional[datetime] = None,
    source: str = "manual",
    metadata: Dict[str, Any] = None,
) -> dict:
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    result = await db.execute(
        text("""
            INSERT INTO timeline_events (user_id, event_type, description, timestamp, source, metadata)
            VALUES (:user_id, :type, :desc, :ts, :source, :meta::jsonb)
            RETURNING id, event_type, description, timestamp, source, metadata, created_at
        """),
        {
            "user_id": user_id, "type": event_type, "desc": description,
            "ts": timestamp, "source": source,
            "meta": str(metadata or {}).replace("'", '"'),
        },
    )
    await db.commit()
    row = result.mappings().first()
    return {**dict(row), "id": str(row["id"])}


async def get_timeline(
    db: AsyncSession,
    user_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> List[dict]:
    query = "SELECT * FROM timeline_events WHERE user_id = :user_id"
    params: dict = {"user_id": user_id}

    if start_date:
        query += " AND timestamp >= :start"
        params["start"] = start_date
    if end_date:
        query += " AND timestamp <= :end"
        params["end"] = end_date
    if event_type:
        query += " AND event_type = :type"
        params["type"] = event_type

    query += " ORDER BY timestamp DESC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(query), params)
    return [{**dict(r), "id": str(r["id"])} for r in result.mappings().all()]


async def delete_timeline_event(db: AsyncSession, user_id: str, event_id: str) -> bool:
    result = await db.execute(
        text("DELETE FROM timeline_events WHERE id = :id AND user_id = :user_id"),
        {"id": event_id, "user_id": user_id},
    )
    await db.commit()
    return result.rowcount > 0
