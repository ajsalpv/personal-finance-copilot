"""
Export Service — Data export in CSV, JSON, and encrypted backup formats.
"""
import csv
import io
import json
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.encryption import encrypt, decrypt


async def export_transactions_csv(db: AsyncSession, user_id: str) -> str:
    """Export transactions as CSV."""
    result = await db.execute(
        text("SELECT * FROM transactions WHERE user_id = :user_id ORDER BY date DESC"),
        {"user_id": user_id},
    )
    rows = result.mappings().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Date", "Type", "Amount", "Category", "Merchant", "Payment Method", "Note", "Source"
    ])

    for r in rows:
        merchant = decrypt(r["merchant_name"]) if r["merchant_name"] else ""
        note = decrypt(r["note"]) if r["note"] else ""
        writer.writerow([
            r["date"].isoformat() if r["date"] else "",
            r["transaction_type"],
            float(r["amount"]),
            r["category"] or "",
            merchant,
            r["payment_method"] or "",
            note,
            r["source"] or "",
        ])

    return output.getvalue()


async def export_all_json(db: AsyncSession, user_id: str) -> dict:
    """Export all user data as JSON."""
    data = {}

    # Transactions
    result = await db.execute(
        text("SELECT * FROM transactions WHERE user_id = :user_id ORDER BY date DESC"),
        {"user_id": user_id},
    )
    transactions = []
    for r in result.mappings().all():
        row = dict(r)
        if row.get("merchant_name"):
            row["merchant_name"] = decrypt(row["merchant_name"])
        if row.get("person_name"):
            row["person_name"] = decrypt(row["person_name"])
        if row.get("upi_id"):
            row["upi_id"] = decrypt(row["upi_id"])
        if row.get("note"):
            row["note"] = decrypt(row["note"])
        # Convert non-serializable types
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
            elif hasattr(v, "hex"):  # UUID
                row[k] = str(v)
            elif isinstance(v, (int, float, str, bool, type(None))):
                pass
            else:
                row[k] = str(v)
        transactions.append(row)
    data["transactions"] = transactions

    # Tasks
    result = await db.execute(
        text("SELECT * FROM tasks WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    data["tasks"] = _serialize_rows(result.mappings().all())

    # Memories
    result = await db.execute(
        text("SELECT * FROM memories WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    memories = []
    for r in result.mappings().all():
        row = dict(r)
        if row.get("content"):
            row["content"] = decrypt(row["content"])
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
            elif hasattr(v, "hex"):
                row[k] = str(v)
            elif isinstance(v, (int, float, str, bool, type(None), list)):
                pass
            else:
                row[k] = str(v)
        memories.append(row)
    data["memories"] = memories

    # Budgets
    result = await db.execute(
        text("SELECT * FROM budgets WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    data["budgets"] = _serialize_rows(result.mappings().all())

    # Categories
    result = await db.execute(
        text("SELECT * FROM categories WHERE user_id = :user_id OR user_id IS NULL"),
        {"user_id": user_id},
    )
    data["categories"] = _serialize_rows(result.mappings().all())

    return data


async def export_encrypted_backup(db: AsyncSession, user_id: str) -> str:
    """Export all data as an encrypted JSON string."""
    data = await export_all_json(db, user_id)
    json_str = json.dumps(data, indent=2)
    return encrypt(json_str)


def _serialize_rows(rows) -> list:
    """Convert SQLAlchemy rows to JSON-safe dicts."""
    serialized = []
    for r in rows:
        row = dict(r)
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
            elif hasattr(v, "hex"):
                row[k] = str(v)
            elif isinstance(v, (int, float, str, bool, type(None), list)):
                pass
            else:
                row[k] = str(v)
        serialized.append(row)
    return serialized
