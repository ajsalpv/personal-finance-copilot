"""
Categories Router — Category management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.security.auth import get_current_user
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse])
async def list_categories(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all categories for the user (including defaults)."""
    result = await db.execute(
        text("""
            SELECT * FROM categories 
            WHERE user_id = :user_id OR user_id IS NULL
            ORDER BY is_default DESC, name ASC
        """),
        {"user_id": str(current_user["id"])},
    )
    return [
        CategoryResponse(id=str(r["id"]), name=r["name"], type=r["type"],
                         icon=r["icon"], is_default=r["is_default"],
                         created_at=r["created_at"])
        for r in result.mappings().all()
    ]


@router.post("", response_model=CategoryResponse)
async def create_category(
    body: CategoryCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a custom category."""
    result = await db.execute(
        text("""
            INSERT INTO categories (user_id, name, type, icon, is_default)
            VALUES (:user_id, :name, :type, :icon, FALSE)
            RETURNING id, name, type, icon, is_default, created_at
        """),
        {
            "user_id": str(current_user["id"]),
            "name": body.name, "type": body.type, "icon": body.icon,
        },
    )
    await db.commit()
    r = result.mappings().first()
    return CategoryResponse(
        id=str(r["id"]), name=r["name"], type=r["type"],
        icon=r["icon"], is_default=r["is_default"], created_at=r["created_at"],
    )


@router.put("/{cat_id}", response_model=CategoryResponse)
async def update_category(
    cat_id: str,
    body: CategoryUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a custom category."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = cat_id
    updates["user_id"] = str(current_user["id"])

    result = await db.execute(
        text(f"""
            UPDATE categories SET {set_clauses}
            WHERE id = :id AND user_id = :user_id AND is_default = FALSE
            RETURNING id, name, type, icon, is_default, created_at
        """),
        updates,
    )
    await db.commit()
    r = result.mappings().first()
    if not r:
        raise HTTPException(status_code=404, detail="Category not found or cannot update defaults")
    return CategoryResponse(
        id=str(r["id"]), name=r["name"], type=r["type"],
        icon=r["icon"], is_default=r["is_default"], created_at=r["created_at"],
    )


@router.delete("/{cat_id}")
async def delete_category(
    cat_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom category (cannot delete defaults)."""
    result = await db.execute(
        text("DELETE FROM categories WHERE id = :id AND user_id = :user_id AND is_default = FALSE"),
        {"id": cat_id, "user_id": str(current_user["id"])},
    )
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Category not found or cannot delete defaults")
    return {"message": "Category deleted"}
