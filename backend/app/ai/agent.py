from typing import Annotated, Literal, TypedDict, List, Dict, Any
from datetime import datetime, timezone, timedelta
import json
import logging
import os
import time
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import get_settings
from app.database import async_session_factory
from app.ai.state import AgentState
from app.ai.tools import all_tools
from app.ai.specialists.call_agent import get_call_concierge_prompt
from app.ai.specialists.memory_agent import extract_and_store_facts
from app.ai.specialists.language_agent import get_language_tutor_prompt
from app.services.memory_service import get_long_term_memory
from app.services.news_intelligence import NewsIntelligenceService
from app.services.location_service import LocationService
from app.ai.protocols.acp import ACPRequest, ACPResponse, ACPHandover

logger = logging.getLogger(__name__)
settings = get_settings()

# --- TOKEN & COST OPTIMIZATION CACHE ---
AI_CACHE = {
    "triage": {"data": None, "expiry": 0},
    "travel": {"data": None, "expiry": 0},
}
CACHE_TTL = 3600  # 1 hour

def get_llm(with_tools=None, model_type="premium"):
    """
    Returns a fresh LLM instance. 
    model_type: 
      - 'premium': llama-3.3-70b (High reasoning, low limits)
      - 'utility': llama-3.1-8b (Fast, high limits, for routing/reflection)
      - 'gemini': gemini-1.5-flash (Highest free limits, great fallback)
    """
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    # Check for Gemini first if requested or as fallback
    google_key = os.getenv("GOOGLE_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    # Force Gemini usage if User requested it via 'gemini' model_type or if Groq key is missing
    if model_type == "gemini" or (not groq_key and google_key):
        if google_key:
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=google_key,
                temperature=0,
            )

    # Default to Groq
    key = groq_key
    if not key or not key.startswith("gsk_"):
        current_settings = get_settings()
        key = current_settings.GROQ_API_KEY
    
    if key:
        key = key.strip().replace('"', '').replace("'", "")

    model_name = "llama-3.3-70b-versatile" if model_type == "premium" else "llama-3.1-8b-instant"
    
    _llm = ChatGroq(
        model=model_name,
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
    # Truncate history to last 10 messages for specialists
    history = state["messages"][-10:]
    plan = state.get("plan", [])
    current_step = plan[0] if plan else "Execute call task"
    
    messages = [
        get_call_concierge_prompt(),
        SystemMessage(content=f"PLAN STEP: {current_step}\nLONG-TERM CONTEXT:\n{memory_context}")
    ] + history
    # Specialist can use premium for better dialogue
    response = await get_llm(model_type="premium").ainvoke(messages)
    return {"messages": [response]}

async def language_expert(state: AgentState):
    """Handles language tutoring and learning."""
    user_id = state.get("user_id", "default_user")
    memory_context = state.get("memory_context", "")
    history = state["messages"][-10:]
    
    # Fetch user level (simulated for now, could be in state)
    user_level = 1 
    
    plan = state.get("plan", [])
    current_step = plan[0] if plan else "Execute language task"
    
    messages = [
        get_language_tutor_prompt(user_level=user_level, language="Russian"),
        SystemMessage(content=f"PLAN STEP: {current_step}\nLONG-TERM CONTEXT:\n{memory_context}")
    ] + history
    
    llm_with_tools = get_llm(with_tools=all_tools, model_type="premium")
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}

async def system_manager(state: AgentState):
    """General assistant logic with tool access (Premium reasoning)."""
    try:
        # Finance and tool calling requires 70B for accuracy
        llm_with_tools = get_llm(with_tools=all_tools, model_type="premium")
        memory_context = state.get("memory_context", "")
        advisories = state.get("advisory_briefs", [])
        
        advisory_text = ""
        if advisories:
            advisory_text = "\n\nREAL-TIME INTELLIGENCE / NEWS:\n" + "\n".join([
                f"- {a['event']}: {a['impact']} (Suggestion: {a['suggestion']})"
                for a in advisories[:3] # Show top 3 for token efficiency
            ])

        # Truncate history to last 15 messages to stay within TPM limits
        history = state["messages"][-15:]

        plan = state.get("plan", [])
        thought = state.get("thought", "")
        current_step = plan[0] if plan else "Execute request"

        messages = [
            SystemMessage(
                content=(
                    "You are Callista (Agentic reasoning mode). Follow the current plan step-by-step.\n"
                    f"STRATEGIC THOUGHT: {thought}\n"
                    f"CURRENT PLAN STEP: {current_step}\n\n"
                    "Use tools for finance, system tasks, memory, and web search. Tone: Premium/Jarvis.\n"
                    "REAL-TIME ACCESS: You HAVE access to real-time news and the LIVE WEB. Call 'search_web' if needed.\n"
                    "CRITICAL: Complete the current task perfectly. If satisfied, your result will be reviewed by the Reflection Agent.\n"
                    f"LONG-TERM USER CONTEXT:\n{memory_context}"
                    f"{advisory_text}"
                )
            )
        ] + history
        
        # If there's an image, add it to the message content for multi-modal reasoning
        image_base64 = state.get("image_base64")
        if image_base64:
             messages[-1] = HumanMessage(
                 content=[
                     {"type": "text", "text": messages[-1].content},
                     {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                 ]
             )

        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"System Manager Node Error: {repr(e)}")
        # If 429 occurs, final fallback is to notify the user or use a utility model
        if "429" in str(e):
             llm_fallback = get_llm(model_type="utility") # Try 8B fallback
             response = await llm_fallback.ainvoke(messages)
             return {"messages": [response]}
        return {"messages": [AIMessage(content=f"SYSTEM_ERROR: {repr(e)}")]}

async def vision_expert(state: AgentState):
    """Handles image and screen-related queries."""
    memory_context = state.get("memory_context", "")
    # Truncate history to last 10 messages for specialists
    history = state["messages"][-10:]
    
    # "Meta Glass" Vision System Message
    system_instr = (
        "You are Callista's Vision Intelligence System. You are current observing the user's environment in real-time. "
        "Describe what you see with a premium, proactive JARVIS-like tone. "
        "Analyze objects, text, and context in the camera frame to assist the user proactively."
    )

    plan = state.get("plan", [])
    current_step = plan[0] if plan else "Analyze environmental context"

    messages = [
        SystemMessage(content=f"{system_instr}\n\nPLAN STEP: {current_step}\nLTM Context: {memory_context}")
    ] + history
    
    # Inject the image if present
    image_base64 = state.get("image_base64")
    if image_base64:
        # Wrap the last human message with the image content
        messages[-1] = HumanMessage(
            content=[
                {"type": "text", "text": messages[-1].content},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
            ]
        )
    
    # Use Gemini for superior vision processing
    response = await get_llm(model_type="gemini").ainvoke(messages)
    return {"messages": [response]}

# --- PREDICTIVE NODES ---

async def advisory_triage(state: AgentState):
    """[PHASE 15+] Triages global news. Optimized with 60-min cache."""
    try:
        now_ts = time.time()
        # 1. Use Cache if valid
        if AI_CACHE["triage"]["data"] and now_ts < AI_CACHE["triage"]["expiry"]:
            logger.info("Using cached Advisory Briefs")
            return {"advisory_briefs": AI_CACHE["triage"]["data"]}

        user_id = state.get("user_id", "default_user")
        
        # 2. Dynamically Assemble Context
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
        
        # 3. Fetch and Analyze (Uses 70B for impact reasoning)
        news = await NewsIntelligenceService.fetch_global_risks()
        advisories = await NewsIntelligenceService.analyze_impact(news, user_context)
        relevant_briefs = await NewsIntelligenceService.filter_relevance(advisories, user_context)
        
        # 4. Update Cache
        AI_CACHE["triage"]["data"] = relevant_briefs
        AI_CACHE["triage"]["expiry"] = now_ts + CACHE_TTL
        
        return {"advisory_briefs": relevant_briefs}
    except Exception as e:
        logger.error(f"Advisory Triage Node Error: {e}")
        return {"advisory_briefs": []}

async def travel_intelligence(state: AgentState):
    """[PHASE 18] Detects travel anomalies. Optimized with 60-min cache."""
    try:
        now_ts = time.time()
        # Check cache (global is fine for now)
        if AI_CACHE["travel"]["data"] and now_ts < AI_CACHE["travel"]["expiry"]:
            return state

        user_id = state.get("user_id", "default_user")
        async with async_session_factory() as db:
            anomaly = await LocationService.detect_travel_anomaly(db, user_id)
            if anomaly and anomaly.get("is_traveling"):
                state["messages"].append(AIMessage(content=f"System Alert: Travel anomaly detected. You appear to be in {anomaly['current_city']}. {anomaly.get('reasoning', '')}"))
                
        AI_CACHE["travel"]["data"] = True
        AI_CACHE["travel"]["expiry"] = now_ts + CACHE_TTL
    except Exception as e:
        logger.error(f"Travel Intelligence Node Error: {e}")
    return state

# --- AGENTIC REASONING NODES ---

async def planner_node(state: AgentState):
    """
    [PLANNING AGENT]
    Breaks down the user request into a step-by-step strategy.
    Uses First Principles thinking.
    """
    try:
        last_msg = state["messages"][-1].content
        system_prompt = """You are the Callista Strategic Planner. 
        Analyze the user's intent and create a step-by-step Execution Plan.
        Break complex requests into independent tasks.
        
        RESPOND IN STRICT JSON:
        {"thought": "Your internal reasoning", "plan": ["Step 1", "Step 2", ...]}
        Only return JSON."""
        
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=last_msg)]
        response = await get_llm(model_type="premium").ainvoke(messages)
        
        data = json.loads(response.content.strip().replace("```json", "").replace("```", ""))
        return {"thought": data.get("thought"), "plan": data.get("plan"), "next": "supervisor"}
    except Exception as e:
        logger.error(f"Planner Node Error: {e}")
        return {"next": "supervisor"}

async def reflexion_node(state: AgentState):
    """
    [REFLEXION AGENT]
    Reviews the result of the last action. If it didn't solve the plan step, it retries or adjusts.
    """
    try:
        plan = state.get("plan", [])
        if not plan: return state
        
        last_action_result = state["messages"][-1].content
        system_prompt = f"""You are the Callista Reflection Agent.
        Current Plan: {json.dumps(plan)}
        Last Result: {last_action_result}
        
        Did the last action successfully complete the current plan step?
        If yes, remove the step from the plan. If no, stay on the step and suggest a correction.
        
        RESPOND IN STRICT JSON:
        {"is_satisfied": true/false, "remaining_plan": [...], "correction": "advice for next step"}
        Only return JSON."""
        
        messages = [SystemMessage(content=system_prompt)]
        response = await get_llm(model_type="utility").ainvoke(messages)
        
        data = json.loads(response.content.strip().replace("```json", "").replace("```", ""))
        return {"plan": data.get("remaining_plan"), "next": "supervisor"}
    except Exception as e:
        logger.error(f"Reflexion Node Error: {e}")
        return state

# --- SUPERVISOR & AUTO-ROUTING ---

async def supervisor(state: AgentState):
    """The central brain that routes to specialists using LLM reasoning."""
    try:
        plan = state.get("plan", [])
        thought = state.get("thought", "")
        
        system_prompt = f"""You are the Callista Supervisor (ACP/A2A Protocol).
        Your goal is to execute the following plan: {json.dumps(plan)}
        Plan Context: {thought}
        
        Current Specialists (Internal Endpoints):
        - 'call': Phone concierge / call handling.
        - 'vision': Environmental awareness / screen / camera.
        - 'system': Finance, task management, memory, search.
        - 'language': Russian tutoring / translation.
        
        Analyze the current step of the plan and the conversation. Route to the correct specialist.
        
        RESPOND IN STRICT JSON (ACP Format):
        {{"next": "call/vision/system/language", "reasoning": "ACP Routing Decision"}}
        Only return JSON."""
        
        # Truncate history for supervisor
        history = state["messages"][-10:]
        
        memory_context = state.get("memory_context", "")
        advisories = state.get("advisory_briefs", [])
        advisory_summary = f"({len(advisories)} news events found)" if advisories else "(No news alerts)"

        full_prompt = (
            f"{system_prompt}\n\n"
            f"CTX: {memory_context[:500]}\n"
            f"NEWS: {advisory_summary}"
        )

        messages = [SystemMessage(content=full_prompt)] + history
        # Use utility model (8B) to save 70B tokens
        response = await get_llm(model_type="utility").ainvoke(messages)
        
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
    # Use utility model (8B)
    response = await get_llm(model_type="utility").ainvoke(messages)
    
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

async def wake_up_node(state: AgentState):
    """
    Handles 'Wake Up' logic. If Callista is asleep, she only responds to wake words.
    """
    last_msg = state["messages"][-1].content.lower()
    is_active = state.get("is_active", False)
    last_time = state.get("last_active_time", 0)
    now = time.time()

    # 1. Check for wake words
    wake_words = [
        # Discovered multilingual wake words
        "salve callista", "salve zafira", 
        "kalos callista", "kalos zafira", 
        "zdravo callista", "zdravo zafira", 
        "bonjour callista", "bonjour zafira", 
        "ya callista", "ya zafira",
        "wake up", "jarvis", "hey callista", "hello callista"
    ]
    is_wake_call = any(word in last_msg for word in wake_words)
    
    # 3. Check for sleep/bye phrases
    sleep_words = [
        "ciao callista", "ciao zafira", 
        "vale callista", "vale zafira", 
        "poka callista", "poka zafira",
        "bye", "goodbye", "sleep"
    ]
    is_sleep_call = any(word in last_msg for word in sleep_words)

    if is_sleep_call:
        is_active = False
        logger.info("Callista is going to sleep.")
        return {
            "is_active": False,
            "next": "end",
            "messages": [AIMessage(content="Goodbye. I'm going to sleep now.")]
        }

    # 2. Check for timeout (1 min)
    if is_active and (now - last_time > 60):
        is_active = False

    if not is_active:
        if is_wake_call:
            is_active = True
            logger.info("Callista has woken up.")
        else:
            # Stay asleep
            return {
                "is_active": False,
                "next": "end",
                "messages": [AIMessage(content="[Callista is sleeping. Say 'Wake up' or 'Hey Callista' to talk.]")]
            }

    return {"is_active": is_active, "last_active_time": now, "next": "continue"}

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

workflow.add_node("wake_up", wake_up_node)
workflow.add_node("memory_entry", memory_entry)
workflow.add_node("planner", planner_node)
workflow.add_node("supervisor", supervisor)
workflow.add_node("call", call_specialist)
workflow.add_node("vision", vision_expert)
workflow.add_node("system", system_manager)
workflow.add_node("language", language_expert)
workflow.add_node("tools", ToolNode(tools=all_tools))
workflow.add_node("reflect", self_reflection)
workflow.add_node("reflexion", reflexion_node)
workflow.add_node("triage", advisory_triage)
workflow.add_node("travel", travel_intelligence)

workflow.add_edge(START, "wake_up")

def after_wake(state: AgentState):
    if state.get("next") == "end":
        return END
    return "memory_entry"

workflow.add_conditional_edges("wake_up", after_wake)
workflow.add_edge("memory_entry", "travel")
workflow.add_edge("travel", "triage")
workflow.add_edge("triage", "planner")
workflow.add_edge("planner", "supervisor")

workflow.add_conditional_edges(
    "supervisor",
    lambda x: x.get("next"),
    {
        "call": "call",
        "vision": "vision",
        "system": "system",
        "language": "language"
    }
)

def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return "reflect"

workflow.add_conditional_edges("system", should_continue)
workflow.add_conditional_edges("language", should_continue)
workflow.add_edge("tools", "system")
workflow.add_edge("call", "reflexion")
workflow.add_edge("vision", "reflexion")
workflow.add_edge("language", "reflexion")
workflow.add_edge("reflexion", "reflect")
workflow.add_edge("reflect", END)

memory = MemorySaver()
agent_executor = workflow.compile(checkpointer=memory)

async def process_message(thread_id: str, user_id: str, message: str, image_base64: str = None) -> dict:
    try:
        config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
        result = await agent_executor.ainvoke(
            {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
                "image_base64": image_base64,
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
