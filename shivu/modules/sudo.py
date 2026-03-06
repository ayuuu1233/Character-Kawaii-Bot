from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters
from shivu import application, sudo_users, db

OWNER_ID = 5158013355
# MongoDB collection for storing sudo users
sudo_collection = db['sudos']

async def add_sudo(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Only the owner can add sudo users.")
        return

    if update.message.reply_to_message:
        new_sudo = update.message.reply_to_message.from_user.id
        existing_sudo = await sudo_collection.find_one({'user_id': new_sudo})
        if existing_sudo:
            await update.message.reply_text("⚠️ This user is already a sudo.")
        else:
            await sudo_collection.insert_one({'user_id': new_sudo})
            await update.message.reply_text(
                f"✅ Successfully added [this user](tg://user?id={new_sudo}) as a sudo.",
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text("⚠️ Please reply to a user's message to add them as a sudo.")

async def rm_sudo(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ Only the owner can remove sudo users.")
        return

    if update.message.reply_to_message:
        remove_sudo = update.message.reply_to_message.from_user.id
        result = await sudo_collection.delete_one({'user_id': remove_sudo})
        if result.deleted_count:
            await update.message.reply_text(
                f"✅ Successfully removed [this user](tg://user?id={remove_sudo}) from sudo.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠️ This user is not a sudo.")
    else:
        await update.message.reply_text("⚠️ Please reply to a user's message to remove them as a sudo.")

async def sudo_list(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        await update.message.reply_text("❌ You don't have permission to view the sudo list.")
        return

    sudo_users_cursor = sudo_collection.find({})
    sudo_list = await sudo_users_cursor.to_list(length=None)
    if sudo_list:
        sudo_ids = [
            f"🔹 [User ID: {sudo['user_id']}](tg://user?id={sudo['user_id']})"
            for sudo in sudo_list
        ]
        await update.message.reply_text(
            "🛡️ **Sudo Users List**:\n\n" + "\n".join(sudo_ids),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("⚠️ There are no sudo users.")

# Register the command handlers
application.add_handler(CommandHandler("addsudo", add_sudo))
application.add_handler(CommandHandler("rmsudo", rm_sudo))
application.add_handler(CommandHandler("sudolist", sudo_list))
