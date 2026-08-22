import logging
from datetime import datetime
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.database.database import get_session, get_active_subscribers, get_recent_jobs
from app.jobs.collector import JobCollector
from app.jobs.matcher import JobMatcher

logger = logging.getLogger(__name__)


async def run_periodic_collection() -> None:
    """Scheduled task to scrape and store latest jobs."""
    logger.info("Executing scheduled job collection...")
    try:
        count = await JobCollector.collect_and_store_jobs()
        logger.info(f"Scheduled collection added {count} new jobs.")
    except Exception as e:
        logger.error(f"Error during scheduled collection: {e}", exc_info=True)


async def send_daily_digest(bot: Bot) -> None:
    """Send personalized daily job digest to all subscribed users."""
    logger.info("Starting daily job digest delivery...")
    try:
        async with get_session() as session:
            subscribers = await get_active_subscribers(session)
            jobs = await get_recent_jobs(session, limit=50)

            if not jobs:
                logger.info("No active jobs available for digest.")
                return

            for user in subscribers:
                # Score jobs for this specific subscriber (only eligible)
                scored = []
                for job in jobs:
                    match_info = JobMatcher.match(user, job)
                    if match_info.get("is_eligible", True) and match_info["score"] >= settings.MATCH_THRESHOLD:
                        scored.append((job, match_info))

                scored.sort(key=lambda x: x[1]["score"], reverse=True)
                top_matches = scored[:5]

                if not top_matches:
                    continue

                digest_lines = [
                    f"☀️ **Good Morning, {user.first_name or 'Job Hunter'}!**",
                    f"Here is your curated AI Job Digest for today (Threshold: ≥{settings.MATCH_THRESHOLD}%):\n"
                ]

                for i, (job, match_info) in enumerate(top_matches, start=1):
                    digest_lines.append(
                        f"**{i}. {job.title}** @ {job.company}\n"
                        f"📊 Match: `{match_info['score']}%` | 📍 {job.location}\n"
                        f"💡 _{match_info['reasons']}_\n"
                        f"🔗 [Apply Here]({job.url})\n"
                    )

                digest_lines.append("Use `/jobs` anytime to browse full interactive job cards.")
                message_text = "\n".join(digest_lines)

                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message_text,
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
                    user.last_digest_at = datetime.utcnow()
                except Exception as send_err:
                    logger.warning(f"Failed to send digest to user {user.telegram_id}: {send_err}")

        logger.info("Daily job digest delivery complete.")
    except Exception as e:
        logger.error(f"Error during daily digest execution: {e}", exc_info=True)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Initialize and schedule periodic tasks."""
    scheduler = AsyncIOScheduler()

    # Parse digest time (HH:MM)
    time_parts = settings.DIGEST_TIME.split(":")
    hour = int(time_parts[0]) if len(time_parts) > 0 else 9
    minute = int(time_parts[1]) if len(time_parts) > 1 else 0

    # Schedule Daily Digest
    scheduler.add_job(
        send_daily_digest,
        trigger=CronTrigger(hour=hour, minute=minute),
        args=[bot],
        id="daily_digest_job",
        replace_existing=True,
    )

    # Schedule Periodic Scraper
    scheduler.add_job(
        run_periodic_collection,
        trigger=IntervalTrigger(hours=settings.SCRAPE_INTERVAL_HOURS),
        id="periodic_scrape_job",
        replace_existing=True,
    )

    return scheduler
