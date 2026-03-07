"""
Budget Service — Business logic for budget management.
"""
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def create_budget(db: AsyncSession, user_id: str, category: str, monthly_limit: float) -> dict:
    result = await db.execute(
        text("""
            INSERT INTO budgets (user_id, category, monthly_limit)
            VALUES (:user_id, :category, :limit)
            ON CONFLICT (user_id, category) DO UPDATE SET monthly_limit = :limit
            RETURNING id, category, monthly_limit, created_at
        """),
        {"user_id": user_id, "category": category, "limit": monthly_limit},
    )
    await db.commit()
    row = result.mappings().first()
    return {**dict(row), "id": str(row["id"])}


async def get_budgets(db: AsyncSession, user_id: str) -> List[dict]:
    result = await db.execute(
        text("SELECT * FROM budgets WHERE user_id = :user_id ORDER BY category"),
        {"user_id": user_id},
    )
    return [{**dict(r), "id": str(r["id"])} for r in result.mappings().all()]


async def update_budget(db: AsyncSession, user_id: str, budget_id: str, monthly_limit: float) -> Optional[dict]:
    result = await db.execute(
        text("""
            UPDATE budgets SET monthly_limit = :limit 
            WHERE id = :id AND user_id = :user_id
            RETURNING id, category, monthly_limit, created_at
        """),
        {"id": budget_id, "user_id": user_id, "limit": monthly_limit},
    )
    await db.commit()
    row = result.mappings().first()
    return {**dict(row), "id": str(row["id"])} if row else None


async def delete_budget(db: AsyncSession, user_id: str, budget_id: str) -> bool:
    result = await db.execute(
        text("DELETE FROM budgets WHERE id = :id AND user_id = :user_id"),
        {"id": budget_id, "user_id": user_id},
    )
    await db.commit()
    return result.rowcount > 0


async def get_budget_status(db: AsyncSession, user_id: str) -> List[dict]:
    """Get spending vs budget for each category in the current month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        text("""
            SELECT 
                b.category,
                b.monthly_limit,
                COALESCE(SUM(t.amount), 0) as spent
            FROM budgets b
            LEFT JOIN transactions t ON 
                t.user_id = b.user_id 
                AND t.category = b.category 
                AND t.transaction_type = 'expense'
                AND t.date >= :month_start
                AND t.date <= :now
            WHERE b.user_id = :user_id
            GROUP BY b.category, b.monthly_limit
            ORDER BY b.category
        """),
        {"user_id": user_id, "month_start": month_start, "now": now},
    )
    rows = result.mappings().all()

    return [
        {
            "category": r["category"],
            "monthly_limit": float(r["monthly_limit"]),
            "spent": float(r["spent"]),
            "remaining": float(r["monthly_limit"]) - float(r["spent"]),
            "percentage_used": round(float(r["spent"]) / float(r["monthly_limit"]) * 100, 1)
            if float(r["monthly_limit"]) > 0
            else 0,
            "is_over_budget": float(r["spent"]) > float(r["monthly_limit"]),
        }
        for r in rows
    ]
