"""
Nova Telegram Bot — Command & Message Handlers.
All handlers are owner-only (controlled by OWNER_TELEGRAM_ID).
"""
import logging
import re
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.ext import ContextTypes, filters

from app.config import get_settings
from app.database import async_session_factory
from app.services import transaction_service, budget_service, task_service
from app.services import memory_service, timeline_service
import io
import httpx
import time
import uuid

# We will import the agent function inside the handler to avoid circular imports during startup,
# but for now we put globals here to track session state.
active_sessions = {}  # telegram_id -> last_active timestamp (float)
session_threads = {}  # telegram_id -> thread_id (str)

WAKE_WORDS = {
    "salve callista", "salve zafira", 
    "kalos callista", "kalos zafira", 
    "zdravo callista", "zdravo zafira", 
    "bonjour callista", "bonjour zafira", 
    "ya callista", "ya zafira"
}

SLEEP_WORDS = {
    "ciao callista", "ciao zafira", 
    "vale callista", "vale zafira", 
    "poka callista", "poka zafira"
}

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Owner-only filter
# ---------------------------------------------------------------------------
settings = get_settings()


class OwnerFilter(filters.MessageFilter):
    """Only allow messages from the bot owner."""

    def filter(self, message):
        if not settings.OWNER_TELEGRAM_ID:
            return False
        return str(message.from_user.id) == str(settings.OWNER_TELEGRAM_ID)


owner_only_filter = OwnerFilter()


# ---------------------------------------------------------------------------
# Helper: get or create user by telegram_id
# ---------------------------------------------------------------------------
async def _get_user_id(telegram_id: str) -> str:
    """Get user ID by telegram_id, or return a default."""
    from sqlalchemy import text
    async with async_session_factory() as db:
        result = await db.execute(
            text("SELECT id FROM users WHERE telegram_id = :tid"),
            {"tid": telegram_id},
        )
        row = result.first()
        if row:
            return str(row[0])
    return None


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧠 *Nova AI Life Assistant*\n\n"
        "I'm your private AI assistant. Here's what I can do:\n\n"
        "💰 `/expense <amount> <description>` — Log expense\n"
        "📥 `/income <amount> <description>` — Log income\n"
        "📊 `/balance` — Spending summary\n"
        "💳 `/budget` — Budget status\n"
        "📋 `/task <title>` — Create task\n"
        "🧠 `/remember <info>` — Store memory\n"
        "🔍 `/recall <query>` — Search memories\n"
        "📅 `/timeline` — Today's timeline\n"
        "📤 `/export` — Export data\n\n"
        "Or just send me a message and I'll understand! 🚀",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# /expense <amount> <description>
# ---------------------------------------------------------------------------
async def expense_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await _get_user_id(str(update.effective_user.id))
    if not user_id:
        await update.message.reply_text("⚠️ You're not registered yet. Please register via the API first.")
        return

    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text("Usage: `/expense <amount> [description]`", parse_mode="Markdown")
        return

    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Example: `/expense 250 lunch`", parse_mode="Markdown")
        return

    description = " ".join(args[1:]) if len(args) > 1 else None
    category = _guess_category(description) if description else None

    async with async_session_factory() as db:
        txn = await transaction_service.create_transaction(
            db=db, user_id=user_id, amount=amount,
            transaction_type="expense",
            merchant_name=description, category=category,
            source="telegram",
        )
        # Auto timeline
        await timeline_service.create_timeline_event(
            db=db, user_id=user_id,
            event_type="expense",
            description=f"💸 ₹{amount}" + (f" — {description}" if description else ""),
            source="telegram",
            metadata={"transaction_id": txn["id"]},
        )

    emoji = "🍔" if category == "Food" else "💸"
    reply = f"{emoji} Logged: ₹{amount:.0f}"
    if description:
        reply += f" — {description}"
    if category:
        reply += f" [{category}]"
    await update.message.reply_text(reply)


# ---------------------------------------------------------------------------
# /income <amount> <description>
# ---------------------------------------------------------------------------
async def income_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await _get_user_id(str(update.effective_user.id))
    if not user_id:
        await update.message.reply_text("⚠️ Not registered. Register via the API first.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: `/income <amount> [description]`", parse_mode="Markdown")
        return

    try:
        amount = float(args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid amount.")
        return

    description = " ".join(args[1:]) if len(args) > 1 else None

    async with async_session_factory() as db:
        await transaction_service.create_transaction(
            db=db, user_id=user_id, amount=amount,
            transaction_type="income",
            merchant_name=description, category="Salary" if not description else None,
            source="telegram",
        )

    await update.message.reply_text(f"💰 Income logged: ₹{amount:.0f}" + (f" — {description}" if description else ""))


# ---------------------------------------------------------------------------
# /balance
# ---------------------------------------------------------------------------
async def balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await _get_user_id(str(update.effective_user.id))
    if not user_id:
        await update.message.reply_text("⚠️ Not registered.")
        return

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async with async_session_factory() as db:
        summary = await transaction_service.get_spending_summary(
            db, user_id, month_start, now
        )

    msg = f"📊 *This Month's Summary*\n\n"
    msg += f"💰 Income: ₹{summary['total_income']:.0f}\n"
    msg += f"💸 Expenses: ₹{summary['total_expense']:.0f}\n"
    msg += f"📈 Net: ₹{summary['net']:.0f}\n"

    if summary["by_category"]:
        msg += "\n📂 *By Category:*\n"
        for cat in summary["by_category"][:8]:
            msg += f"  • {cat['category']}: ₹{cat['total']:.0f} ({cat['percentage']}%)\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /budget
# ---------------------------------------------------------------------------
async def budget_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await _get_user_id(str(update.effective_user.id))
    if not user_id:
        await update.message.reply_text("⚠️ Not registered.")
        return

    async with async_session_factory() as db:
        statuses = await budget_service.get_budget_status(db, user_id)

    if not statuses:
        await update.message.reply_text("No budgets set. Use the API to create budgets.")
        return

    msg = "💳 *Budget Status*\n\n"
    for s in statuses:
        bar = "🟢" if s["percentage_used"] < 70 else "🟡" if s["percentage_used"] < 90 else "🔴"
        msg += f"{bar} {s['category']}: ₹{s['spent']:.0f}/₹{s['monthly_limit']:.0f} ({s['percentage_used']}%)\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /task <title>
# ---------------------------------------------------------------------------
async def task_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await _get_user_id(str(update.effective_user.id))
    if not user_id:
        await update.message.reply_text("⚠️ Not registered.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/task <title>`", parse_mode="Markdown")
        return

    title = " ".join(context.args)

    async with async_session_factory() as db:
        await task_service.create_task(db=db, user_id=user_id, title=title)

    await update.message.reply_text(f"📋 Task created: *{title}*", parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /remember <info>
# ---------------------------------------------------------------------------
async def remember_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await _get_user_id(str(update.effective_user.id))
    if not user_id:
        await update.message.reply_text("⚠️ Not registered.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/remember <information>`", parse_mode="Markdown")
        return

    content = " ".join(context.args)

    async with async_session_factory() as db:
        await memory_service.create_memory(db=db, user_id=user_id, content=content)

    await update.message.reply_text(f"🧠 Remembered: _{content}_", parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /recall <query>
# ---------------------------------------------------------------------------
async def recall_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await _get_user_id(str(update.effective_user.id))
    if not user_id:
        await update.message.reply_text("⚠️ Not registered.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/recall <query>`", parse_mode="Markdown")
        return

    query = " ".join(context.args)

    async with async_session_factory() as db:
        results = await memory_service.search_memories(db, user_id, query, limit=5)

    if not results:
        await update.message.reply_text("🔍 No memories found matching your query.")
        return

    msg = f"🔍 *Memories matching '{query}':*\n\n"
    for i, m in enumerate(results, 1):
        msg += f"{i}. {m['content']}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /timeline
# ---------------------------------------------------------------------------
async def timeline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = await _get_user_id(str(update.effective_user.id))
    if not user_id:
        await update.message.reply_text("⚠️ Not registered.")
        return

    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    async with async_session_factory() as db:
        events = await timeline_service.get_timeline(
            db, user_id, start_date=day_start, end_date=now, limit=20,
        )

    if not events:
        await update.message.reply_text("📅 No events today yet.")
        return

    # Convert to IST for display
    ist = timezone(timedelta(hours=5, minutes=30))
    msg = "📅 *Today's Timeline*\n\n"
    for e in reversed(events):  # chronological order
        ts = e["timestamp"]
        if hasattr(ts, "astimezone"):
            ts = ts.astimezone(ist)
        time_str = ts.strftime("%I:%M %p")
        msg += f"🕐 {time_str} — {e['description']}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /export
# ---------------------------------------------------------------------------
async def export_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📤 Use the API to export your data:\n\n"
        "• `GET /export/transactions?format=csv`\n"
        "• `GET /export/all`\n"
        "• `GET /export/backup`\n",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Natural language text (Phase 2 AI Agent Integration)
# ---------------------------------------------------------------------------
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lowered_text = text.lower()
    telegram_id = str(update.effective_user.id)
    
    # 1. Check for WAKE phrases
    if lowered_text in WAKE_WORDS:
        active_sessions[telegram_id] = time.time()
        session_threads[telegram_id] = str(uuid.uuid4())
        await update.message.reply_text("Hello. How can I help?")
        return
        
    # 2. Check for SLEEP phrases
    if lowered_text in SLEEP_WORDS:
        if telegram_id in active_sessions:
            del active_sessions[telegram_id]
        if telegram_id in session_threads:
            del session_threads[telegram_id]
        await update.message.reply_text("Going to sleep.")
        return

    # 3. Check if active and apply IDLE TIMEOUT (30 seconds)
    if telegram_id in active_sessions:
        time_since_active = time.time() - active_sessions[telegram_id]
        
        if time_since_active > 30:
            # Idle timeout hit
            del active_sessions[telegram_id]
            if telegram_id in session_threads:
                del session_threads[telegram_id]
            await update.message.reply_text("Going idle.")
            return
            
        # 4. Agent is awake and not timed out -> Process Message
        active_sessions[telegram_id] = time.time() # Reset idle timer
        
        # We need the user DB ID for backend services
        user_id = await _get_user_id(telegram_id)
        if not user_id:
            await update.message.reply_text("⚠️ You're not registered in the database.")
            return
            
        # Import dynamically to avoid circular dependencies
        from app.ai.agent import process_message
        
        thread_id = session_threads.get(telegram_id)
        
        try:
            # UX: Show typing indicator while LLM processes
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
            response = await process_message(thread_id, user_id, text)
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Agent error: {e}")
            await update.message.reply_text("Hmm, something went wrong with the AI processing.")
            
        return

    # 5. Fallback: If agent is asleep and message is sent
    # We silently ignore based on user request ("The bot will only actively converse when woken up")
    # But for debugging, we can log it.
    logger.debug(f"Ignored message from {telegram_id} because agent is asleep.")


# ---------------------------------------------------------------------------
# Voice message handler
# ---------------------------------------------------------------------------
async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Strict Voice Authentication:
    1. Download audio
    2. Verify voice fingerprint (Resemblyzer)
    3. Transcribe (Groq Whisper)
    4. Process as AI Agent command
    """
    telegram_id = str(update.effective_user.id)
    user_id = await _get_user_id(telegram_id)
    
    if not user_id:
        await update.message.reply_text("⚠️ You are not registered.")
        return

    # UX: Show "record_voice" action while processing
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='record_voice')

    # 1. Download voice file from Telegram
    voice_file = await update.message.voice.get_file()
    audio_buffer = io.BytesIO()
    await voice_file.download_to_memory(audio_buffer)
    audio_bytes = audio_buffer.getvalue()

    async with async_session_factory() as db:
        # Fetch user's reference embedding
        from sqlalchemy import text
        result = await db.execute(text("SELECT voice_embedding FROM users WHERE id = :id"), {"id": user_id})
        row = result.fetchone()
        
        if not row or not row[0]:
            await update.message.reply_text("👋 I haven't learned your voice yet. Please enroll your voice via the mobile app or API first.")
            return
            
        from app.security.voice_auth import verify_voice, bytes_to_embedding
        reference_embedding = bytes_to_embedding(row[0])

        # 2. Verify voice identity
        try:
            is_verified, score = verify_voice(audio_bytes, reference_embedding)
            logger.info(f"Voice verification for {telegram_id}: score={score:.4f}, verified={is_verified}")
            
            if not is_verified:
                await update.message.reply_text("🔒 Voice mismatch. I only take orders from my master.")
                return
        except Exception as e:
            logger.error(f"Voice verification failed: {e}")
            await update.message.reply_text("⚠️ Voice authentication error. Please try again or type.")
            return

    # 3. Transcribe via Groq Whisper API
    try:
        from app.config import get_settings
        settings = get_settings()
        
        # We need a file-like object with a proper extension for Groq
        audio_buffer.seek(0)
        # Wrap in a way Groq's client likes it (or use httpx directly for speed)
        async with httpx.AsyncClient() as client:
            files = {'file': ('voice.ogg', audio_bytes, 'audio/ogg')}
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                files=files,
                data={"model": "whisper-large-v3-turbo"}
            )
            response.raise_for_status()
            transcription = response.json().get("text", "")
            
        if not transcription:
            await update.message.reply_text("🤷 I heard you, but couldn't understand the words.")
            return
            
        await update.message.reply_text(f"🎤 _I heard:_ \"{transcription}\"", parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        await update.message.reply_text("⚠️ Error transcribing voice.")
        return

    # 4. Process transcribed text as Agent command
    from app.ai.agent import process_message
    
    # Ensure session is active
    if telegram_id not in active_sessions:
        active_sessions[telegram_id] = time.time()
        session_threads[telegram_id] = str(uuid.uuid4())
    
    thread_id = session_threads.get(telegram_id)
    
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        response = await process_message(thread_id, user_id, transcription)
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Agent error from voice: {e}")
        await update.message.reply_text("Error processing your voice command.")


# ---------------------------------------------------------------------------
# Helper: guess category from description
# ---------------------------------------------------------------------------
def _guess_category(description: str) -> str:
    """Simple keyword-based category guessing (Phase 2 will use AI)."""
    desc = description.lower()
    category_keywords = {
        "Food": ["lunch", "dinner", "breakfast", "food", "eat", "restaurant", "cafe", "coffee", "tea", "snack", "biryani", "pizza", "burger"],
        "Transport": ["uber", "ola", "auto", "bus", "train", "metro", "fuel", "petrol", "diesel", "cab", "taxi"],
        "Shopping": ["shopping", "amazon", "flipkart", "myntra", "clothes", "shoes"],
        "Bills": ["bill", "electricity", "water", "internet", "wifi", "recharge", "phone"],
        "Entertainment": ["movie", "netflix", "spotify", "game", "concert"],
        "Health": ["medicine", "doctor", "hospital", "pharmacy", "gym"],
        "Education": ["book", "course", "class", "tuition", "school", "college"],
        "Groceries": ["grocery", "vegetables", "fruits", "milk", "eggs"],
        "Rent": ["rent", "house rent"],
        "Subscriptions": ["subscription", "premium", "membership"],
    }

    for category, keywords in category_keywords.items():
        if any(kw in desc for kw in keywords):
            return category

    return "Other"
