"""
Nova AI Life Assistant — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    auth, transactions, categories, budgets,
    tasks, memories, timeline, files, export, notifications, chat, vision
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
    logger.info("⏱️ Background scheduler started — waiting 30s for services to warm up")
    # Wait for container networking/DNS to stabilize before first run
    await asyncio.sleep(30)
    
    while True:
        try:
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
            logger.warning(f"Scheduler cycle error (will retry in 12h): {e}")
            
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

    # Determine Telegram mode (Webhook for Render, Polling for Local)
    base_url = os.environ.get("RENDER_EXTERNAL_URL")
    webhook_url = f"{base_url}/api/telegram/webhook" if base_url else None

    # Start Telegram bot
    try:
        from app.telegram.bot import start_bot, stop_bot
        await start_bot(webhook_url=webhook_url)
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")
        
    # Start background scheduler
    _bg_task = asyncio.create_task(_background_scheduler())
    _keep_alive_task = asyncio.create_task(_keep_alive_ping())

    # Send Telegram notification that server is live
    try:
        from app.telegram.bot import _bot_app
        owner_id = settings.OWNER_TELEGRAM_ID
        if _bot_app and owner_id:
            await _bot_app.bot.send_message(
                chat_id=owner_id,
                text="✅ *Callista is online!*\nYour AI assistant server has started successfully and is ready to serve you.",
                parse_mode="Markdown"
            )
            logger.info("📱 Server-live notification sent to owner.")
    except Exception as e:
        logger.warning(f"Could not send startup notification: {e}")

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    from app.telegram.bot import stop_bot
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
app.include_router(vision.router)

@app.get("/api/ping", tags=["health"])
async def ping_endpoint():
    """Endpoint used to keep Render alive via cron-job.org or self-ping"""
    return {"status": "ok", "message": "Callista is awake!"}
    
@app.post("/api/telegram/webhook", tags=["telegram"])
async def telegram_webhook(request: Request):
    """Receive incoming webhook updates from Telegram."""
    try:
        data = await request.json()
        from app.telegram.bot import handle_webhook_update
        await handle_webhook_update(data)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error handling Telegram webhook: {e}")
        return {"status": "error"}

from fastapi.responses import JSONResponse
import socket
from sqlalchemy.exc import OperationalError

@app.exception_handler(socket.gaierror)
async def gaierror_handler(request: Request, exc: socket.gaierror):
    logger.error(f"DNS Resolution failed (typically bad DATABASE_URL): {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database connection failed. Please check the DATABASE_URL environment variable on Render for typos."},
    )

@app.exception_handler(OperationalError)
async def sqlalchemy_op_error_handler(request: Request, exc: OperationalError):
    logger.error(f"Database operational error: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Could not connect to the database. Check if the database server is running and accessible."},
    )

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
