"""
Budgets Router — Budget management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.security.auth import get_current_user
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse, BudgetStatusResponse
from app.services import budget_service

router = APIRouter()


@router.post("", response_model=BudgetResponse)
async def create_budget(
    body: BudgetCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a budget for a category."""
    return await budget_service.create_budget(
        db, str(current_user["id"]), body.category, body.monthly_limit
    )


@router.get("", response_model=List[BudgetResponse])
async def list_budgets(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all budgets."""
    return await budget_service.get_budgets(db, str(current_user["id"]))


@router.get("/status", response_model=List[BudgetStatusResponse])
async def get_budget_status(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current month spending vs budget for each category."""
    return await budget_service.get_budget_status(db, str(current_user["id"]))


@router.put("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    body: BudgetUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a budget's monthly limit."""
    result = await budget_service.update_budget(
        db, str(current_user["id"]), budget_id, body.monthly_limit
    )
    if not result:
        raise HTTPException(status_code=404, detail="Budget not found")
    return result


@router.delete("/{budget_id}")
async def delete_budget(
    budget_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a budget."""
    deleted = await budget_service.delete_budget(db, str(current_user["id"]), budget_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget deleted"}
