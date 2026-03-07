"""
Transaction Service — Business logic for income/expense tracking.
"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.encryption import encrypt, decrypt, mask_identifier


async def create_transaction(
    db: AsyncSession,
    user_id: str,
    amount: float,
    transaction_type: str,
    merchant_name: Optional[str] = None,
    person_name: Optional[str] = None,
    upi_id: Optional[str] = None,
    category: Optional[str] = None,
    payment_method: str = "cash",
    date: Optional[datetime] = None,
    source: str = "manual",
    note: Optional[str] = None,
) -> dict:
    """Create a new transaction with encrypted sensitive fields."""
    if date is None:
        date = datetime.now(timezone.utc)

    # Encrypt sensitive fields
    enc_merchant = encrypt(merchant_name) if merchant_name else None
    enc_person = encrypt(person_name) if person_name else None
    enc_upi = encrypt(upi_id) if upi_id else None
    enc_note = encrypt(note) if note else None

    result = await db.execute(
        text("""
            INSERT INTO transactions 
            (user_id, amount, transaction_type, merchant_name, person_name, 
             upi_id, category, payment_method, date, source, note)
            VALUES (:user_id, :amount, :type, :merchant, :person, 
                    :upi, :category, :payment, :date, :source, :note)
            RETURNING id, amount, transaction_type, merchant_name, person_name,
                      upi_id, category, payment_method, date, source, note, created_at
        """),
        {
            "user_id": user_id, "amount": amount, "type": transaction_type,
            "merchant": enc_merchant, "person": enc_person, "upi": enc_upi,
            "category": category, "payment": payment_method,
            "date": date, "source": source, "note": enc_note,
        },
    )
    await db.commit()
    row = result.mappings().first()
    return _decrypt_transaction(dict(row))


async def get_transactions(
    db: AsyncSession,
    user_id: str,
    transaction_type: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[dict]:
    """Get user transactions with optional filters."""
    query = "SELECT * FROM transactions WHERE user_id = :user_id"
    params: dict = {"user_id": user_id}

    if transaction_type:
        query += " AND transaction_type = :type"
        params["type"] = transaction_type
    if category:
        query += " AND category = :category"
        params["category"] = category
    if start_date:
        query += " AND date >= :start"
        params["start"] = start_date
    if end_date:
        query += " AND date <= :end"
        params["end"] = end_date

    query += " ORDER BY date DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    result = await db.execute(text(query), params)
    rows = result.mappings().all()
    return [_decrypt_transaction(dict(r)) for r in rows]


async def get_transaction_by_id(db: AsyncSession, user_id: str, txn_id: str) -> Optional[dict]:
    result = await db.execute(
        text("SELECT * FROM transactions WHERE id = :id AND user_id = :user_id"),
        {"id": txn_id, "user_id": user_id},
    )
    row = result.mappings().first()
    return _decrypt_transaction(dict(row)) if row else None


async def update_transaction(db: AsyncSession, user_id: str, txn_id: str, updates: dict) -> Optional[dict]:
    # Encrypt fields if present
    if "merchant_name" in updates and updates["merchant_name"]:
        updates["merchant_name"] = encrypt(updates["merchant_name"])
    if "person_name" in updates and updates["person_name"]:
        updates["person_name"] = encrypt(updates["person_name"])
    if "upi_id" in updates and updates["upi_id"]:
        updates["upi_id"] = encrypt(updates["upi_id"])
    if "note" in updates and updates["note"]:
        updates["note"] = encrypt(updates["note"])

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates if updates[k] is not None)
    if not set_clauses:
        return await get_transaction_by_id(db, user_id, txn_id)

    params = {k: v for k, v in updates.items() if v is not None}
    params["id"] = txn_id
    params["user_id"] = user_id

    await db.execute(
        text(f"UPDATE transactions SET {set_clauses} WHERE id = :id AND user_id = :user_id"),
        params,
    )
    await db.commit()
    return await get_transaction_by_id(db, user_id, txn_id)


async def delete_transaction(db: AsyncSession, user_id: str, txn_id: str) -> bool:
    result = await db.execute(
        text("DELETE FROM transactions WHERE id = :id AND user_id = :user_id"),
        {"id": txn_id, "user_id": user_id},
    )
    await db.commit()
    return result.rowcount > 0


async def get_spending_summary(
    db: AsyncSession, user_id: str, start_date: datetime, end_date: datetime
) -> dict:
    """Get spending summary grouped by category for a date range."""
    result = await db.execute(
        text("""
            SELECT 
                category,
                transaction_type,
                SUM(amount) as total,
                COUNT(*) as count
            FROM transactions 
            WHERE user_id = :user_id AND date >= :start AND date <= :end
            GROUP BY category, transaction_type
            ORDER BY total DESC
        """),
        {"user_id": user_id, "start": start_date, "end": end_date},
    )
    rows = result.mappings().all()

    total_income = sum(r["total"] for r in rows if r["transaction_type"] == "income")
    total_expense = sum(r["total"] for r in rows if r["transaction_type"] == "expense")

    by_category = []
    for r in rows:
        if r["transaction_type"] == "expense" and total_expense > 0:
            by_category.append({
                "category": r["category"] or "Uncategorized",
                "total": float(r["total"]),
                "count": r["count"],
                "percentage": round(float(r["total"]) / float(total_expense) * 100, 1),
            })

    return {
        "total_income": float(total_income),
        "total_expense": float(total_expense),
        "net": float(total_income - total_expense),
        "by_category": by_category,
    }


async def get_daily_spending(
    db: AsyncSession, user_id: str, days: int = 30
) -> List[dict]:
    """Get daily spending totals for the last N days."""
    result = await db.execute(
        text("""
            SELECT 
                DATE(date) as day,
                SUM(amount) as total
            FROM transactions 
            WHERE user_id = :user_id 
              AND transaction_type = 'expense'
              AND date >= CURRENT_DATE - INTERVAL '1 day' * :days
            GROUP BY DATE(date)
            ORDER BY day ASC
        """),
        {"user_id": user_id, "days": days},
    )
    rows = result.fetchall()
    return [{"date": str(r[0]), "amount": float(r[1])} for r in rows]


def _decrypt_transaction(row: dict) -> dict:
    """Decrypt sensitive fields in a transaction row."""
    if row.get("merchant_name"):
        row["merchant_name"] = decrypt(row["merchant_name"])
    if row.get("person_name"):
        row["person_name"] = decrypt(row["person_name"])
    if row.get("upi_id"):
        raw_upi = decrypt(row["upi_id"])
        row["upi_id"] = mask_identifier(raw_upi)
    if row.get("note"):
        row["note"] = decrypt(row["note"])
    # Convert UUID to string
    row["id"] = str(row["id"])
    return row
