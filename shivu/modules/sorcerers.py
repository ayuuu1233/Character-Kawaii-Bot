from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaVideo
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from shivu import OWNER_ID
from shivu import application, GRADE4, GRADE3, GRADE2, GRADE1, SPECIALGRADE

OWNER_ID = 5158013355

# Grade database with emoji indicators
grades = {
    "Special grade": {
        "users": SPECIALGRADE,
        "video_url": "https://files.catbox.moe/0noa8s.mp4",
        "emoji": "🌟"
    },
    "Grade 1": {
        "users": GRADE1,
        "video_url": "https://files.catbox.moe/0o1307.mp4",
        "emoji": "🔹"
    },
    "Grade 2": {
        "users": GRADE2,
        "video_url": "https://files.catbox.moe/75cts9.mp4",
        "emoji": "🔸"
    },
    "Grade 3": {
        "users": GRADE3,
        "video_url": "https://files.catbox.moe/4hdn74.mp4",
        "emoji": "⚪"
    },
    "Grade 4": {
        "users": GRADE4,
        "video_url": "https://files.catbox.moe/4hdn74.mp4",
        "emoji": "⚫"
    },
}

# Helper: Verify if user is Special Grade
def is_special_grade(user_id):
    return user_id in grades["Special grade"]["users"] or user_id == OWNER_ID

# Helper: Display grade nicely
def get_grade_display(grade_key):
    info = grades.get(grade_key, {})
    emoji = info.get("emoji", "")
    count = len(info.get("users", []))
    return f"{emoji} {grade_key} ({count} users)"

# ---------------- COMMANDS ---------------- #

# Add a user to a grade (God-tier)
async def add_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_special_grade(user_id):
        await update.message.reply_text("❌ Only Special Grade users can use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addgrade <user_id> <grade>")
        return

    target_user_id = int(context.args[0])
    grade = " ".join(context.args[1:]).title()

    if grade not in grades:
        await update.message.reply_text(
            "❌ Invalid grade. Available grades: Special Grade, Grade 1, Grade 2, Grade 3, Grade 4."
        )
        return

    # Remove user from all other grades
    for g in grades.values():
        if target_user_id in g["users"]:
            g["users"].remove(target_user_id)

    if target_user_id not in grades[grade]["users"]:
        grades[grade]["users"].append(target_user_id)
    await update.message.reply_text(f"✅ User with ID {target_user_id} added to {get_grade_display(grade)}.")

# Remove user from all grades
async def remove_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_special_grade(user_id):
        await update.message.reply_text("❌ Only Special Grade users can use this command.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("Usage: /remgrade <user_id>")
        return

    target_user_id = int(context.args[0])
    removed = False
    for g in grades.values():
        if target_user_id in g["users"]:
            g["users"].remove(target_user_id)
            removed = True

    if removed:
        await update.message.reply_text(f"✅ User with ID {target_user_id} removed from all grades.")
    else:
        await update.message.reply_text(f"❌ User with ID {target_user_id} not found in any grade.")

# List sorcerers with interactive buttons
async def list_sorcerers(update: Update, context: ContextTypes.DEFAULT_TYPE, grade="Special grade"):
    response = f"<b><u>{get_grade_display(grade)}</u></b>\n\n"
    for user_id in grades[grade]["users"]:
        try:
            user = await context.bot.get_chat(user_id)
            user_full_name = user.first_name
            if user.last_name:
                user_full_name += f" {user.last_name}"
            user_link = f'<a href="tg://user?id={user_id}">{user_full_name}</a>'
            response += f"├─➩ {user_link}\n"
        except Exception:
            response += f"├─➩ User not found (ID: {user_id})\n"
    response += "╰──────────\n"

    keyboard = [
        [
            InlineKeyboardButton("⬅️", callback_data=f"navigate:prev:{grade}"),
            InlineKeyboardButton("➡️", callback_data=f"navigate:next:{grade}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        media = InputMediaVideo(media=grades[grade]["video_url"], caption=response, parse_mode=ParseMode.HTML)
        await update.callback_query.edit_message_media(media=media, reply_markup=reply_markup)
        await update.callback_query.answer()
    else:
        await update.message.reply_video(video=grades[grade]["video_url"], caption=response,
                                         parse_mode=ParseMode.HTML, reply_markup=reply_markup)

# Navigation handler
async def navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.message is None:
        await query.answer("No message to navigate.")
        return

    data_parts = query.data.split(":")
    direction = data_parts[1]
    current_grade = data_parts[2]

    grades_list = list(grades.keys())
    current_index = grades_list.index(current_grade)
    new_index = (current_index + 1) % len(grades_list) if direction == "next" else (current_index - 1) % len(grades_list)
    new_grade = grades_list[new_index]

    await list_sorcerers(update, context, new_grade)

# ---------------- HANDLERS ---------------- #
application.add_handler(CommandHandler("sorcerers", list_sorcerers))
application.add_handler(CommandHandler("addgrade", add_grade))
application.add_handler(CommandHandler("remgrade", remove_grade))
application.add_handler(CallbackQueryHandler(navigate, pattern=r"^navigate:(prev|next):"))
