from typing import Annotated, Literal, TypedDict
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq

from app.config import get_settings
from app.database import async_session_factory
from app.ai.state import AgentState
from app.ai.tools import all_tools
from app.ai.specialists.call_agent import get_call_concierge_prompt
from app.ai.specialists.memory_agent import extract_and_store_facts
from app.services.memory_service import get_long_term_memory

settings = get_settings()

# Initialize the LLM
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=settings.GROQ_API_KEY,
    temperature=0,
)

# --- SPECIALIST NODES ---

async def call_specialist(state: AgentState):
    """Handles call-related queries."""
    memory_context = state.get("memory_context", "")
    messages = [
        get_call_concierge_prompt(),
        SystemMessage(content=f"LONG-TERM CONTEXT:\n{memory_context}")
    ] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

async def system_manager(state: AgentState):
    """General assistant logic with tool access."""
    llm_with_tools = llm.bind_tools(all_tools)
    memory_context = state.get("memory_context", "")
    messages = [
        SystemMessage(
            content=(
                "You are Callista, the core system manager. Use tools for finance, system tasks, and memory. "
                "Tone: Premium/Jarvis.\n\n"
                f"LONG-TERM USER CONTEXT:\n{memory_context}"
            )
        )
    ] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}

async def vision_expert(state: AgentState):
    """Handles image and screen-related queries."""
    memory_context = state.get("memory_context", "")
    messages = [
        SystemMessage(
            content=(
                "You are Callista's Vision Expert. Use vision sensors to help the user. "
                f"LTM Context: {memory_context}"
            )
        )
    ] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

# --- SUPERVISOR NODE ---

class RouterState(TypedDict):
    next: Literal["call", "system", "vision", "__end__"]

async def supervisor(state: AgentState):
    """The central brain that routes to specialists."""
    prompt = SystemMessage(
        content=(
            "You are the Callista Supervisor. Analyze the user request and route to the correct specialist.\n"
            "- 'call': If the user wants to handle/answer calls or manage call interactions.\n"
            "- 'vision': If the user mentions seeing something, using the camera, or analyzing the screen.\n"
            "- 'system': For finance, tasks, memory, maps, or general help.\n"
            "Respond with ONLY the name of the specialist."
        )
    )
    messages = [prompt] + state["messages"]
    response = await llm.ainvoke(messages)
    
    route = response.content.lower()
    if "call" in route:
        return {"next": "call"}
    if "vision" in route:
        return {"next": "vision"}
    return {"next": "system"}

async def memory_entry(state: AgentState):
    """Pre-processes the message to fetch LTM and extract facts."""
    user_id = state.get("user_id", "default_user")
    async with async_session_factory() as db:
        memory_context = await get_long_term_memory(db, user_id)
        last_human_msg = state["messages"][-1].content
        await extract_and_store_facts(db, user_id, last_human_msg)
    return {"memory_context": memory_context}

# --- GRAPH DEFINITION ---

workflow = StateGraph(AgentState)

workflow.add_node("memory_entry", memory_entry)
workflow.add_node("supervisor", supervisor)
workflow.add_node("call", call_specialist)
workflow.add_node("vision", vision_expert)
workflow.add_node("system", system_manager)
workflow.add_node("tools", ToolNode(tools=all_tools))

workflow.add_edge(START, "memory_entry")
workflow.add_edge("memory_entry", "supervisor")

workflow.add_conditional_edges(
    "supervisor",
    lambda x: x.get("next"),
    {
        "call": "call",
        "vision": "vision",
        "system": "system",
    }
)

def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END

workflow.add_conditional_edges("system", should_continue)
workflow.add_edge("tools", "system")
workflow.add_edge("call", END)
workflow.add_edge("vision", END)

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
agent_executor = workflow.compile(checkpointer=memory)

async def process_message(thread_id: str, user_id: str, message: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent_executor.ainvoke(
        {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "memory_context": "",
            "is_active": True,
            "last_active_time": 0.0
        },
        config=config,
    )
    
    # Check if memory was recalled (context wasn't empty)
    memory_recalled = bool(result.get("memory_context") and result["memory_context"].strip())
    
    return {
        "reply": result["messages"][-1].content,
        "memory_recalled": memory_recalled
    }

