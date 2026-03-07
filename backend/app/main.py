"""
Nova AI Life Assistant — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    auth, transactions, categories, budgets,
    tasks, memories, timeline, files, export, notifications, chat
)
from app.telegram.bot import start_bot, stop_bot

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background Task Scheduler
# ---------------------------------------------------------------------------
import asyncio
from app.services import insight_service

async def _background_scheduler():
    """Runs periodic background tasks for active users."""
    logger.info("⏱️ Background scheduler started")
    while True:
        try:
            # We run this loop once per hour, but can trigger logic based on time
            from app.database import async_session_factory
            from sqlalchemy import text
            
            now = datetime.now(timezone.utc)
            
            # Simple simulation: we will just run anomaly detection every 12 hours
            # In production, check `if now.hour == 9:` for specific local time triggers
            
            # Get all user IDs
            async with async_session_factory() as db:
                result = await db.execute(text("SELECT id FROM users"))
                users = result.fetchall()
                
            for user in users:
                user_id = str(user[0])
                await insight_service.detect_anomalies(user_id)
                await insight_service.generate_monthly_forecast(user_id)
                
            logger.info("✅ Background scan complete.")
            
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            
        # Sleep for half a day
        await asyncio.sleep(43200)

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
_bg_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bg_task
    settings = get_settings()
    logger.info(f"🚀 Starting {settings.APP_NAME}")

    # Start Telegram bot
    try:
        await start_bot()
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")
        
    # Start background scheduler
    _bg_task = asyncio.create_task(_background_scheduler())

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    await stop_bot()
    if _bg_task:
        _bg_task.cancel()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A privacy-first personal AI assistant that manages finances, tasks, "
        "knowledge, files, and life analytics. Your own private Jarvis. 🧠"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins in dev, restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include all routers
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["ai-chat"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(budgets.router, prefix="/api/budgets", tags=["budgets"])
app.include_router(tasks.router)
app.include_router(memories.router)
app.include_router(timeline.router)
app.include_router(files.router)
app.include_router(export.router)
app.include_router(notifications.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health",
    }
