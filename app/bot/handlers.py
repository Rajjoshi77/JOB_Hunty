import json
import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, update

from app.database.database import get_session, get_or_create_user, get_recent_jobs
from app.database.models import (
    User,
    Job,
    JobMatch,
    DEFAULT_SKILLS,
    DEFAULT_ROLES,
    DEFAULT_LOCATION_TIERS,
)
from app.jobs.matcher import JobMatcher
from app.jobs.collector import JobCollector
from app.bot.keyboards import (
    get_main_menu_keyboard,
    get_job_card_keyboard,
    get_preferences_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="main_router")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command: register user profile and display dashboard."""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    async with get_session() as session:
        user = await get_or_create_user(session, user_id, username, first_name)
        is_sub = user.is_subscribed

    welcome_text = (
        f"👋 **Welcome to JobHunter AI, {first_name or 'there'}!** 🎯\n\n"
        "I am your automated AI job search assistant, pre-configured with your **Full Tech Stack**, **Fresher/AI/Software Engineer Roles**, and **Tiered Location Priority System**:\n"
        "• 🔥 **Ahmedabad** (Priority 100)\n"
        "• 🔥 **Gujarat** (Priority 95)\n"
        "• 🟢 **Remote India** (Priority 90)\n"
        "• 🟢 **Bengaluru / Hyderabad / Pune** (Priority 85)\n"
        "• 🟡 **Delhi NCR / Mumbai / Other Hubs** (Priority 70)\n\n"
        "✨ **Quick Preference Commands:**\n"
        "• `/preferences` - View & customize your search criteria\n"
        "• `/jobs` - Explore your highest matching positions\n"
        "• `/setroles <roles>` - Update target job titles\n"
        "• `/setskills <skills>` - Update your tech stack\n"
        "• `/setexp <years>` - Update experience (default: 0)\n"
        "• `/setworkmode <Remote / Hybrid / On-site / Any>`\n\n"
        "Select an option below to get started:"
    )
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(is_subscribed=is_sub),
        parse_mode="Markdown",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    help_text = (
        "🤖 **JobHunter AI - Help & Commands**\n\n"
        "📌 **Core Navigation:**\n"
        "• `/start` - Main menu & dashboard\n"
        "• `/jobs` - Browse recommended jobs with match scores\n"
        "• `/preferences` - View and modify your search parameters\n"
        "• `/profile` - View your active profile summary\n"
        "• `/digest` - Receive an instant digest of top jobs\n"
        "• `/subscribe` or `/unsubscribe` - Daily notification toggle\n\n"
        "⚙️ **Dynamic Filter Modifiers:**\n"
        "• `/setroles React Developer, AI Engineer, Fresher`\n"
        "• `/setskills JavaScript, React, Node, Python, PyTorch`\n"
        "• `/setlocations Ahmedabad, Gujarat, Remote India, Bengaluru`\n"
        "• `/setworkmode Remote` (or Hybrid / Any / On-site)\n"
        "• `/setexp 0` (0 for Fresher / Entry-level)\n"
        "• `/setsalary 600000` (e.g. 6 LPA in INR)\n"
    )
    await message.answer(help_text, parse_mode="Markdown")


@router.message(Command("preferences"))
async def cmd_preferences(message: Message) -> None:
    """Show detailed user preferences dashboard."""
    async with get_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        pref_text = (
            f"⚙️ **Your Job Search Preferences**\n\n"
            f"🎯 **Target Roles:**\n`{user.preferred_roles[:180]}...`\n\n"
            f"💻 **Tech Stack:**\n`{user.skills[:180]}...`\n\n"
            f"📍 **Location Strategy:**\n"
            f"• Priority 100: Ahmedabad\n"
            f"• Priority 95: Gujarat (Gandhinagar, Surat, Vadodara, Rajkot)\n"
            f"• Priority 90: Remote India\n"
            f"• Priority 85: Bengaluru / Hyderabad / Pune\n"
            f"• Priority 70: Delhi / Mumbai / Chennai / Kolkata / Kochi\n\n"
            f"🏠 **Work Mode:** `{user.work_mode}`\n"
            f"👨‍💻 **Experience:** `{user.experience_years} years (Fresher Friendly)`\n"
            f"💰 **Min Salary:** `{user.min_salary if user.min_salary > 0 else 'Flexible / Any'}`\n\n"
            "Tap any category below to customize:"
        )
    await message.answer(
        pref_text,
        reply_markup=get_preferences_keyboard(),
        parse_mode="Markdown",
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    """Display user profile summary."""
    await cmd_preferences(message)


@router.message(Command("setskills"))
async def cmd_set_skills(message: Message) -> None:
    """Update user skills."""
    args = message.text.replace("/setskills", "").strip()
    if not args:
        await message.answer("⚠️ Please provide skills separated by comma.\nExample: `/setskills React, Node.js, Python, MongoDB, Tailwind`", parse_mode="Markdown")
        return

    async with get_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        user.skills = args
        await session.commit()

    await message.answer(f"✅ **Tech Stack updated successfully:**\n`{args}`", parse_mode="Markdown")


@router.message(Command("setroles"))
async def cmd_set_roles(message: Message) -> None:
    """Update user target job roles."""
    args = message.text.replace("/setroles", "").strip()
    if not args:
        await message.answer("⚠️ Please provide target roles separated by comma.\nExample: `/setroles Software Engineer, MERN Developer, AI Engineer, Junior ML Engineer`", parse_mode="Markdown")
        return

    async with get_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        user.preferred_roles = args
        await session.commit()

    await message.answer(f"✅ **Target roles updated:**\n`{args}`", parse_mode="Markdown")


@router.message(Command("setworkmode"))
async def cmd_set_work_mode(message: Message) -> None:
    """Update work mode preference."""
    args = message.text.replace("/setworkmode", "").strip()
    if not args:
        await message.answer("⚠️ Specify your work mode:\nExample: `/setworkmode Remote` (or `Hybrid`, `On-site`, `Any`)", parse_mode="Markdown")
        return

    async with get_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        user.work_mode = args
        await session.commit()

    await message.answer(f"✅ **Work mode updated:** `{args}`", parse_mode="Markdown")


@router.message(Command("setexp"))
async def cmd_set_exp(message: Message) -> None:
    """Update years of experience."""
    args = message.text.replace("/setexp", "").strip()
    try:
        years = int(args)
    except ValueError:
        await message.answer("⚠️ Please provide a valid number.\nExample: `/setexp 0` (for fresher) or `/setexp 2`", parse_mode="Markdown")
        return

    async with get_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        user.experience_years = max(0, years)
        await session.commit()

    await message.answer(f"✅ **Experience updated:** `{years} years`", parse_mode="Markdown")


@router.message(Command("setsalary"))
async def cmd_set_salary(message: Message) -> None:
    """Update minimum salary requirement."""
    args = message.text.replace("/setsalary", "").strip()
    try:
        sal = int(args.replace(",", "").replace("₹", "").replace("$", ""))
    except ValueError:
        await message.answer("⚠️ Please provide a valid salary amount.\nExample: `/setsalary 500000` (for ₹5 LPA) or `/setsalary 0` for any", parse_mode="Markdown")
        return

    async with get_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        user.min_salary = max(0, sal)
        await session.commit()

    await message.answer(f"✅ **Minimum salary preference updated:** `{sal}`", parse_mode="Markdown")


@router.message(Command("jobs"))
async def cmd_jobs(message: Message) -> None:
    """Show top job matches for current user."""
    await send_job_card(message, user_id=message.from_user.id, card_index=0)


async def send_job_card(event: Message | CallbackQuery, user_id: int, card_index: int = 0) -> None:
    """Render an individual job match card with score, location tier badge, and pagination."""
    async with get_session() as session:
        user = await get_or_create_user(session, user_id)
        jobs = await get_recent_jobs(session, limit=50)

        if not jobs:
            no_jobs_msg = "ℹ️ No active job listings found in database. Click **Refresh Jobs** to fetch latest openings."
            if isinstance(event, CallbackQuery):
                await event.message.edit_text(no_jobs_msg, reply_markup=get_main_menu_keyboard())
            else:
                await event.answer(no_jobs_msg, reply_markup=get_main_menu_keyboard())
            return

        # Score and rank jobs for the user (filter only eligible fresher/beginner jobs)
        scored_jobs = []
        for job in jobs:
            match_res = JobMatcher.match(user, job)
            if match_res.get("is_eligible", True) and match_res["score"] > 0:
                scored_jobs.append((job, match_res))

        if not scored_jobs:
            no_match_msg = (
                "ℹ️ **No Fresher / Beginner jobs found right now matching your criteria.**\n\n"
                "Experienced & Senior positions have been filtered out.\n"
                "Tap **⚡ Refresh Jobs** to fetch latest openings or check your `/preferences`."
            )
            if isinstance(event, CallbackQuery):
                await event.message.edit_text(no_match_msg, reply_markup=get_main_menu_keyboard())
            else:
                await event.answer(no_match_msg, reply_markup=get_main_menu_keyboard())
            return

        # Sort descending by match score
        scored_jobs.sort(key=lambda x: x[1]["score"], reverse=True)

        if card_index < 0:
            card_index = 0
        if card_index >= len(scored_jobs):
            card_index = len(scored_jobs) - 1

        selected_job, match_info = scored_jobs[card_index]
        score = match_info["score"]
        reasons = match_info["reasons"]

        badge = "🔥 Top Match" if score >= 80 else ("⚡ Strong Match" if score >= 60 else "📌 Relevant Match")

        text = (
            f"💼 **{selected_job.title}**\n"
            f"🏢 **Company:** {selected_job.company}\n"
            f"📍 **Location:** {selected_job.location}\n"
            f"💰 **Salary:** {selected_job.salary}\n"
            f"📊 **Compatibility:** `{score}%` ({badge})\n\n"
            f"💡 **AI Match Breakdown:**\n{reasons}\n\n"
            f"📝 **Description Snippet:**\n{selected_job.description[:300]}...\n\n"
            f"🏷️ **Tags:** `{selected_job.tags or 'N/A'}`\n"
            f"🌐 **Source:** {selected_job.source}\n"
            f"🔢 **Match {card_index + 1} of {len(scored_jobs)}**"
        )

        keyboard = get_job_card_keyboard(
            job_id=selected_job.id,
            job_url=selected_job.url,
            current_index=card_index,
            total_count=len(scored_jobs),
        )

        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await event.answer(text, reply_markup=keyboard, parse_mode="Markdown")


# Callback query routers
@router.callback_query(F.data.startswith("view_matches_"))
async def cb_view_matches(callback: CallbackQuery) -> None:
    idx = int(callback.data.split("_")[-1])
    await send_job_card(callback, user_id=callback.from_user.id, card_index=idx)
    await callback.answer()


@router.callback_query(F.data == "view_preferences")
async def cb_view_preferences(callback: CallbackQuery) -> None:
    async with get_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        pref_text = (
            f"⚙️ **Your Job Search Preferences**\n\n"
            f"🎯 **Target Roles:**\n`{user.preferred_roles[:180]}...`\n\n"
            f"💻 **Tech Stack:**\n`{user.skills[:180]}...`\n\n"
            f"📍 **Location Strategy:**\n"
            f"• Priority 100: Ahmedabad\n"
            f"• Priority 95: Gujarat (Gandhinagar, Surat, Vadodara, Rajkot)\n"
            f"• Priority 90: Remote India\n"
            f"• Priority 85: Bengaluru / Hyderabad / Pune\n"
            f"• Priority 70: Delhi / Mumbai / Chennai / Kolkata / Kochi\n\n"
            f"🏠 **Work Mode:** `{user.work_mode}`\n"
            f"👨‍💻 **Experience:** `{user.experience_years} years (Fresher Friendly)`\n"
            f"💰 **Min Salary:** `{user.min_salary if user.min_salary > 0 else 'Flexible / Any'}`"
        )
    await callback.message.edit_text(pref_text, reply_markup=get_preferences_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "view_profile")
async def cb_view_profile(callback: CallbackQuery) -> None:
    await cb_view_preferences(callback)


@router.callback_query(F.data == "guide_roles")
async def cb_guide_roles(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "🎯 **How to update target roles:**\n"
        "Send the command:\n"
        "`/setroles Software Engineer, MERN Developer, Frontend Developer, AI Engineer, Software Engineer - Fresher`",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "guide_skills")
async def cb_guide_skills(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "💻 **How to update Tech Stack / Skills:**\n"
        "Send the command:\n"
        "`/setskills React, Node.js, Python, TypeScript, MongoDB, PostgreSQL, Tailwind, Next.js, Generative AI`",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "guide_locations")
async def cb_guide_locations(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "📍 **Location Priority Guide:**\n"
        "JobHunter prioritizes jobs in this order:\n"
        "1. 🔥 **Ahmedabad** (Score 100)\n"
        "2. 🔥 **Gujarat** (Score 95)\n"
        "3. 🟢 **Remote India** (Score 90)\n"
        "4. 🟢 **Bengaluru / Hyderabad / Pune** (Score 85)\n"
        "5. 🟡 **Delhi / Mumbai / Other Metros** (Score 70)\n\n"
        "Jobs outside India or on-site abroad receive lower score rather than being blindly discarded.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "guide_workmode")
async def cb_guide_workmode(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "🏠 **How to update Work Mode:**\n"
        "Send the command:\n"
        "• `/setworkmode Remote`\n"
        "• `/setworkmode Hybrid`\n"
        "• `/setworkmode Any`",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "guide_exp")
async def cb_guide_exp(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "👨‍💻 **How to update Experience:**\n"
        "Send `/setexp 0` for Fresher/Graduate or `/setexp 2` for 2 years.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "guide_salary")
async def cb_guide_salary(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "💰 **How to set Minimum Salary:**\n"
        "Send `/setsalary 600000` (e.g. ₹6 LPA) or `/setsalary 0` for any.",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "reset_preferences_default")
async def cb_reset_preferences(callback: CallbackQuery) -> None:
    async with get_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        user.skills = DEFAULT_SKILLS
        user.preferred_roles = DEFAULT_ROLES
        user.location_tiers = DEFAULT_LOCATION_TIERS
        user.experience_years = 0
        user.work_mode = "Any (Remote, Hybrid, On-site)"
        user.min_salary = 0
        await session.commit()

    await callback.answer("✅ Preferences reset to your full stack & Gujarat/India defaults!", show_alert=True)
    await cb_view_preferences(callback)


@router.callback_query(F.data == "refresh_jobs")
async def cb_refresh_jobs(callback: CallbackQuery) -> None:
    await callback.answer("⏳ Scraping & aggregating latest jobs...", show_alert=False)
    added = await JobCollector.collect_and_store_jobs()
    await callback.message.answer(f"✅ Job refresh complete. Added **{added}** new positions!", parse_mode="Markdown")
    await send_job_card(callback, user_id=callback.from_user.id, card_index=0)


@router.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery) -> None:
    async with get_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        is_sub = user.is_subscribed
    await callback.message.edit_text(
        "🎯 **JobHunter AI Dashboard**\nSelect an option below:",
        reply_markup=get_main_menu_keyboard(is_subscribed=is_sub),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.in_(["toggle_sub_on", "toggle_sub_off"]))
async def cb_toggle_sub(callback: CallbackQuery) -> None:
    new_status = callback.data == "toggle_sub_on"
    async with get_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        user.is_subscribed = new_status
        await session.commit()

    msg = "🔔 Daily Job Digest enabled!" if new_status else "🔕 Daily Job Digest disabled."
    await callback.answer(msg, show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=get_main_menu_keyboard(is_subscribed=new_status))


@router.callback_query(F.data.startswith("save_job_"))
async def cb_save_job(callback: CallbackQuery) -> None:
    job_id = int(callback.data.split("_")[-1])
    async with get_session() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        match_stmt = select(JobMatch).where(
            JobMatch.user_id == user.id, JobMatch.job_id == job_id
        )
        match_obj = (await session.execute(match_stmt)).scalar_one_or_none()
        if not match_obj:
            match_obj = JobMatch(user_id=user.id, job_id=job_id, is_saved=True)
            session.add(match_obj)
        else:
            match_obj.is_saved = True
        await session.commit()

    await callback.answer("⭐ Job saved to your favorites!", show_alert=True)


@router.message(Command("digest"))
async def cmd_digest(message: Message) -> None:
    """Send an instant personalized job digest directly to the user."""
    await send_user_digest(message, user_id=message.from_user.id)


@router.callback_query(F.data == "send_digest_now")
async def cb_send_digest_now(callback: CallbackQuery) -> None:
    """Send an instant personalized job digest via callback query."""
    await callback.answer("📩 Generating your personalized job digest...", show_alert=False)
    await send_user_digest(callback, user_id=callback.from_user.id)


async def send_user_digest(event: Message | CallbackQuery, user_id: int) -> None:
    """Compile and send a formatted job digest to the user."""
    async with get_session() as session:
        user = await get_or_create_user(session, user_id)
        jobs = await get_recent_jobs(session, limit=60)

        if not jobs:
            msg = "ℹ️ No jobs currently found. Click **⚡ Refresh Jobs** to fetch latest openings."
            if isinstance(event, CallbackQuery):
                await event.message.answer(msg, parse_mode="Markdown")
            else:
                await event.answer(msg, parse_mode="Markdown")
            return

        scored = []
        for job in jobs:
            match_info = JobMatcher.match(user, job)
            if match_info.get("is_eligible", True) and match_info["score"] > 0:
                scored.append((job, match_info))

        scored.sort(key=lambda x: x[1]["score"], reverse=True)
        top_matches = scored[:5]

        if not top_matches:
            msg = "ℹ️ No matching fresher positions found. Try adjusting your preferences with `/preferences`."
            if isinstance(event, CallbackQuery):
                await event.message.answer(msg, parse_mode="Markdown")
            else:
                await event.answer(msg, parse_mode="Markdown")
            return

        digest_lines = [
            f"☀️ **Your Daily AI Job Digest, {user.first_name or 'Job Hunter'}!**\n",
            "Here are today's top curated fresher & beginner openings from **official company career portals**:\n"
        ]

        for i, (job, match_info) in enumerate(top_matches, start=1):
            digest_lines.append(
                f"**{i}. {job.title}**\n"
                f"🏢 **Company:** {job.company}\n"
                f"📍 **Location:** {job.location} | 📊 **Match:** `{match_info['score']}%`\n"
                f"💡 _{match_info['reasons']}_\n"
                f"🔗 [🚀 Apply Directly on Official Portal]({job.url})\n"
            )

        digest_lines.append("Use `/jobs` to browse interactive job cards or `/preferences` to adjust filters.")
        digest_text = "\n".join(digest_lines)

        if isinstance(event, CallbackQuery):
            await event.message.answer(digest_text, parse_mode="Markdown", disable_web_page_preview=True)
        else:
            await event.answer(digest_text, parse_mode="Markdown", disable_web_page_preview=True)

