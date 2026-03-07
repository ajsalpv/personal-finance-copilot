"""
Nova Telegram Bot — Setup and lifecycle management.
"""
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.config import get_settings
from app.telegram.handlers import (
    start_handler,
    expense_handler,
    income_handler,
    balance_handler,
    budget_handler,
    task_handler,
    remember_handler,
    recall_handler,
    timeline_handler,
    export_handler,
    text_message_handler,
    voice_message_handler,
    owner_only_filter,
)

logger = logging.getLogger(__name__)

_bot_app: Application = None


async def start_bot():
    """Initialize and start the Telegram bot (polling mode)."""
    global _bot_app
    settings = get_settings()

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram bot disabled")
        return

    _bot_app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Register command handlers (all go through owner-only filter)
    _bot_app.add_handler(CommandHandler("start", start_handler, filters=owner_only_filter))
    _bot_app.add_handler(CommandHandler("expense", expense_handler, filters=owner_only_filter))
    _bot_app.add_handler(CommandHandler("income", income_handler, filters=owner_only_filter))
    _bot_app.add_handler(CommandHandler("balance", balance_handler, filters=owner_only_filter))
    _bot_app.add_handler(CommandHandler("budget", budget_handler, filters=owner_only_filter))
    _bot_app.add_handler(CommandHandler("task", task_handler, filters=owner_only_filter))
    _bot_app.add_handler(CommandHandler("remember", remember_handler, filters=owner_only_filter))
    _bot_app.add_handler(CommandHandler("recall", recall_handler, filters=owner_only_filter))
    _bot_app.add_handler(CommandHandler("timeline", timeline_handler, filters=owner_only_filter))
    _bot_app.add_handler(CommandHandler("export", export_handler, filters=owner_only_filter))

    # Voice messages
    _bot_app.add_handler(MessageHandler(
        filters.VOICE & owner_only_filter, voice_message_handler
    ))

    # Regular text messages (natural language → AI agent in Phase 2)
    _bot_app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & owner_only_filter, text_message_handler
    ))

    # Initialize and start polling
    await _bot_app.initialize()
    await _bot_app.start()
    await _bot_app.updater.start_polling(drop_pending_updates=True)

    logger.info("🤖 Telegram bot started successfully")


async def stop_bot():
    """Stop the Telegram bot gracefully."""
    global _bot_app
    if _bot_app:
        if _bot_app.updater and _bot_app.updater.running:
            await _bot_app.updater.stop()
        await _bot_app.stop()
        await _bot_app.shutdown()
        logger.info("🤖 Telegram bot stopped")
