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
from app.services.news_intelligence import NewsIntelligenceService
from app.services.location_service import LocationService

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

# --- PREDICTIVE NODES ---

async def advisory_triage(state: AgentState):
    """[PHASE 15+] Triages global news for personal relevance."""
    news = await NewsIntelligenceService.fetch_global_risks()
    mock_stats = {"top_categories": ["fuel", "groceries", "tech"]}
    
    advisories = await NewsIntelligenceService.analyze_impact(news, state.get("memory_context", {}))
    relevant_briefs = await NewsIntelligenceService.filter_relevance(advisories, mock_stats)
    
    return {"advisory_briefs": relevant_briefs}

async def travel_intelligence(state: AgentState):
    """[PHASE 18] Detects travel anomalies and updates context."""
    user_id = state.get("user_id", "default_user")
    async with async_session_factory() as db:
        anomaly = await LocationService.detect_travel_anomaly(db, user_id)
        if anomaly and anomaly.get("is_traveling"):
            state["messages"].append(AIMessage(content=f"System Alert: Travel anomaly detected. You appear to be in {anomaly['current_city']}. Would you like to update your travel plan?"))
    return state

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

async def self_reflection(state: AgentState):
    """Analyzes the response and user feedback for self-improvement."""
    user_id = state.get("user_id", "default_user")
    last_msg = state["messages"][-1].content
    
    if any(keyword in last_msg.lower() for keyword in ["don't", "stop", "never", "always", "prefer"]):
        async with async_session_factory() as db:
            await extract_and_store_facts(db, user_id, f"USER PREFERENCE CORRECTION: {last_msg}")
            
    return state

# --- GRAPH DEFINITION ---

workflow = StateGraph(AgentState)

workflow.add_node("memory_entry", memory_entry)
workflow.add_node("supervisor", supervisor)
workflow.add_node("call", call_specialist)
workflow.add_node("vision", vision_expert)
workflow.add_node("system", system_manager)
workflow.add_node("tools", ToolNode(tools=all_tools))
workflow.add_node("reflect", self_reflection)
workflow.add_node("triage", advisory_triage)
workflow.add_node("travel", travel_intelligence)

workflow.add_edge(START, "memory_entry")
workflow.add_edge("memory_entry", "travel")
workflow.add_edge("travel", "triage")
workflow.add_edge("triage", "supervisor")

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
    return "reflect"

workflow.add_conditional_edges("system", should_continue)
workflow.add_edge("tools", "system")
workflow.add_edge("call", "reflect")
workflow.add_edge("vision", "reflect")
workflow.add_edge("reflect", END)

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
    
    memory_recalled = bool(result.get("memory_context") and result["memory_context"].strip())
    
    return {
        "reply": result["messages"][-1].content,
        "memory_recalled": memory_recalled
    }
