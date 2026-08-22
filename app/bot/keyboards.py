from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard(is_subscribed: bool = True) -> InlineKeyboardMarkup:
    """Generate main interactive dashboard menu."""
    sub_text = "🔕 Unsubscribe Daily Digest" if is_subscribed else "🔔 Subscribe Daily Digest"
    sub_data = "toggle_sub_off" if is_subscribed else "toggle_sub_on"

    buttons = [
        [
            InlineKeyboardButton(text="🎯 View Matched Jobs", callback_data="view_matches_0"),
            InlineKeyboardButton(text="⚡ Refresh Jobs", callback_data="refresh_jobs"),
        ],
        [
            InlineKeyboardButton(text="👤 My Profile", callback_data="view_profile"),
            InlineKeyboardButton(text="⚙️ Preferences & Filters", callback_data="view_preferences"),
        ],
        [
            InlineKeyboardButton(text=sub_text, callback_data=sub_data),
        ],
        [
            InlineKeyboardButton(text="📩 Send Instant Digest", callback_data="send_digest_now"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_job_card_keyboard(job_id: int, job_url: str, current_index: int, total_count: int) -> InlineKeyboardMarkup:
    """Generate action buttons for an individual job match card."""
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Prev", callback_data=f"view_matches_{current_index - 1}")
        )
    if current_index < total_count - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="Next ➡️", callback_data=f"view_matches_{current_index + 1}")
        )

    buttons = [
        [
            InlineKeyboardButton(text="🚀 Apply Now", url=job_url),
            InlineKeyboardButton(text="⭐ Save Job", callback_data=f"save_job_{job_id}"),
        ],
    ]
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([
        InlineKeyboardButton(text="🔙 Main Menu", callback_data="back_to_menu"),
        InlineKeyboardButton(text="⚙️ Preferences", callback_data="view_preferences"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_preferences_keyboard() -> InlineKeyboardMarkup:
    """Generate interactive preferences modification keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="🎯 Target Roles", callback_data="guide_roles"),
            InlineKeyboardButton(text="💻 Tech Stack / Skills", callback_data="guide_skills"),
        ],
        [
            InlineKeyboardButton(text="📍 Location Priorities", callback_data="guide_locations"),
            InlineKeyboardButton(text="🏠 Work Mode", callback_data="guide_workmode"),
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Experience Level", callback_data="guide_exp"),
            InlineKeyboardButton(text="💰 Min Salary", callback_data="guide_salary"),
        ],
        [
            InlineKeyboardButton(text="🔄 Reset to Full Defaults", callback_data="reset_preferences_default"),
        ],
        [
            InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
