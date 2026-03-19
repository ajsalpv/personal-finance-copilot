import operator
from typing import Annotated, TypedDict, List
from langchain_core.messages import AnyMessage

class AgentState(TypedDict):
    """
    Represents the conversational state per user session.
    """
    messages: Annotated[List[AnyMessage], operator.add]
    user_id: str
    memory_context: str
    is_active: bool
    last_active_time: float
    image_base64: str | None
    advisory_briefs: List[dict] | None
    plan: List[str] | None
    thought: str | None
    next: str | None
