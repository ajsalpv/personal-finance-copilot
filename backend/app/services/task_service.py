"""
Task Service — Business logic for tasks and reminders.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_task(
    db: AsyncSession,
    user_id: str,
    title: str,
    description: Optional[str] = None,
    due_date: Optional[datetime] = None,
    priority: str = "medium",
    recurrence: Optional[str] = None,
) -> dict:
    result = await db.execute(
        text("""
            INSERT INTO tasks (user_id, title, description, due_date, priority, recurrence)
            VALUES (:user_id, :title, :desc, :due, :priority, :recurrence)
            RETURNING id, title, description, due_date, status, priority, recurrence, created_at
        """),
        {
            "user_id": user_id, "title": title, "desc": description,
            "due": due_date, "priority": priority, "recurrence": recurrence,
        },
    )
    await db.commit()
    row = result.mappings().first()
    return {**dict(row), "id": str(row["id"])}


async def get_tasks(
    db: AsyncSession,
    user_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[dict]:
    query = "SELECT * FROM tasks WHERE user_id = :user_id"
    params: dict = {"user_id": user_id}

    if status:
        query += " AND status = :status"
        params["status"] = status
    if priority:
        query += " AND priority = :priority"
        params["priority"] = priority

    query += " ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    result = await db.execute(text(query), params)
    return [{**dict(r), "id": str(r["id"])} for r in result.mappings().all()]


async def get_task_by_id(db: AsyncSession, user_id: str, task_id: str) -> Optional[dict]:
    result = await db.execute(
        text("SELECT * FROM tasks WHERE id = :id AND user_id = :user_id"),
        {"id": task_id, "user_id": user_id},
    )
    row = result.mappings().first()
    return {**dict(row), "id": str(row["id"])} if row else None


async def update_task(db: AsyncSession, user_id: str, task_id: str, updates: dict) -> Optional[dict]:
    filtered = {k: v for k, v in updates.items() if v is not None}
    if not filtered:
        return await get_task_by_id(db, user_id, task_id)

    set_clauses = ", ".join(f"{k} = :{k}" for k in filtered)
    filtered["id"] = task_id
    filtered["user_id"] = user_id

    await db.execute(
        text(f"UPDATE tasks SET {set_clauses} WHERE id = :id AND user_id = :user_id"),
        filtered,
    )
    await db.commit()
    return await get_task_by_id(db, user_id, task_id)


async def delete_task(db: AsyncSession, user_id: str, task_id: str) -> bool:
    result = await db.execute(
        text("DELETE FROM tasks WHERE id = :id AND user_id = :user_id"),
        {"id": task_id, "user_id": user_id},
    )
    await db.commit()
    return result.rowcount > 0
