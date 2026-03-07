import logging
from pymongo import ReturnDocument
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, settings_collection, OWNER_ID

# ----------------- LOGGING ----------------- #
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------- FREQUENCY DB FUNCTIONS ----------------- #
async def get_frequency() -> int:
    """Get the current message frequency from MongoDB."""
    setting = await settings_collection.find_one({"setting": "frequency"})
    return setting["value"] if setting else 10  # default 10

async def set_frequency(new_frequency: int):
    """Set a new frequency value in MongoDB."""
    await settings_collection.update_one(
        {"setting": "frequency"},
        {"$set": {"value": new_frequency}},
        upsert=True
    )

# ----------------- SUDO CHECK ----------------- #
async def is_sudo(user_id: int) -> bool:
    """Check if the user is sudo."""
    setting = await settings_collection.find_one({"setting": "sudo_users"})
    if setting and isinstance(setting["value"], list):
        return user_id in setting["value"]
    return user_id == OWNER_ID  # fallback owner ID

# ----------------- COMMAND HANDLER ----------------- #
async def change_freq(update: Update, context: CallbackContext) -> None:
    user = update.effective_user

    if not await is_sudo(user.id):
        await update.message.reply_text("❌ You do not have permission to use this command.")
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text("⚠️ Incorrect format. Use: /cfreq NUMBER")
        return

    try:
        new_frequency = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ The frequency must be a number.")
        return

    if new_frequency < 1:
        await update.message.reply_text("⚠️ Frequency must be at least 1.")
        return
    if new_frequency > 10000:
        await update.message.reply_text("⚠️ That's too high! Keep it below 10,000.")
        return

    # Ask for confirmation using inline button
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Change", callback_data=f"confirm_freq:{new_frequency}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Are you sure you want to change character appearance frequency to every {new_frequency} messages?",
        reply_markup=reply_markup
    )

# ----------------- CALLBACK HANDLER ----------------- #
async def confirm_freq_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user

    # Extract frequency from callback data
    data = query.data
    if not data.startswith("confirm_freq:"):
        return
    new_frequency = int(data.split(":")[1])

    # Verify sudo again for safety
    if not await is_sudo(user.id):
        await query.answer("❌ You do not have permission.", show_alert=True)
        return

    try:
        await set_frequency(new_frequency)
        await query.edit_message_text(
            f"✅ Successfully changed character appearance frequency to every {new_frequency} messages."
        )
        logger.info(f"{user.username} ({user.id}) changed frequency to {new_frequency}")
    except Exception as e:
        logger.error(f"Failed to set frequency: {e}")
        await query.edit_message_text("❌ Failed to change frequency due to an error.")

# ----------------- HANDLER REGISTRATION ----------------- #
application.add_handler(CommandHandler("cfreq", change_freq, block=False))
application.add_handler(CallbackQueryHandler(confirm_freq_callback, pattern=r"^confirm_freq:"))
