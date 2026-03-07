"""
Memory Service — Business logic for knowledge/memory storage and retrieval.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.encryption import encrypt, decrypt


async def create_memory(
    db: AsyncSession,
    user_id: str,
    content: str,
    type: str = "general",
    tags: List[str] = None,
    importance_score: int = 5,
) -> dict:
    enc_content = encrypt(content)

    result = await db.execute(
        text("""
            INSERT INTO memories (user_id, content, type, tags, importance_score)
            VALUES (:user_id, :content, :type, :tags, :importance)
            RETURNING id, content, type, tags, importance_score, created_at
        """),
        {
            "user_id": user_id, "content": enc_content,
            "type": type, "tags": tags or [],
            "importance": importance_score,
        },
    )
    await db.commit()
    row = dict(result.mappings().first())
    row["content"] = content  # Return plaintext
    row["id"] = str(row["id"])
    return row


async def get_memories(
    db: AsyncSession,
    user_id: str,
    type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[dict]:
    query = "SELECT * FROM memories WHERE user_id = :user_id"
    params: dict = {"user_id": user_id}

    if type:
        query += " AND type = :type"
        params["type"] = type

    query += " ORDER BY importance_score DESC, created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    result = await db.execute(text(query), params)
    memories = []
    for r in result.mappings().all():
        row = dict(r)
        row["content"] = decrypt(row["content"])
        row["id"] = str(row["id"])
        memories.append(row)
    return memories


async def get_memory_by_id(db: AsyncSession, user_id: str, memory_id: str) -> Optional[dict]:
    result = await db.execute(
        text("SELECT * FROM memories WHERE id = :id AND user_id = :user_id"),
        {"id": memory_id, "user_id": user_id},
    )
    row = result.mappings().first()
    if not row:
        return None
    row = dict(row)
    row["content"] = decrypt(row["content"])
    row["id"] = str(row["id"])
    return row


async def update_memory(db: AsyncSession, user_id: str, memory_id: str, updates: dict) -> Optional[dict]:
    if "content" in updates and updates["content"]:
        updates["content"] = encrypt(updates["content"])

    filtered = {k: v for k, v in updates.items() if v is not None}
    if not filtered:
        return await get_memory_by_id(db, user_id, memory_id)

    set_clauses = ", ".join(f"{k} = :{k}" for k in filtered)
    filtered["id"] = memory_id
    filtered["user_id"] = user_id

    await db.execute(
        text(f"UPDATE memories SET {set_clauses} WHERE id = :id AND user_id = :user_id"),
        filtered,
    )
    await db.commit()
    return await get_memory_by_id(db, user_id, memory_id)


async def delete_memory(db: AsyncSession, user_id: str, memory_id: str) -> bool:
    result = await db.execute(
        text("DELETE FROM memories WHERE id = :id AND user_id = :user_id"),
        {"id": memory_id, "user_id": user_id},
    )
    await db.commit()
    return result.rowcount > 0


async def search_memories(db: AsyncSession, user_id: str, query: str, limit: int = 5) -> List[dict]:
    """
    Search memories by keyword match.
    """
    result = await db.execute(
        text("""
            SELECT * FROM memories 
            WHERE user_id = :user_id
            ORDER BY importance_score DESC, created_at DESC
            LIMIT :limit
        """),
        {"user_id": user_id, "limit": limit * 3},
    )
    rows = result.mappings().all()

    query_lower = query.lower()
    matches = []
    for r in rows:
        row = dict(r)
        row["content"] = decrypt(row["content"])
        row["id"] = str(row["id"])
        if query_lower in row["content"].lower():
            matches.append(row)
            if len(matches) >= limit:
                break
    return matches


async def store_reflection(db: AsyncSession, user_id: str, fact: str, category: str = "general"):
    """
    Stores a persistent fact or reflection about the user.
    """
    enc_fact = encrypt(fact)
    await db.execute(
        text("""
            INSERT INTO memories (user_id, content, type, importance_score, tags)
            VALUES (:user_id, :content, 'fact', 10, :tags)
        """),
        {"user_id": user_id, "content": enc_fact, "tags": [category]},
    )
    await db.commit()


async def get_long_term_memory(db: AsyncSession, user_id: str) -> str:
    """
    Retrieves all stored facts for memory pre-processing.
    """
    result = await db.execute(
        text("SELECT content, tags FROM memories WHERE user_id = :user_id AND type = 'fact'"),
        {"user_id": user_id},
    )
    rows = result.mappings().all()
    facts = []
    for r in rows:
        content = decrypt(r["content"])
        category = r["tags"][0] if r["tags"] else "General"
        facts.append(f"- [{category}]: {content}")
    
    return "\n".join(facts) if facts else "No long-term memories found yet."
