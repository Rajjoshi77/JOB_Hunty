import asyncio
import logging
import sys
import os
from aiohttp import web
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


async def health_check_handler(request: web.Request) -> web.Response:
    """HTTP Healthcheck endpoint for Render, Koyeb, Railway."""
    return web.json_response({
        "status": "healthy",
        "service": "JobHunter AI Bot",
        "bot": "online"
    })


async def start_web_server(port: int) -> web.AppRunner:
    """Start standard aiohttp web server on 0.0.0.0 for Render port binding."""
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🚀 Render Web Service bound to 0.0.0.0:{port} successfully.")
    return runner


async def background_initial_scraping() -> None:
    """Pre-populate initial job vacancies in background after web server is live."""
    try:
        await JobCollector.collect_and_store_jobs()
    except Exception as e:
        logger.warning(f"Initial job collection encountered error: {e}")


async def main() -> None:
    """Application entrypoint."""
    logger.info("Initializing JobHunter AI...")

    # 1. Start HTTP web server immediately so Render detects open port instantly
    port = int(os.environ.get("PORT", 10000))
    runner = None
    try:
        runner = await start_web_server(port)
    except Exception as e:
        logger.error(f"Failed to start web server on port {port}: {e}")

    # 2. Initialize database
    await init_db()

    # 3. Trigger initial job collection in background
    asyncio.create_task(background_initial_scraping())

    # 4. Check for bot token
    token = settings.BOT_TOKEN
    if not token or len(token) < 15:
        token = "8943083272:AAHr8eRczMwlh9AkDGQc7Vbzb6zJbsgSeRU"

    # 5. Initialize Telegram Bot & Dispatcher
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()
    dp.include_router(bot_router)

    # 6. Start background scheduler (Daily digests & periodic scraping)
    scheduler = setup_scheduler(bot)
    scheduler.start()
    logger.info(
        f"Scheduler active: Scrapes every {settings.SCRAPE_INTERVAL_HOURS}h | "
        f"Daily digest at {settings.DIGEST_TIME} UTC"
    )

    # 7. Start Telegram Bot resilient polling
    try:
        me = await bot.get_me()
        logger.info(f"✅ Connected to Telegram successfully as @{me.username} (ID: {me.id})")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Telegram API: {e}")

    logger.info("Starting Telegram Bot resilient long-polling...")
    try:
        # Delete any existing webhook and drop stale updates on startup
        await bot.delete_webhook(drop_pending_updates=True)
        while True:
            try:
                await dp.start_polling(bot, handle_signals=False)
                break
            except Exception as poll_err:
                logger.warning(f"Polling connection interrupted ({poll_err}). Reconnecting in 3s...")
                await asyncio.sleep(3)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Polling received shutdown signal.")
    finally:
        scheduler.shutdown()
        await bot.session.close()
        if runner:
            await runner.cleanup()
            logger.info("Bot session and web server closed cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("JobHunter AI stopped.")
