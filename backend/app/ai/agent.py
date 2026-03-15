from typing import Annotated, Literal, TypedDict, List, Dict, Any
from datetime import datetime, timezone, timedelta
import json
import logging
import os
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

logger = logging.getLogger(__name__)
settings = get_settings()

def get_llm(with_tools=None):
    """Returns a fresh LLM instance with latest settings (force refreshed)."""
    # Force reload environment to catch dynamic .env changes
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    key = os.getenv("GROQ_API_KEY")
    if not key or not key.startswith("gsk_"):
        current_settings = get_settings()
        key = current_settings.GROQ_API_KEY
    
    if key:
        key = key.strip().replace('"', '').replace("'", "")

    # HEX DIAGNOSTIC
    import binascii
    key_hex = binascii.hexlify(key.encode()).decode() if key else "None"
    with open("key_diag.log", "a") as f:
        f.write(f"{datetime.now()}: {key[:10]}... HEX={key_hex}\n")

    _llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=key,
        temperature=0,
    )
    if with_tools:
        return _llm.bind_tools(with_tools)
    return _llm

# --- SPECIALIST NODES ---

async def call_specialist(state: AgentState):
    """Handles call-related queries."""
    memory_context = state.get("memory_context", "")
    messages = [
        get_call_concierge_prompt(),
        SystemMessage(content=f"LONG-TERM CONTEXT:\n{memory_context}")
    ] + state["messages"]
    response = await get_llm().ainvoke(messages)
    return {"messages": [response]}

async def system_manager(state: AgentState):
    """General assistant logic with tool access."""
    try:
        llm_with_tools = get_llm(with_tools=all_tools)
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
    except Exception as e:
        logger.error(f"System Manager Node Error: {repr(e)}")
        return {"messages": [AIMessage(content=f"SYSTEM_ERROR: {repr(e)}")]}

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
    response = await get_llm().ainvoke(messages)
    return {"messages": [response]}

# --- PREDICTIVE NODES ---

async def advisory_triage(state: AgentState):
    """[PHASE 15+] Triages global news for personal relevance with dynamic context."""
    try:
        user_id = state.get("user_id", "default_user")
        
        # 1. Dynamically Assemble Context
        async with async_session_factory() as db:
            loc_history = await LocationService.get_recent_locations(db, user_id, limit=1)
            current_city = loc_history[0]["city"] if loc_history else "Unknown"
            
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=30)
            from app.services.transaction_service import get_spending_summary
            summary = await get_spending_summary(db, user_id, start, now)
            top_cats = [c["category"] for c in summary.get("by_category", [])[:5]]

        user_context = {
            "location": current_city,
            "top_categories": top_cats if top_cats else ["General"],
            "current_city": current_city
        }
        
        news = await NewsIntelligenceService.fetch_global_risks()
        advisories = await NewsIntelligenceService.analyze_impact(news, user_context)
        relevant_briefs = await NewsIntelligenceService.filter_relevance(advisories, user_context)
        
        return {"advisory_briefs": relevant_briefs}
    except Exception as e:
        logger.error(f"Advisory Triage Node Error: {e}")
        return {"advisory_briefs": []}

async def travel_intelligence(state: AgentState):
    """[PHASE 18] Detects travel anomalies and updates context."""
    try:
        user_id = state.get("user_id", "default_user")
        async with async_session_factory() as db:
            anomaly = await LocationService.detect_travel_anomaly(db, user_id)
            if anomaly and anomaly.get("is_traveling"):
                state["messages"].append(AIMessage(content=f"System Alert: Travel anomaly detected. You appear to be in {anomaly['current_city']}. {anomaly.get('reasoning', '')}"))
    except Exception as e:
        logger.error(f"Travel Intelligence Node Error: {e}")
    return state

# --- SUPERVISOR & AUTO-ROUTING ---

async def supervisor(state: AgentState):
    """The central brain that routes to specialists using LLM reasoning."""
    try:
        system_prompt = """You are the Callista Supervisor. Analyze the user request and determine the best specialist.
        Specialists:
        - 'call': Managing phone calls, answering calls, concierge services.
        - 'vision': Camera, screen, image recognition, narration of surroundings.
        - 'system': Finance, budgeting, tasks, reminders, memory, general questions.
        
        RESPOND IN STRICT JSON:
        {"next": "call/vision/system", "reasoning": "short explanation"}
        Only return JSON."""
        
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = await get_llm().ainvoke(messages)
        
        cleaned = response.content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(cleaned)
        return {"next": data.get("next", "system")}
    except Exception as e:
        logger.error(f"Supervisor Node Error: {e}")
        return {"next": "system"}

async def self_reflection(state: AgentState):
    """
    [REFLECTION AGENT]
    Analyzes the user's last message to learn preferences or corrections.
    Replaces keyword-based extraction with LLM reasoning.
    """
    user_id = state.get("user_id", "default_user")
    last_msg = state["messages"][-1].content
    
    system_prompt = """You are a Preference Learning Agent. 
    Analyze the user's message. Is the user expressing a long-term preference, a correction to your behavior, or an important life fact?
    Examples: "Never use red for alerts", "I prefer Zomato over Swiggy", "My sister's name is Maya".
    
    RESPOND IN STRICT JSON:
    {"is_preference": true/false, "fact": "The extracted fact or preference"}
    Only return JSON."""
    
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=last_msg)]
    response = await get_llm().ainvoke(messages)
    
    try:
        cleaned = response.content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(cleaned)
        if data.get("is_preference"):
            async with async_session_factory() as db:
                await extract_and_store_facts(db, user_id, data["fact"])
                logger.info(f"Learned new preference: {data['fact']}")
    except Exception as e:
        logger.error(f"Reflection Agent failed: {e}")
            
    return state

# --- UTILS ---

async def memory_entry(state: AgentState):
    """Pre-processes the message to fetch LTM."""
    user_id = state.get("user_id", "default_user")
    async with async_session_factory() as db:
        memory_context = await get_long_term_memory(db, user_id)
        # Fact extraction is now handled by the Reflection node at the end of the loop
    return {"memory_context": memory_context}

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
    last_message = state["messages"][-1]
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
    try:
        config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
        result = await agent_executor.ainvoke(
            {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
            },
            config=config,
        )
        
        memory_recalled = bool(result.get("memory_context") and result["memory_context"].strip())
        
        return {
            "reply": result["messages"][-1].content,
            "memory_recalled": memory_recalled
        }
    except Exception as e:
        import traceback
        logger.error(f"FATAL AGENT ERROR: {e}\n{traceback.format_exc()}")
        raise e
