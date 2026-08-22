import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.config import settings
from app.database.database import init_db
from app.bot.handlers import router as bot_router
from app.scheduler.daily_jobs import setup_scheduler
from app.jobs.collector import JobCollector

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("jobhunter")


async def main() -> None:
    """Application entrypoint."""
    logger.info("Initializing JobHunter AI...")

    # 1. Initialize SQLite / Postgres database tables
    await init_db()

    # 2. Pre-populate initial jobs if database is fresh
    try:
        await JobCollector.collect_and_store_jobs()
    except Exception as e:
        logger.warning(f"Initial job collection skipped or encountered error: {e}")

    # 3. Check for bot token
    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "your_telegram_bot_token_here":
        logger.warning(
            "⚠️ No valid BOT_TOKEN provided in .env! "
            "Please create a bot via @BotFather and set BOT_TOKEN in .env to enable Telegram interaction."
        )

    # 4. Initialize Telegram Bot & Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN or "123456789:MockTokenForValidationPurposesOnly000",
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()
    dp.include_router(bot_router)

    # 5. Start background scheduler (Daily digests & periodic scraping)
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info(
        f"Scheduler active: Scrapes every {settings.SCRAPE_INTERVAL_HOURS}h | "
        f"Daily digest at {settings.DIGEST_TIME} UTC"
    )

    # 6. Start polling if token is configured
    if settings.BOT_TOKEN and settings.BOT_TOKEN != "your_telegram_bot_token_here":
        logger.info("Starting Telegram Bot resilient long-polling...")
        try:
            # Delete any webhook and drop outdated pending updates on startup
            await bot.delete_webhook(drop_pending_updates=True)
            while True:
                try:
                    await dp.start_polling(bot, handle_signals=False)
                    break
                except Exception as poll_err:
                    logger.warning(f"Polling connection interrupted ({poll_err}). Reconnecting in 3 seconds...")
                    await asyncio.sleep(3)
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Polling received shutdown signal.")
        finally:
            scheduler.shutdown()
            await bot.session.close()
            logger.info("Bot session and scheduler closed cleanly.")
    else:
        logger.info("Database and Scheduler verified. Exiting startup sequence (running in worker test mode).")
        scheduler.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("JobHunter AI stopped.")
