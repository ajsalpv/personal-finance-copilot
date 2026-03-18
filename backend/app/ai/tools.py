import logging
from typing import Optional
from langchain_core.tools import tool
from datetime import datetime, timezone, timedelta

# Note: We can't inject async DB sessions directly into LangChain @tools easily
# without wrapping them in an async tool context, but we will pass user_id via 
# dependency injection or thread-level configuration later.

# For simplicity, we will use thread-local state or pass user_id via run config.
from langchain_core.runnables.config import RunnableConfig
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import time

from app.database import async_session_factory
from app.config import get_settings
from app.services import (
    transaction_service, task_service, memory_service,
    budget_service, news_intelligence, location_service, emergency_service,
    learning_service
)

logger = logging.getLogger(__name__)

# --- TOOL CACHE ---
TOOL_CACHE = {
    "strategic": {"data": None, "expiry": 0},
    "emergency": {"data": None, "expiry": 0}
}
CACHE_TTL = 3600 # 1 hour

async def _get_user_id(config: RunnableConfig) -> str:
    """Helper to extract user_id from RunnableConfig."""
    return config.get("configurable", {}).get("user_id")

@tool
async def log_expense(
    amount: float, 
    description: str, 
    category: Optional[str] = None, 
    config: RunnableConfig = None
) -> str:
    """
    Logs an expense transaction for the user.
    Required arguments: amount (float), description (str).
    Optional: category (str).
    Call this when the user explicitly provides an amount and what it was for.
    If the user hasn't provided BOTH an amount and a description (e.g. they only said "Lunch"),
    DO NOT call this tool. Ask them for the missing information first.
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    try:
        async with async_session_factory() as db:
            txn = await transaction_service.create_transaction(
                db=db, 
                user_id=user_id, 
                amount=amount,
                transaction_type="expense",
                merchant_name=description, 
                category=category,
                source="ai_agent",
            )
            return f"Successfully logged expense of ₹{amount} for '{description}'."
    except Exception as e:
        logger.error(f"Error logging expense: {e}")
        return f"Failed to log expense: {str(e)}"

@tool
async def log_income(
    amount: float, 
    source_description: str, 
    config: RunnableConfig = None
) -> str:
    """
    Logs an income transaction.
    Required arguments: amount (float), source_description (str).
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    try:
        async with async_session_factory() as db:
            txn = await transaction_service.create_transaction(
                db=db, 
                user_id=user_id, 
                amount=amount,
                transaction_type="income",
                merchant_name=source_description, 
                category="Salary",
                source="ai_agent",
            )
            return f"Successfully logged income of ₹{amount} from '{source_description}'."
    except Exception as e:
        logger.error(f"Error logging income: {e}")
        return f"Failed to log income: {str(e)}"

@tool
async def get_balance_summary(config: RunnableConfig = None) -> str:
    """
    Gets the spending summary and net balance for the current month.
    Call this when the user asks for balance, summary, or how much they've spent.
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    try:
        async with async_session_factory() as db:
            summary = await transaction_service.get_spending_summary(
                db, user_id, month_start, now
            )
        
        msg = (
            f"This month's summary:\n"
            f"Income: ₹{summary['total_income']:.0f}\n"
            f"Expenses: ₹{summary['total_expense']:.0f}\n"
            f"Net: ₹{summary['net']:.0f}"
        )
        return msg
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return "Failed to get balance summary."

@tool
async def add_task(title: str, config: RunnableConfig = None) -> str:
    """
    Creates a new task or reminder for the user.
    Required argument: title (str).
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    try:
        async with async_session_factory() as db:
            await task_service.create_task(db=db, user_id=user_id, title=title)
        return f"Successfully created task: '{title}'."
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return f"Failed to create task: {str(e)}"

@tool
async def get_tasks(status: Optional[str] = None, config: RunnableConfig = None) -> str:
    """
    Retrieves the user's tasks or reminders.
    Optional argument: status (str, e.g. "pending", "completed").
    Use this when the user asks "what are my tasks" or "do I have any reminders".
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    try:
        async with async_session_factory() as db:
            tasks = await task_service.get_tasks(db=db, user_id=user_id, status=status)
            
        if not tasks:
            return "You have no tasks matching that criteria."
            
        result = "Your Tasks:\n"
        for i, t in enumerate(tasks, 1):
            stat = t.get("status", "pending")
            result += f"{i}. [{stat}] {t.get('title')}\n"
        return result
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return f"Failed to retrieve tasks: {str(e)}"

@tool
async def complete_task(task_title: str, config: RunnableConfig = None) -> str:
    """
    Marks a task as completed based on its title matching.
    Required argument: task_title (str).
    Use this when the user says "I finished X" or "cross off Y".
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    try:
        async with async_session_factory() as db:
            # First find tasks matching title (simple match for now)
            tasks = await task_service.get_tasks(db=db, user_id=user_id, status="pending")
            matching_task = None
            for t in tasks:
                if task_title.lower() in t.get("title", "").lower():
                    matching_task = t
                    break
                    
            if not matching_task:
                return f"I couldn't find a pending task matching '{task_title}'."
                
            await task_service.update_task(db=db, user_id=user_id, task_id=matching_task["id"], updates={"status": "completed"})
            return f"Successfully marked task '{matching_task['title']}' as completed."
    except Exception as e:
        logger.error(f"Error completing task: {e}")
        return f"Failed to complete task: {str(e)}"

@tool
async def store_memory(content: str, config: RunnableConfig = None) -> str:
    """
    Stores an important piece of information or knowledge for the user to remember.
    Required argument: content (str).
    Use this when the user says "remember that X" or tells you a fact they want you to retain.
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    try:
        async with async_session_factory() as db:
            await memory_service.create_memory(db=db, user_id=user_id, content=content)
        return f"Successfully remembered: '{content}'."
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        return f"Failed to store memory: {str(e)}"

@tool
async def search_memory(query: str, config: RunnableConfig = None) -> str:
    """
    Searches the user's stored memories and knowledge base.
    Required argument: query (str).
    Use this when the user asks "what did I say about X" or "do you remember Y".
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    try:
        async with async_session_factory() as db:
            results = await memory_service.search_memories(db, user_id, query, limit=3)
            
        if not results:
            return f"I couldn't find any memories matching '{query}'."
            
        memories = [m['content'] for m in results]
        return "Here is what I remember:\n- " + "\n- ".join(memories)
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        return f"Failed to search memory: {str(e)}"

@tool
async def get_financial_advice(config: RunnableConfig = None) -> str:
    """
    Generates personalized financial advice based on the user's current month spending and budgets.
    Call this when the user explicitly asks for "financial advice", "savings tips", or "how to reduce spending".
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    try:
        async with async_session_factory() as db:
            summary = await transaction_service.get_spending_summary(db, user_id, month_start, now)
            statuses = await budget_service.get_budget_status(db, user_id)
            
        # Format the context for the LLM
        context_str = f"Total Income: ₹{summary['total_income']:.0f}\n"
        context_str += f"Total Expenses: ₹{summary['total_expense']:.0f}\n"
        context_str += f"Net Balance: ₹{summary['net']:.0f}\n\n"
        
        context_str += "Category Breakdown:\n"
        for cat in summary["by_category"]:
            context_str += f"- {cat['category']}: ₹{cat['total']:.0f}\n"
            
        context_str += "\nBudget Status:\n"
        for stat in statuses:
            context_str += f"- {stat['category']}: Spent ₹{stat['spent']:.0f} of ₹{stat['monthly_limit']:.0f}\nAI Coaching: {stat.get('ai_coaching', 'No status available.')}\n"
            
        # Call LLM for advice with forced dynamic settings
        load_dotenv(override=True)
        key = os.getenv("GROQ_API_KEY")
        
        llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=key, temperature=0.5)
        
        messages = [
            SystemMessage(content="You are a strict, smart financial advisor named Callista. Keep your advice under 4 sentences. Point out bad spending habits directly based on the data."),
            HumanMessage(content=f"Here is my financial data for this month. Give me advice:\n{context_str}")
        ]
        
        advice = await llm.ainvoke(messages)
        return advice.content

    except Exception as e:
        logger.error(f"Error getting financial advice: {e}")
        return "Sorry, I couldn't generate financial advice at the moment."

@tool
async def make_call(phone_number: str, contact_name: Optional[str] = None) -> str:
    """
    Triggers a phone call to a specific number or contact.
    Required argument: phone_number (str).
    Optional: contact_name (str).
    Use this when the user says "call X" or "phone Y".
    """
    return f"COMMAND:CALL|{phone_number}|{contact_name or ''}"

@tool
async def send_sms(phone_number: str, message: str) -> str:
    """
    Triggers sending an SMS/message to a phone number.
    Required arguments: phone_number (str), message (str).
    Use this when the user says "message X that I'm running late".
    """
    return f"COMMAND:SMS|{phone_number}|{message}"

@tool
async def send_email(recipient: str, subject: str, body: str) -> str:
    """
    Triggers sending an email.
    Required arguments: recipient (str), subject (str), body (str).
    Use this when the user says "email X about the meeting".
    """
    return f"COMMAND:EMAIL|{recipient}|{subject}|{body}"

@tool
async def open_maps(location: str) -> str:
    """
    Opens Google Maps for navigation or searching a location.
    Required argument: location (str).
    Use this when the user says "where is X" or "take me to Y" or "open maps for Z".
    """
    return f"COMMAND:MAPS|{location}"

@tool
async def search_contacts(query: str) -> str:
    """
    Searches the phone's contact list for a specific name or detail.
    Required argument: query (str).
    Use this when the user says "find X's number" or "who is Y".
    """
    return f"COMMAND:SEARCH_CONTACTS|{query}"

@tool
async def add_calendar_event(title: str, start_time: str, location: Optional[str] = None) -> str:
    """
    Adds an event to the phone's calendar.
    Required arguments: title (str), start_time (ISO format string).
    Optional: location (str).
    Use this when the user says "schedule a meeting at 5pm tomorrow".
    """
    return f"COMMAND:ADD_CALENDAR|{title}|{start_time}|{location or ''}"

@tool
async def list_calendar_events(date: Optional[str] = None) -> str:
    """
    Lists calendar events for a specific date.
    Optional argument: date (ISO format string, defaults to today).
    Use this when the user says "what's on my schedule today?".
    """
    return f"COMMAND:LIST_CALENDAR|{date or ''}"

@tool
async def set_alarm(time_str: str, label: Optional[str] = None) -> str:
    """
    Sets an alarm on the user's phone.
    Required argument: time_str (e.g., '07:30', '7:30 AM').
    Optional: label (str).
    Use this when the user says "set an alarm for 7am" or "wake me up at 8".
    """
    return f"COMMAND:ALARM|{time_str}|{label or ''}"

@tool
async def add_phone_reminder(text: str, due_time: str) -> str:
    """
    Adds a system-level reminder on the phone.
    Required arguments: text (str), due_time (ISO format or descriptive like 'in 5 minutes').
    Use this when the user says "remind me to take medicine in 10 minutes".
    """
    return f"COMMAND:REMINDER|{text}|{due_time}"

@tool
async def modify_phone_setting(feature: str, value: str) -> str:
    """
    Modifies a phone system setting (Brightness, Volume, Bluetooth, DND).
    Required arguments: feature (str, e.g. 'brightness', 'bluetooth'), value (str, e.g. '50%', 'on', 'off').
    Use this when the user says "turn on bluetooth" or "set brightness to max".
    """
    return f"COMMAND:SETTING|{feature}|{value}"

@tool
async def control_device(action: str, target: str = "") -> str:
    """
    Controls smart home devices or local phone hardware.
    Required arguments: action (e.g., 'turn on', 'stop', 'play'), target (e.g., 'living room light', 'music').
    Use this when the user says "turn on the lights" or "play some music".
    """
    return f"COMMAND:CONTROL|{action}|{target}"

@tool
async def update_learning_progress(
    language: str, 
    word: Optional[str] = None, 
    translation: Optional[str] = None,
    mastered: bool = False, 
    score: Optional[int] = None,
    config: RunnableConfig = None
) -> str:
    """
    Updates the user's language learning progress in the database.
    Use this when the user learns a new word, finishes a lesson, or practices.
    """
    user_id = await _get_user_id(config)
    if not user_id: return "Error: User context not found."
    
    try:
        async with async_session_factory() as db:
            if word and translation:
                await learning_service.add_vocabulary(db, user_id, language, word, translation)
            if score is not None:
                await learning_service.record_lesson(db, user_id, language, "chat", score)
            return f"Progress updated for {language}."
    except Exception as e:
        logger.error(f"Error updating learning progress: {e}")
        return f"Failed to update progress: {str(e)}"

@tool
async def get_learning_status(language: str, config: RunnableConfig = None) -> str:
    """
    Retrieves the user's learning stats, streaks, and top words for a language.
    """
    user_id = await _get_user_id(config)
    if not user_id: return "Error: User context not found."
    
    try:
        async with async_session_factory() as db:
            progress = await learning_service.get_progress(db, user_id, language)
            if not progress:
                return f"You haven't started learning {language} yet."
            
            return (
                f"--- {language} Learning Status ---\n"
                f"Level: {progress['current_level']}\n"
                f"Words Learned: {progress['total_words_learned']}\n"
                f"Daily Streak: {progress['daily_streak']} days\n"
                f"Points: {progress['points']}"
            )
    except Exception as e:
        logger.error(f"Error getting learning status: {e}")
        return "Failed to retrieve learning status."

@tool
async def get_strategic_advisory(config: RunnableConfig = None) -> str:
    """
    [PHASE 15/18] Analyzes global geopolitical and economic news against the user's personal context.
    Provides proactive risk warnings with confidence scores.
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    try:
        now_ts = time.time()
        if TOOL_CACHE["strategic"]["data"] and now_ts < TOOL_CACHE["strategic"]["expiry"]:
            logger.info("Using cached strategic output")
            return TOOL_CACHE["strategic"]["data"]

        async with async_session_factory() as db:
            # 1. Gather dynamic context
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=30)
            summary = await transaction_service.get_spending_summary(db, user_id, start, now)
            top_cats = [c["category"] for c in summary.get("by_category", [])[:5]]
            
            # Fetch real location context
            location_ctx = await location_service.LocationService.get_recent_locations(db, user_id, limit=1)
            user_city = location_ctx[0]["city"] if location_ctx else "Unknown"
            
            user_context = {
                "location": user_city,
                "top_categories": top_cats if top_cats else ["General"],
                "current_city": user_city
            }
            
            # 2. Pipeline processing
            news = await news_intelligence.NewsIntelligenceService.fetch_global_risks()
            advisories = await news_intelligence.NewsIntelligenceService.analyze_impact(news, user_context)
            filtered = await news_intelligence.NewsIntelligenceService.filter_relevance(advisories, user_context)
            
            # 3. Cost of Living (dynamic)
            col_index = await news_intelligence.NewsIntelligenceService.get_cost_of_living_index()
            
        if not filtered:
            return f"Current global trends don't show an immediate direct impact on your spending habits in {user_city}."
            
        result = f"PROACTIVE LIFE INTELLIGENCE BRIEFING ({user_city}):\n\n"
        for adv in filtered:
            result += f"⚠️ {adv['event']}\n"
            result += f"  - Impact: {adv['impact']}\n"
            result += f"  - Confidence: {adv['confidence']}\n"
            result += f"  - Recommendation: {adv['suggestion']}\n\n"
            
        result += f"📊 Cost of Living Insight ({col_index['period']}):\n"
        for item in col_index['items']:
            result += f"  - {item['name']}: {item['trend']} ({item['status']})\n"
            
        TOOL_CACHE["strategic"]["data"] = result
        TOOL_CACHE["strategic"]["expiry"] = now_ts + CACHE_TTL
        return result
    except Exception as e:
        logger.error(f"Error in strategic advisory: {e}")
        return "Failed to process global intelligence data."

@tool
async def get_purchase_advice(item_name: str, config: RunnableConfig = None) -> str:
    """
    [PHASE 17] Provides smart advice on whether now is a good time to buy a specific high-value item.
    Analyzes price trends, seasonal sales, and inflation.
    """
    from app.ai.agents.purchase_agent import PurchaseAgent
    advice = await PurchaseAgent.analyze_purchase_timing(item_name)
    return f"SMART PURCHASE ADVISORY:\n{advice}"

@tool
async def get_emergency_readiness(config: RunnableConfig = None) -> str:
    """
    [PHASE 17] Checks for local risks like weather (Kerala rainfall), shortages, or policy changes.
    """
    user_id = await _get_user_id(config)
    try:
        now_ts = time.time()
        if TOOL_CACHE["emergency"]["data"] and now_ts < TOOL_CACHE["emergency"]["expiry"]:
            return TOOL_CACHE["emergency"]["data"]

        async with async_session_factory() as db:
            # Detect user's current region dynamically
            loc_history = await location_service.LocationService.get_recent_locations(db, user_id, limit=1)
            region = loc_history[0]["city"] if loc_history else "India/Kerala"
            
            report = await emergency_service.EmergencyService.get_local_readiness(region)
        
        result = f"EMERGENCY READINESS ALERT ({report['region']}):\n"
        for alert in report['active_alerts']:
            result += f"\n🚨 {alert['title']} ({alert['severity'].upper()})\n"
            result += f"  - Description: {alert['description']}\n"
            result += f"  - Confidence: {alert['confidence']}\n"
            result += f"  - Preparation:\n"
            for step in alert['prep']:
                result += f"    • {step}\n"
        
        TOOL_CACHE["emergency"]["data"] = result
        TOOL_CACHE["emergency"]["expiry"] = now_ts + CACHE_TTL
        return result
    except Exception as e:
        logger.error(f"Error in emergency readiness: {e}")
        return "Failed to retrieve local risk data."

# List of all available tools
all_tools = [
    log_expense,
    log_income,
    get_balance_summary,
    add_task,
    get_tasks,
    complete_task,
    store_memory,
    search_memory,
    get_financial_advice,
    make_call,
    send_sms,
    send_email,
    open_maps,
    search_contacts,
    add_calendar_event,
    list_calendar_events,
    control_device,
    set_alarm,
    add_phone_reminder,
    modify_phone_setting,
    update_learning_progress,
    get_learning_status,
    get_strategic_advisory,
    get_purchase_advice,
    get_emergency_readiness,
    search_web
]
