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
import httpx
import os
from datetime import datetime, timezone
from sqlalchemy import text

from app.database import async_session_factory
from app.services import insight_service

async def _keep_alive_ping():
    """Background task to ping the server every 10 minutes to prevent Render sleep."""
    while True:
        try:
            await asyncio.sleep(600)  # 10 minutes
            
            # If RENDER_EXTERNAL_URL is available (Render sets this), hit the external URL.
            base_url = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:8000")
            url = f"{base_url}/api/ping"
            
            async with httpx.AsyncClient() as client:
                await client.get(url)
            logger.debug(f"Keep-alive ping sent to {url}")
        except Exception as e:
            logger.debug(f"Keep-alive ping failed: {e}")

async def _background_scheduler():
    """Runs periodic background tasks for active users."""
    logger.info("⏱️ Background scheduler started")
    while True:
        try:
            now = datetime.now(timezone.utc)
            
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
_keep_alive_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bg_task, _keep_alive_task
    settings = get_settings()
    logger.info(f"🚀 Starting {settings.APP_NAME}")

    # Start Telegram bot
    try:
        await start_bot()
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")
        
    # Start background scheduler
    _bg_task = asyncio.create_task(_background_scheduler())
    _keep_alive_task = asyncio.create_task(_keep_alive_ping())

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    await stop_bot()
    if _bg_task:
        _bg_task.cancel()
    if _keep_alive_task:
        _keep_alive_task.cancel()

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

@app.get("/api/ping", tags=["health"])
async def ping_endpoint():
    """Endpoint used to keep Render alive via cron-job.org or self-ping"""
    return {"status": "ok", "message": "Callista is awake!"}

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
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
