from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext
from datetime import datetime, timedelta
from shivu import application, user_collection
from shivu import shivuu as app

MUST_JOIN = "upper_moon_chat"  # Replace with your group/channel username or ID
allowed_group_id = -1001945969614  # Replace with your allowed group ID
COOLDOWN_HOURS = 5  # Cooldown period in hours

# Function to format remaining time into a readable string
def format_time(seconds):
    duration = timedelta(seconds=seconds)
    days, seconds = duration.days, duration.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{days}d {hours}h {minutes}m"

# Function to send a sticker
async def send_sticker(chat_id, sticker_id, app):
    try:
        await app.send_sticker(chat_id, sticker_id)
    except Exception as e:
        print(f"Error sending sticker: {e}")

# Function to handle bonus claims
async def claim_reward(update: Update, context: CallbackContext):
    message = update.message
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Ensure the command is used in the allowed group
    if chat_id != allowed_group_id:
        return await message.reply_text("⚠️ This command only works in the official group! Please join @Dyna_community.")

    # Send a processing message
    sent_msg = await message.reply_text("🔍 Checking your reward status...")

    # Check if the user has already claimed the bonus recently
    user_data = await user_collection.find_one({'id': user_id}, projection={'eix_suck_claim': 1})
    if user_data and user_data.get('eix_suck_claim'):
        last_claimed_date = user_data.get('eix_suck_claim')
        if last_claimed_date and datetime.utcnow() - last_claimed_date < timedelta(hours=COOLDOWN_HOURS):
            remaining_time = int((timedelta(hours=COOLDOWN_HOURS) - (datetime.utcnow() - last_claimed_date)).total_seconds())
            time_remaining_str = format_time(remaining_time)
            await sent_msg.edit_text(
                f"⏳ You’ve already claimed your bonus! 🕒 Come back in {time_remaining_str}."
            )
            return

    try:
        # Check if the user has joined the required group
        await app.get_chat_member(MUST_JOIN, user_id)
    except UserNotParticipant:
        # Ask the user to join the group if they haven't
        if MUST_JOIN.isalpha():
            link = f"https://t.me/{MUST_JOIN}"
        else:
            chat_info = await app.get_chat(MUST_JOIN)
            link = chat_info.invite_link
        await sent_msg.edit_text(
            "👋 It looks like you haven't joined our support group yet! Join now to claim your bonus.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Join Support Group", url=link)]]
            )
        )
        return

    # Grant the bonus to the user
    await user_collection.update_one(
        {'id': user_id},
        {'$inc': {'balance': 7500000}, '$set': {'eix_suck_claim': datetime.utcnow()}}
    )

    # Send a sticker first
    await send_sticker(chat_id, "CAACAgUAAyEFAASC_Np2AAKg7GdaeMz-doB0adsZqIxa5n-F4PGQAAJJCQACgdQpV9n6Jzs4kf7NNgQ", app)

    # Send a success message as a reply
    await sent_msg.delete()  # Delete the processing message
    await message.reply_text(
        "🎉 **Congratulations!** 🎊\n\n"
        "💰 You’ve claimed a bonus of Ŧ<code>7,500,000</code>!\n\n"
        "🔥 **Keep up the good work! More rewards await you!**",
        reply_to_message_id=message.message_id
    )

# Add the command handler
application.add_handler(CommandHandler("bonus", claim_reward, block=False))
