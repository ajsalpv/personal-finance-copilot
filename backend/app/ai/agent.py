import logging
from typing import Annotated, Literal
from datetime import datetime, timezone

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode

from app.config import get_settings
from app.ai.state import AgentState
from app.ai.tools import all_tools

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize the LLM
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=settings.GROQ_API_KEY,
    temperature=0,
)

# Bind tools to the LLM
llm_with_tools = llm.bind_tools(all_tools)

def call_model(state: AgentState, config: RunnableConfig) -> dict:
    """The main LLM node that decides the next action."""
    messages = state["messages"]
    
    # Prepend the system prompt if not present
    system_prompt = SystemMessage(
        content=(
            "You are a helpful, private AI life assistant known as Callista (or Zafira). "
            "You can manage finances, track tasks, and strictly remember contextual details.\n\n"
            "CRITICAL RULES:\n"
            "1. NEVER make up information. Use tools exclusively to record or retrieve data.\n"
            "2. If the user asks to log an expense or income but does not provide both the AMOUNT and the REASON, "
            "do NOT call the tool. Ask them for the missing detail first.\n"
            "3. If the user only provides an amount, or only provides a reason, use your conversational memory "
            "to deduce the missing piece if they just told you, otherwise ask.\n"
            "4. Keep responses extremely natural, short, and conversational. Do not list JSON."
        )
    )
    
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [system_prompt] + messages
        
    response = llm_with_tools.invoke(messages, config)
    
    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Determines whether to call a tool or end the turn."""
    messages = state.get("messages", [])
    last_message = messages[-1]
    
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return "__end__"

# Create the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools=all_tools))

# Add edges
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

from langgraph.checkpoint.memory import MemorySaver

# Add MemorySaver for context persistence across turns
memory = MemorySaver()

# Compile the graph
agent_executor = workflow.compile(checkpointer=memory)

async def process_message(thread_id: str, user_id: str, message: str) -> str:
    """Entry point for the Telegram bot to chat with the AI."""
    config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
    
    # Run the graph
    result = await agent_executor.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )
    
    # The last message is the AI's response
    return result["messages"][-1].content

