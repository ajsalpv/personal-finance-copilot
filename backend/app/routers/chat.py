from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.security.auth import get_current_user
from app.schemas.user import UserResponse
from app.ai.agent import process_message
import uuid

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None

class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    memory_recalled: bool = False

@router.post("/message", response_model=ChatResponse)
async def chat_with_callista(
    payload: ChatRequest = Body(...),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Send a natural language message to the AI Agent (Callista).
    If no thread_id is provided, a new conversational session is started.
    """
    # Create or reuse a thread ID for LangGraph memory persistence
    thread_id = payload.thread_id if payload.thread_id else str(uuid.uuid4())
    user_id = str(current_user.id)
    
    try:
        agent_result = await process_message(
            thread_id=thread_id,
            user_id=user_id,
            message=payload.message
        )
        return ChatResponse(
            reply=agent_result["reply"], 
            thread_id=thread_id,
            memory_recalled=agent_result["memory_recalled"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Agent Error: {str(e)}")
