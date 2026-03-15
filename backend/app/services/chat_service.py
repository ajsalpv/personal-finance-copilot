"""
Chat Service — Business logic for persistent conversation history.
"""
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def save_chat_message(
    db: AsyncSession,
    user_id: str,
    role: str,
    text_content: str,
    thread_id: Optional[str] = None,
    memory_recalled: bool = False
) -> dict:
    """Save a chat message to the database."""
    result = await db.execute(
        text("""
            INSERT INTO chat_messages (user_id, role, text, thread_id, memory_recalled)
            VALUES (:user_id, :role, :text, :thread_id, :memory_recalled)
            RETURNING id, user_id, role, text, thread_id, memory_recalled, created_at
        """),
        {
            "user_id": user_id,
            "role": role,
            "text": text_content,
            "thread_id": thread_id,
            "memory_recalled": memory_recalled
        }
    )
    await db.commit()
    row = result.mappings().first()
    message = dict(row)
    # Convert UUID to string
    message["id"] = str(message["id"])
    message["user_id"] = str(message["user_id"])
    return message

async def get_chat_history(
    db: AsyncSession,
    user_id: str,
    limit: int = 50
) -> List[dict]:
    """Retrieve recent chat history for a user."""
    result = await db.execute(
        text("""
            SELECT id, role, text, thread_id, memory_recalled, created_at
            FROM chat_messages
            WHERE user_id = :user_id
            ORDER BY created_at ASC
            LIMIT :limit
        """),
        {"user_id": user_id, "limit": limit}
    )
    rows = result.mappings().all()
    history = []
    for r in rows:
        m = dict(r)
        m["id"] = str(m["id"])
        history.append(m)
    return history

async def delete_chat_history(db: AsyncSession, user_id: str) -> bool:
    """Clear all chat history for a user."""
    result = await db.execute(
        text("DELETE FROM chat_messages WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    await db.commit()
    return result.rowcount > 0
