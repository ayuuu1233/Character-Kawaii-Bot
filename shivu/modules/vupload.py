import os
import re
import unicodedata
import tempfile
import aiohttp
from pymongo import ReturnDocument
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, sudo_users, collection, db, CHARA_CHANNEL_ID, SUPPORT_CHAT

# --- CONFIG & MAPPINGS ---

WRONG_FORMAT_TEXT_VIDEO = """⚠️ *Invalid Format!*

Please use the correct format:
`/upvideo <Video_URL> <character_name> <anime_name> <rarity_number>`

*Examples:*
- `/upvideo https://url.com/vid.mp4 Naruto Naruto-Shippuden 1`
- `/editvideo 001 name Sasuke-Uchiha`
- `/editvideo 001 video_url https://newurl.com/vid.mp4`
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

# --- HELPER FUNCTIONS ---

def get_category(name):
    for emoji, category in CATEGORY_MAP.items():
        if emoji in name:
            return category
    return "🌟 Unknown"

async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'sequence_value': 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return sequence_document['sequence_value']

async def download_to_tempfile(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Download failed. Status: {resp.status}")
            fd, temp_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            with open(temp_path, "wb") as f:
                f.write(await resp.read())
    return temp_path

# --- COMMANDS ---

# 1. UPLOAD VIDEO
async def upload_video(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        return
    try:
        args = context.args
        if len(args) != 4:
            await update.message.reply_text(WRONG_FORMAT_TEXT_VIDEO, parse_mode='Markdown')
            return

        status_msg = await update.message.reply_text("⏳ *Processing video... Please wait Master!*", parse_mode='Markdown')
        
        video_url, char_name_raw, anime_name_raw, rarity_num = args
        char_name = char_name_raw.replace('-', ' ').title()
        anime_name = anime_name_raw.replace('-', ' ').title()
        rarity = RARITY_MAP.get(int(rarity_num), "✨ Common")
        category = get_category(char_name)

        seq_num = await get_next_sequence_number('character_id')
        char_id = str(seq_num).zfill(3)

        caption = (
            f"🎥 *New Video Character Added!*\n\n"
            f"🆔 *ID:* {char_id}\n"
            f"🌟 *Name:* {char_name}\n"
            f"🎭 *Anime:* {anime_name}\n"
            f"🏆 *Rarity:* {rarity}\n"
            f"🔖 *Category:* {category}"
        )

        local_file = await download_to_tempfile(video_url)
        with open(local_file, "rb") as video:
            msg = await context.bot.send_video(chat_id=CHARA_CHANNEL_ID, video=video, caption=caption, parse_mode='Markdown')
        
        await collection.insert_one({
            'video_url': video_url, 'name': char_name, 'anime': anime_name,
            'rarity': rarity, 'id': char_id, 'category': category, 'message_id': msg.message_id
        })
        
        await status_msg.edit_text(f"✅ Character `{char_id}` Added Successfully!")
        os.remove(local_file)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# 2. EDIT VIDEO CHARACTER
async def edit_video(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        return
    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("Format: `/editvideo <ID> <field> <value>`\nFields: name, anime, rarity, video_url")
            return

        char_id, field, value = args[0], args[1].lower(), " ".join(args[2:])
        
        # Mapping img_url to video_url just in case
        if field == "img_url": field = "video_url"

        char = await collection.find_one({"id": char_id})
        if not char:
            await update.message.reply_text("❌ Character not found.")
            return

        status_msg = await update.message.reply_text(f"⚙️ *Updating {field}...*", parse_mode='Markdown')
        update_data = {}

        if field == "rarity":
            update_data["rarity"] = RARITY_MAP.get(int(value), char['rarity'])
        elif field == "video_url":
            local_file = await download_to_tempfile(value)
            try: await context.bot.delete_message(CHARA_CHANNEL_ID, char['message_id'])
            except: pass
            
            caption = (f"🎥 *Character Updated!*\n\n🆔 *ID:* {char['id']}\n🌟 *Name:* {char['name']}\n🎭 *Anime:* {char['anime']}\n🏆 *Rarity:* {char['rarity']}\n🔖 *Category:* {char['category']}")
            with open(local_file, "rb") as video:
                new_msg = await context.bot.send_video(chat_id=CHARA_CHANNEL_ID, video=video, caption=caption, parse_mode='Markdown')
            
            update_data["video_url"] = value
            update_data["message_id"] = new_msg.message_id
            os.remove(local_file)
        else:
            update_data[field] = value.replace('-', ' ').title()
            if field == "name":
                update_data["category"] = get_category(update_data[field])

        updated_char = await collection.find_one_and_update({"id": char_id}, {"$set": update_data}, return_document=ReturnDocument.AFTER)

        if field != "video_url":
            new_caption = (
                f"🎥 *Character Updated!*\n\n"
                f"🆔 *ID:* {updated_char['id']}\n"
                f"🌟 *Name:* {updated_char['name']}\n"
                f"🎭 *Anime:* {updated_char['anime']}\n"
                f"🏆 *Rarity:* {updated_char['rarity']}\n"
                f"🔖 *Category:* {updated_char['category']}"
            )
            await context.bot.edit_message_caption(chat_id=CHARA_CHANNEL_ID, message_id=updated_char['message_id'], caption=new_caption, parse_mode='Markdown')

        await status_msg.edit_text(f"✅ ID `{char_id}` updated successfully!")

    except Exception as e:
        await update.message.reply_text(f"❌ Edit Error: {str(e)}")

# 3. DELETE VIDEO CHARACTER
async def delete_video(update: Update, context: CallbackContext) -> None:
    if str(update.effective_user.id) not in sudo_users:
        return
    try:
        if not context.args:
            await update.message.reply_text("Usage: `/delvideo <ID>`")
            return

        char_id = context.args[0]
        char = await collection.find_one_and_delete({"id": char_id})

        if char:
            try: await context.bot.delete_message(chat_id=CHARA_CHANNEL_ID, message_id=char['message_id'])
            except: pass
            await update.message.reply_text(f"🗑️ Deleted `{char_id}` and removed from channel.")
        else:
            await update.message.reply_text("❌ Not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Delete Error: {str(e)}")

# Handlers
application.add_handler(CommandHandler("upvideo", upload_video))
application.add_handler(CommandHandler("editvideo", edit_video))
application.add_handler(CommandHandler("delvideo", delete_video))
