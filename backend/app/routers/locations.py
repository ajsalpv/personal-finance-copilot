from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.security.auth import get_current_user
from app.database import get_db
from app.services.location_service import LocationService
from typing import Optional

router = APIRouter()

@router.post("/log")
async def log_current_location(
    latitude: float = Body(...),
    longitude: float = Body(...),
    city: Optional[str] = Body(None),
    locality: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logs the user's current GPS coordinates."""
    try:
        await LocationService.log_location(
            db, str(current_user["id"]), latitude, longitude, city, locality
        )
        return {"status": "success", "message": "Location logged successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_location_history(
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves recent location history for the user."""
    history = await LocationService.get_recent_locations(db, str(current_user["id"]), limit)
    return {"history": history}

@router.get("/anomaly")
async def check_travel_anomaly(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Checks if the user is currently in an unusual location."""
    anomaly = await LocationService.detect_travel_anomaly(db, str(current_user["id"]))
    return {"anomaly": anomaly or {"is_traveling": False}}
