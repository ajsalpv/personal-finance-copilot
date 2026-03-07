"""
Timeline Router — Daily life timeline endpoints.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security.auth import get_current_user
from app.schemas.timeline import TimelineEventCreate, TimelineEventResponse
from app.services import timeline_service

router = APIRouter(prefix="/timeline", tags=["Timeline"])


@router.get("", response_model=List[TimelineEventResponse])
async def get_timeline(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get timeline events. Defaults to today if no dates specified.
    """
    if start_date is None:
        now = datetime.now(timezone.utc)
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if end_date is None:
        end_date = start_date + timedelta(days=1)

    return await timeline_service.get_timeline(
        db, str(current_user["id"]),
        start_date=start_date, end_date=end_date,
        event_type=event_type, limit=limit,
    )


@router.post("", response_model=TimelineEventResponse)
async def create_timeline_event(
    body: TimelineEventCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a timeline event."""
    return await timeline_service.create_timeline_event(
        db=db,
        user_id=str(current_user["id"]),
        event_type=body.event_type,
        description=body.description,
        timestamp=body.timestamp,
        source=body.source,
        metadata=body.metadata,
    )


@router.delete("/{event_id}")
async def delete_timeline_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a timeline event."""
    from fastapi import HTTPException
    deleted = await timeline_service.delete_timeline_event(
        db, str(current_user["id"]), event_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Timeline event deleted"}
