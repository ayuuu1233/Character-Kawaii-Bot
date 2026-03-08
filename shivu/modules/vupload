import os
import re
import unicodedata
import tempfile
import aiohttp
from pymongo import ReturnDocument
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, sudo_users, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT

WRONG_FORMAT_TEXT_VIDEO = """⚠️ *Invalid Format!*

Please use the correct format:

`/upvideo <Video_URL> <character_name> <anime_name> <rarity_number>`.

Examples:

- `/upvideo https://files.catbox.moe/btit4d.mp4 Naruto Naruto_Shonen 1`
"""

RARITY_MAP = {
    1: "⚜️ Animated",
    2: "🌟 Ultra Rare",
    3: "⭐ Rare",
    4: "✨ Common",
    5: "🔸 Basic",
}

CATEGORY_MAP = {
    '❄️': '❄️ Infinity ❄️',
    '🔥': '🔥 Flame Master 🔥',
    '🌊': '🌊 Water Bender 🌊',
    '⚡': '⚡ Lightning Wizard ⚡',
}

def get_category(name):
    for emoji, category in CATEGORY_MAP.items():
        if emoji in name:
            return category
    return "🌟 Unknown"

def slugify(value, max_length=50):
    value = str(value)
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "_", value)
    return value[:max_length]

async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'sequence_value': 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return sequence_document['sequence_value']

async def download_to_tempfile(url, headers=None, chunk_size=8192):
    temp_path = None
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to download video. HTTP Status Code: {resp.status}")
            fd, temp_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            with open(temp_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(chunk_size):
                    if not chunk:
                        break
                    f.write(chunk)
    return temp_path

async def upload_video(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        await update.message.reply_text('⛔ *Access Denied!* Only the owner can use this command.')
        return
    try:
        args = context.args
        if len(args) != 4:
            await update.message.reply_text(WRONG_FORMAT_TEXT_VIDEO, parse_mode='Markdown')
            return
        video_url, character_name_raw, anime_name_raw, rarity_number_raw = args
        character_name = character_name_raw.replace('-', ' ').title()
        anime_name = anime_name_raw.replace('-', ' ').title()
        try:
            rarity_key = int(rarity_number_raw)
        except Exception:
            await update.message.reply_text(f"❌ *Invalid Rarity!*\nValid rarities: {', '.join(map(str, RARITY_MAP.keys()))}", parse_mode='Markdown')
            return
        rarity = RARITY_MAP.get(rarity_key)
        if not rarity:
            await update.message.reply_text(f"❌ *Invalid Rarity!*\nValid rarities: {', '.join(map(str, RARITY_MAP.keys()))}", parse_mode='Markdown')
            return
        seq_num = await get_next_sequence_number('character_id')
        character_id = str(seq_num).zfill(3)
        category = get_category(character_name)
        character_data = {
            'img_url': video_url,
            'name': character_name,
            'anime': anime_name,
            'rarity': rarity,
            'id': character_id,
            'category': category
        }
        caption = (
            f"🎥 *New Character Added!*\n\n"
            f"🎭 *Anime:* {anime_name}\n"
            f"🆔 *ID:* {character_id}\n"
            f"🌟 *Name:* {character_name}\n"
            f"🏆 *Rarity:* {rarity}\n"
            f"🔖 *Category:* {category}\n\n"
            f"➼ *Added By:* [{update.effective_user.first_name}](tg://user?id={update.effective_user.id})"
        )
        slug_anime = slugify(anime_name, max_length=40)
        slug_character = slugify(character_name, max_length=40)
        cb_anime = f"search_anime_{slug_anime}"
        cb_character = f"search_character_{slug_character}"
        if len(cb_anime) > 64:
            cb_anime = cb_anime[:64]
        if len(cb_character) > 64:
            cb_character = cb_character[:64]
        buttons = [
            [InlineKeyboardButton("📺 View in Channel", url=f"https://t.me/{CHARA_CHANNEL_ID}/{character_id}")],
            [InlineKeyboardButton(f"🔍 Search {anime_name}", callback_data=cb_anime), InlineKeyboardButton(f"🔍 Search {character_name}", callback_data=cb_character)],
            [InlineKeyboardButton("📩 Report Issue", url=f"https://t.me/{SUPPORT_CHAT}")]
        ]
        local_file = None
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            local_file = await download_to_tempfile(video_url, headers=headers)
        except Exception as e:
            await update.message.reply_text(f"❌ *Invalid URL or Unable to Download Video!*\nError: {str(e)}", parse_mode='Markdown')
            if local_file and os.path.exists(local_file):
                os.remove(local_file)
            return
        try:
            if local_file and os.path.exists(local_file):
                with open(local_file, "rb") as video:
                    message = await context.bot.send_video(
                        chat_id=CHARA_CHANNEL_ID,
                        video=video,
                        caption=caption,
                        parse_mode='Markdown',
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                character_data['message_id'] = message.message_id
                await collection.insert_one(character_data)
                await update.message.reply_text("✅ *Character Added Successfully!*", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ *Failed to Upload Character! Local file missing.*", parse_mode='Markdown')
        except Exception as e:
            await update.message.reply_text(f"❌ *Failed to Upload Character!*\nError: {str(e)}", parse_mode='Markdown')
        finally:
            if local_file and os.path.exists(local_file):
                os.remove(local_file)
    except Exception as e:
        await update.message.reply_text(f"❌ *Unexpected Error:*\n{str(e)}", parse_mode='Markdown')

              application.add_handler(CommandHandler('upvideo', upload_video))
