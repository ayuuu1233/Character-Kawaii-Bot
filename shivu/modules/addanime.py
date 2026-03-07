import re
import html
from urllib.parse import urlparse

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, filters, CallbackContext
from pymongo import ReturnDocument

from shivu import application, sudo_users, collection, SUPPORT_CHAT

anime_cache = []

WRONG_FORMAT_TEXT = """Incorrect Usage ❌️.

Correct Usage: /addanime anime_name post_url img_url



Ensure:

- anime_name: Name of the anime.

- post_url: A valid URL (e.g., Wikipedia or MyAnimeList page).

- img_url: Direct URL to an image of the anime.



Please try again."""


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


async def get_next_sequence_number(sequence_name: str) -> int:
    try:
        sequence_document = await collection.find_one_and_update(
            {"_id": sequence_name},
            {"$inc": {"sequence_value": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        if not sequence_document:
            return 1
        return sequence_document.get("sequence_value", 1)
    except Exception as e:
        print(f"Error fetching sequence number: {e}")
        return 1


async def add_anime(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text("You do not have permission to use this command. Please contact the bot owner.")
        return

    try:
        args = context.args
        if len(args) != 3:
            await update.message.reply_text(WRONG_FORMAT_TEXT)
            return

        anime_name = args[0].replace('-', ' ').title()
        post_url = args[1]
        img_url = args[2]

        if not (is_valid_url(post_url) and is_valid_url(img_url)):
            await update.message.reply_text(
                "One or more provided URLs are invalid. Ensure both URLs are properly formatted and try again."
            )
            return

        anime_id = str(await get_next_sequence_number("anime_id")).zfill(2)

        anime_data = {
            "id": anime_id,
            "name": anime_name,
            "post_url": post_url,
            "img_url": img_url
        }

        try:
            safe_name = html.escape(anime_name, quote=True)
            safe_post = html.escape(post_url, quote=True)
            safe_first = html.escape(update.effective_user.first_name or "", quote=True)
            message = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=img_url,
                caption=(
                    f"<b>Anime Name:</b> {safe_name}\n"
                    f"<b>More Info:</b> <a href='{safe_post}'>Click Here</a>\n"
                    f"<b>ID:</b> {anime_id}\n"
                    f"Added by <a href='tg://user?id={update.effective_user.id}'>{safe_first}</a>"
                ),
                parse_mode="HTML"
            )
            anime_data["message_id"] = message.message_id

            await collection.insert_one(anime_data)
            await update.message.reply_text("Anime successfully added to the database!")
        except Exception as e:
            await update.message.reply_text(f"Failed to post anime in the chat. Error: {e}")
            return
    except Exception as e:
        await update.message.reply_text(
            f"An error occurred while processing your request. Error: {e}\n"
            f"If you believe this is a bug, please report it at {SUPPORT_CHAT}."
        )


async def reload_anime_data(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text("You do not have permission to use this command.")
        return

    try:
        global anime_cache
        anime_cache = await collection.find().to_list(length=None)

        await update.message.reply_text("Anime Sanctum Data Has Been Reloaded From DB ☑️.")
    except Exception as e:
        await update.message.reply_text(f"Failed to reload data from the database. Error: {str(e)}")


async def get_anime(update: Update, context: CallbackContext) -> None:
    anime_name = update.message.text.strip().lower()

    for anime in anime_cache:
        if anime.get("name", "").lower() == anime_name:
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="More Info", url=anime.get("post_url", ""))]]
            )

            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=anime.get("img_url", ""),
                caption=f"<b>Anime Name:</b> {html.escape(anime.get('name',''), quote=True)}\n<b>More Info:</b> Below 👇",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            return

    await update.message.reply_text(
        "Anime not found in the database. Please check the name and try again."
    )


ADD_ANIME_HANDLER = CommandHandler("addanime", add_anime, block=False)
RELOAD_HANDLER = CommandHandler("reload", reload_anime_data, block=False)
ANIME_FETCH_HANDLER = MessageHandler(filters.TEXT & ~filters.COMMAND, get_anime, block=False)

application.add_handler(ADD_ANIME_HANDLER)
application.add_handler(RELOAD_HANDLER)
application.add_handler(ANIME_FETCH_HANDLER)
