"""
Tasks Router — Task & Reminder management endpoints.
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security.auth import get_current_user
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.services import task_service
from app.services import timeline_service

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse)
async def create_task(
    body: TaskCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task or reminder."""
    task = await task_service.create_task(
        db=db,
        user_id=str(current_user["id"]),
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        priority=body.priority.value,
        recurrence=body.recurrence,
    )

    # Auto-create timeline event
    await timeline_service.create_timeline_event(
        db=db,
        user_id=str(current_user["id"]),
        event_type="task",
        description=f"📋 New task: {body.title}",
        source="tasks",
        metadata={"task_id": task["id"], "priority": body.priority.value},
    )

    return task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tasks with optional status/priority filters."""
    return await task_service.get_tasks(
        db, str(current_user["id"]), status=status, priority=priority,
        limit=limit, offset=offset,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific task."""
    task = await task_service.get_task_by_id(db, str(current_user["id"]), task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    body: TaskUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a task."""
    updates = body.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"]:
        updates["status"] = updates["status"].value
    if "priority" in updates and updates["priority"]:
        updates["priority"] = updates["priority"].value

    task = await task_service.update_task(
        db, str(current_user["id"]), task_id, updates
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task."""
    deleted = await task_service.delete_task(db, str(current_user["id"]), task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted"}
