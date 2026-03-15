import logging
from typing import Optional
from langchain_core.tools import tool
from datetime import datetime, timezone

# Note: We can't inject async DB sessions directly into LangChain @tools easily
# without wrapping them in an async tool context, but we will pass user_id via 
# dependency injection or thread-level configuration later.

# For simplicity, we will use thread-local state or pass user_id via run config.
from langchain_core.runnables.config import RunnableConfig
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.database import async_session_factory
from app.config import get_settings
from app.services import transaction_service, task_service, memory_service, budget_service, news_intelligence

logger = logging.getLogger(__name__)

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
            context_str += f"- {stat['category']}: Spent ₹{stat['spent']:.0f} of ₹{stat['monthly_limit']:.0f} ({stat['percentage_used']}%)\n"
            
        # Call LLM for advice
        settings = get_settings()
        llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=settings.GROQ_API_KEY, temperature=0.5)
        
        messages = [
            SystemMessage(content="You are a strict, smart financial advisor named Callista. Keep your advice under 4 sentences. Point out bad spending habits directly based on the data."),
            HumanMessage(content=f"Here is my financial data for this month. Give me advice:\n{context_str}")
        ]
        
        advice = llm.invoke(messages)
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
async def control_device(feature: str, action: str) -> str:
    """
    Controls phone hardware/settings like Flashlight, Volume, etc.
    Required arguments: feature (str, e.g., 'flashlight', 'volume'), action (str, e.g., 'on', 'off', 'up', 'down').
    Use this when the user says "turn on flashlight" or "mute volume".
    """
    return f"COMMAND:DEVICE|{feature}|{action}"

@tool
async def get_strategic_advisory(config: RunnableConfig = None) -> str:
    """
    Analyzes global geopolitical and economic news against the user's personal spending data.
    Use this when the user asks about 'future risks', 'market impact', 'war effects', 
    or when they want a proactive briefing on how global events might affect their pocket.
    """
    user_id = await _get_user_id(config)
    if not user_id:
        return "Error: User context not found."
    
    try:
        async with async_session_factory() as db:
            # 1. Get user's recent transactions for context
            three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
            txns = await transaction_service.get_transactions(db, user_id, start_date=three_months_ago)
            
            # 2. Fetch and analyze global risks
            news_data = await news_intelligence.NewsIntelligenceService.fetch_global_risks()
            advisories = await news_intelligence.NewsIntelligenceService.analyze_risk_impact(txns, news_data)
            
        if not advisories:
            return "Current global trends don't show an immediate direct impact on your specific spending habits, Sir. You are well-positioned."
            
        result = "PROACTIVE STRATEGIC ADVISORY:\n"
        for adv in advisories:
            result += f"- {adv['event']}\n  Impact: {adv['impact']}\n  Suggestion: {adv['suggestion']}\n"
            
        return result
    except Exception as e:
        logger.error(f"Error in strategic advisory: {e}")
        return "Failed to process global intelligence data."

# List of all available tools
all_tools = [
    log_expense,
    log_income,
    get_balance_summary,
    add_task,
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
    get_strategic_advisory,
]
