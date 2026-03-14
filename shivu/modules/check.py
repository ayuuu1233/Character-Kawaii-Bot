import urllib.request
import os
from html import escape

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler

from shivu import application, collection, user_collection

async def check_character(update: Update, context: CallbackContext) -> None:
try:
args = context.args

    if len(args) < 1 or not args[0].isdigit():
        await update.message.reply_text(
            "Incorrect format.\nUse: /check character_id [page]"
        )
        return

    character_id = args[0]
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1

    character = await collection.find_one({"id": character_id})

    if not character:
        await update.message.reply_text("❌ Character not found.")
        return

    # Global seized count
    global_count = await user_collection.count_documents(
        {"characters.id": character["id"]}
    )

    response_message = (
        f"<b>🧋 ᴏᴡᴏ! ᴄʜᴇᴄᴋ ᴏᴜᴛ ᴛʜɪs ᴄʜᴀʀᴀᴄᴛᴇʀ !!</b>\n\n"
        f"ID: {character['id']}\n"
        f"Name: <b>{escape(character['name'])}</b>\n"
        f"Anime: <b>{escape(character['anime'])}</b>\n"
        f"Rarity: <b>{character['rarity']}</b>\n\n"
        f"🌐 <b>Globally Seized:</b> {global_count}x"
    )

    # Fetch users who have this character
    cursor = user_collection.find(
        {"characters.id": character_id},
        {
            "id": 1,
            "first_name": 1,
            "last_name": 1,
            "username": 1,
            "profile_name": 1,
            "characters.$": 1,
        },
    ).sort([("characters.count", -1)])

    users = await cursor.to_list(length=None)

    per_page = 10
    total_pages = max(1, (len(users) + per_page - 1) // per_page)

    start = (page - 1) * per_page
    end = start + per_page

    users_page = users[start:end]

    if users_page:
        response_message += f"\n\n🌐 <b>Top Grabbers (Page {page}/{total_pages})</b>\n\n"

        for i, user in enumerate(users_page, start=start + 1):

            full_name = (
                user.get("profile_name")
                or f"{user.get('first_name','')} {user.get('last_name','')}".strip()
                or user.get("username", "Unknown")
            )

            mention = f"<a href='tg://user?id={user['id']}'>{escape(full_name)}</a>"

            response_message += f"{i}. {mention}\n"

    else:
        response_message += "\n\nNo users found with this character."

    # Pagination buttons
    buttons = []

    if page > 1:
        buttons.append(
            InlineKeyboardButton(
                "⬅️ Previous", callback_data=f"page_{character_id}_{page-1}"
            )
        )

    if page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                "➡️ Next", callback_data=f"page_{character_id}_{page+1}"
            )
        )

    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None

    # If callback (pagination)
    if update.callback_query:

        if character.get("video_url"):
            await update.callback_query.edit_message_caption(
                caption=response_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        else:
            await update.callback_query.edit_message_caption(
                caption=response_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

    else:

        if character.get("video_url"):
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=character["video_url"],
                caption=response_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        else:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=character["img_url"],
                caption=response_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

except Exception as e:
    print("Check error:", e)

    if update.message:
        await update.message.reply_text("❌ Error occurred.")

async def handle_callback_query(update: Update, context: CallbackContext):

query = update.callback_query
data = query.data

try:

    if data.startswith("page_"):

        _, char_id, page = data.split("_")

        context.args = [char_id, page]

        await check_character(update, context)

        await query.answer()

    else:

        await query.answer("Unknown action.", show_alert=True)

except Exception as e:

    print("Callback error:", e)

    await query.answer("Error occurred.", show_alert=True)

CHECK_HANDLER = CommandHandler("check", check_character)

application.add_handler(
CallbackQueryHandler(handle_callback_query, pattern="^page_")
)

application.add_handler(CHECK_HANDLER)
