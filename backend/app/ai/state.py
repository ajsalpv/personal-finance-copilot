import operator
from typing import Annotated, TypedDict, List
from langchain_core.messages import AnyMessage

class AgentState(TypedDict):
    """
    Represents the conversational state per user session.
    - messages: Full list of messages (user inputs, AI responses, tool results).
      Used Annotated with operator.add so elements are appended, not overwritten.
    - is_active: Flow control (awake/asleep).
    - last_active_time: Timestamp for the 30-sec idle timeout.
    """
    messages: Annotated[List[AnyMessage], operator.add]
    is_active: bool
    last_active_time: float
