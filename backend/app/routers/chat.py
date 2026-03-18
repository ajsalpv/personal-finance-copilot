from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.security.auth import get_current_user
from app.schemas.user import UserResponse
from app.ai.agent import process_message
from app.services import chat_service
from app.database import get_db
import uuid

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    image_base64: str | None = None

class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    memory_recalled: bool = False
    user_message_id: str
    bot_message_id: str

@router.post("/message", response_model=ChatResponse)
async def chat_with_callista(
    payload: ChatRequest = Body(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a natural language message to the AI Agent (Callista).
    """
    thread_id = payload.thread_id if payload.thread_id else str(uuid.uuid4())
    user_id = str(current_user["id"])
    
    # 1. Save User Message
    user_msg = await chat_service.save_chat_message(
        db, user_id, "user", payload.message, thread_id
    )
    
    try:
        # 2. Process with AI
        agent_result = await process_message(
            thread_id=thread_id,
            user_id=user_id,
            message=payload.message,
            image_base64=payload.image_base64
        )
        
        reply = agent_result["reply"]
        memory_recalled = agent_result["memory_recalled"]
        
        # 3. Save Bot Response
        bot_msg = await chat_service.save_chat_message(
            db, user_id, "bot", reply, thread_id, memory_recalled
        )
        
        return ChatResponse(
            reply=reply, 
            thread_id=thread_id,
            memory_recalled=memory_recalled,
            user_message_id=str(user_msg["id"]),
            bot_message_id=str(bot_msg["id"])
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Agent Error: {str(e)}")

@router.get("/history")
async def get_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch stored chat history for the user."""
    history = await chat_service.get_chat_history(db, str(current_user["id"]))
    return {"history": history}

@router.delete("/history")
async def clear_history(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all chat history for the user."""
    success = await chat_service.delete_chat_history(db, str(current_user["id"]))
    return {"success": success}

@router.post("/delete-messages")
async def delete_messages(
    payload: dict = Body(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete specific messages by IDs."""
    message_ids = payload.get("message_ids", [])
    success = await chat_service.delete_selected_messages(db, str(current_user["id"]), message_ids)
    return {"success": success}
