"""
Memories Router — Knowledge/Memory storage and retrieval.
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.security.auth import get_current_user
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryResponse, MemorySearchRequest
from app.services import memory_service

router = APIRouter(prefix="/memories", tags=["Memories"])


@router.post("", response_model=MemoryResponse)
async def create_memory(
    body: MemoryCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Store a new memory/knowledge."""
    return await memory_service.create_memory(
        db=db,
        user_id=str(current_user["id"]),
        content=body.content,
        type=body.type,
        tags=body.tags,
        importance_score=body.importance_score,
    )


@router.get("", response_model=List[MemoryResponse])
async def list_memories(
    type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List stored memories."""
    return await memory_service.get_memories(
        db, str(current_user["id"]), type=type, limit=limit, offset=offset,
    )


@router.post("/search", response_model=List[MemoryResponse])
async def search_memories(
    body: MemorySearchRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search memories by keyword. (Semantic search coming in Phase 2)"""
    return await memory_service.search_memories(
        db, str(current_user["id"]), body.query, body.limit,
    )


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific memory."""
    memory = await memory_service.get_memory_by_id(db, str(current_user["id"]), memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    body: MemoryUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a memory."""
    updates = body.model_dump(exclude_unset=True)
    memory = await memory_service.update_memory(
        db, str(current_user["id"]), memory_id, updates,
    )
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a memory."""
    deleted = await memory_service.delete_memory(db, str(current_user["id"]), memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"message": "Memory deleted"}
