"""
Export Router — Data export endpoints (CSV, JSON, encrypted backup).
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security.auth import get_current_user
from app.services import export_service

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/transactions")
async def export_transactions(
    format: str = Query("csv", regex="^(csv|json)$"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export transactions in CSV or JSON format."""
    if format == "csv":
        csv_content = await export_service.export_transactions_csv(
            db, str(current_user["id"])
        )
        return PlainTextResponse(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions.csv"},
        )
    else:
        data = await export_service.export_all_json(db, str(current_user["id"]))
        return JSONResponse(content={"transactions": data.get("transactions", [])})


@router.get("/all")
async def export_all(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all user data as JSON."""
    data = await export_service.export_all_json(db, str(current_user["id"]))
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=nova_backup.json"},
    )


@router.get("/backup")
async def export_backup(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all data as an AES-encrypted backup."""
    encrypted = await export_service.export_encrypted_backup(
        db, str(current_user["id"])
    )
    return PlainTextResponse(
        content=encrypted,
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=nova_backup.enc"},
    )
