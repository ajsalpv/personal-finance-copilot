from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union

class ACPMessage(BaseModel):
    """
    Standard Agent Communication Protocol (ACP) Message.
    Used for A2A (Agent-to-Agent) communication.
    """
    sender: str = Field(..., description="The ID of the sending agent")
    recipient: str = Field(..., description="The ID of the target agent")
    message_type: str = Field(..., description="Type of message: 'request', 'response', 'handover', 'broadcast'")
    content: Dict[str, Any] = Field(..., description="The payload of the message")
    timestamp: float = Field(default_factory=lambda: 0.0) # Should be set by sender

class ACPRequest(ACPMessage):
    message_type: str = "request"
    task_id: str = Field(..., description="Unique ID for tracking the task")

class ACPResponse(ACPMessage):
    message_type: str = "response"
    task_id: str = Field(..., description="ID of the original request")
    status: str = Field(..., description="'success', 'error', 'partial'")

class ACPHandover(ACPMessage):
    """Used when one agent delegates a task to another."""
    message_type: str = "handover"
    context: Optional[str] = Field(None, description="Previous conversation context")
