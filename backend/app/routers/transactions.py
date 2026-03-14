"""
Transactions Router — Income & Expense CRUD endpoints.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security.auth import get_current_user
from app.schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionResponse, SpendingSummaryResponse,
)
from app.services import transaction_service
from app.services import timeline_service

router = APIRouter()


@router.post("", response_model=TransactionResponse)
async def create_transaction(
    body: TransactionCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log a new income or expense transaction."""
    txn = await transaction_service.create_transaction(
        db=db,
        user_id=str(current_user["id"]),
        amount=body.amount,
        transaction_type=body.transaction_type.value,
        merchant_name=body.merchant_name,
        person_name=body.person_name,
        upi_id=body.upi_id,
        category=body.category,
        payment_method=body.payment_method,
        date=body.date,
        source=body.source,
        note=body.note,
    )

    # Auto-create timeline event
    desc = f"{'💰' if body.transaction_type.value == 'income' else '💸'} "
    desc += f"₹{body.amount}"
    if body.merchant_name:
        desc += f" at {body.merchant_name}"
    if body.category:
        desc += f" ({body.category})"

    await timeline_service.create_timeline_event(
        db=db,
        user_id=str(current_user["id"]),
        event_type=body.transaction_type.value,
        description=desc,
        timestamp=body.date or datetime.now(timezone.utc),
        source="finance",
        metadata={"transaction_id": txn["id"], "amount": body.amount},
    )

    return txn


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    transaction_type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List transactions with optional filters."""
    return await transaction_service.get_transactions(
        db=db,
        user_id=str(current_user["id"]),
        transaction_type=transaction_type,
        category=category,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=SpendingSummaryResponse)
async def get_summary(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get spending summary for a date range."""
    summary = await transaction_service.get_spending_summary(
        db=db,
        user_id=str(current_user["id"]),
        start_date=start_date,
        end_date=end_date,
    )
    return SpendingSummaryResponse(
        period=f"{start_date.date()} to {end_date.date()}",
        **summary,
    )


@router.get("/stats/daily")
async def get_daily_stats(
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily spending trends for the last N days."""
    return await transaction_service.get_daily_spending(
        db=db,
        user_id=str(current_user["id"]),
        days=days,
    )


@router.get("/{txn_id}", response_model=TransactionResponse)
async def get_transaction(
    txn_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific transaction."""
    txn = await transaction_service.get_transaction_by_id(
        db, str(current_user["id"]), txn_id
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.put("/{txn_id}", response_model=TransactionResponse)
async def update_transaction(
    txn_id: str,
    body: TransactionUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a transaction."""
    updates = body.model_dump(exclude_unset=True)
    if "transaction_type" in updates and updates["transaction_type"]:
        updates["transaction_type"] = updates["transaction_type"].value
    txn = await transaction_service.update_transaction(
        db, str(current_user["id"]), txn_id, updates
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.delete("/{txn_id}")
async def delete_transaction(
    txn_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a transaction."""
    deleted = await transaction_service.delete_transaction(
        db, str(current_user["id"]), txn_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted"}
