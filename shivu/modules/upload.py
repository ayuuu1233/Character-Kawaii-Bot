import asyncio
import logging
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, 
    InlineQueryResultArticle, InputTextMessageContent, 
    ReplyKeyboardMarkup, KeyboardButton
)
from pymongo import ReturnDocument
from shivu import user_collection, collection, CHARA_CHANNEL_ID, SUPPORT_CHAT, shivuu as app, sudo_users, db
from pyrogram.errors import BadRequest

# --- 1. LOGGING CONFIGURATION (Sabse Top Pe) ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler("bot_logs.txt", maxBytes=5000000, backupCount=2),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
GOOD_MORNING_TIME = "08:00"
GOOD_NIGHT_TIME = "22:00"
NEW_CHARACTER_TIME = "18:00"

SUDO_USER_IDS = [6402009857, 7004889403, 1135445089, 5158013355, 5630057244, 
                 1374057577, 6305653111, 5421067814, 7497950160, 7334126640, 
                 6835013483, 1993290981, 1742711103, 6180567980]
CHARA_CHANNEL_ID = -1002596866659

user_states = {}

rarity_emojis = {
    '⚪️ Common': '⚪️', '🔮 Limited Edition': '🔮', '🫧 Premium': '🫧',
    '🌸 Exotic': '🌸', '💮 Exclusive': '💮', '👶 Chibi': '👶',
    '🟡 Legendary': '🟡', '🟠 Rare': '🟠', '🔵 Medium': '🔵',
    '🎐 Astral': '🎐', '💞 Valentine': '💞'
}

event_emojis = {
    '🩺 Nurse': '🩺', '🐰 Bunny': '🐰', '🧹 Maid': '🧹', '🎃 Halloween': '🎃',
    '🎄 Christmas': '🎄', '🎩 Tuxedo': '🎩', '☃️ Winter': '☃️', '👘 Kimono': '👘',
    '🎒 School': '🎒', '🥻 Saree': '🥻', '🏖️ Summer': '🏖️', '🏀 Basketball': '🏀',
    '⚽ Soccer': '⚽'
}

# --- 2. ERROR LOGGER HELPER ---
async def log_error(e, context="General"):
    err_trace = traceback.format_exc()
    logger.error(f"Error in {context}: {str(e)}", exc_info=True)
    for uid in SUDO_USER_IDS:
        try:
            await app.send_message(
                uid, 
                f"❌ **LOG ALERT: {context}**\n\n**Error:** `{str(e)}`"
            )
        except: pass

# --- HELPERS ---
async def get_next_id():
    seq = await db.sequences.find_one_and_update(
        {'_id': 'character_id'}, {'$inc': {'sequence_value': 1}},
        upsert=True, return_document=ReturnDocument.AFTER
    )
    return str(seq['sequence_value']).zfill(2)

async def send_sudo_log(text):
    for uid in SUDO_USER_IDS:
        try: await app.send_message(uid, text)
        except: pass

# --- BACKGROUND TASK ---
async def scheduler():
    while True:
        now = datetime.now().strftime("%H:%M")
        if now == GOOD_MORNING_TIME:
            await send_sudo_log("Good morning! ☀️")
            await asyncio.sleep(61)
        elif now == GOOD_NIGHT_TIME:
            await send_sudo_log("Good night! 🌙")
            await asyncio.sleep(61)
        elif now == NEW_CHARACTER_TIME:
            try: await app.send_message(CHARA_CHANNEL_ID, "📢 New character coming soon!")
            except: pass
            await asyncio.sleep(61)
        await asyncio.sleep(30)

# --- START & ADMIN PANEL ---
@app.on_message(filters.command("start") & filters.private)
async def start_handler(_, msg):
    if msg.from_user.id in SUDO_USER_IDS:
        await msg.reply_text(f"Hello Admin!", reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("⚙ Admin panel ⚙")]], resize_keyboard=True
        ))

@app.on_message(filters.regex("^⚙ Admin panel ⚙$") & filters.private)
async def panel_handler(_, msg):
    if msg.from_user.id not in SUDO_USER_IDS: return
    total_w = await collection.count_documents({})
    total_a = len(await collection.distinct("anime"))
    total_h = await user_collection.count_documents({})
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Add Character", callback_data="add_waifu"),
         InlineKeyboardButton("Add Anime 🆕", callback_data="add_anime")],
        [InlineKeyboardButton("👾 Anime List", switch_inline_query_current_chat="choose_anime ")]
    ])
    await msg.reply_text(f"Admin Panel:\n\nTotal Waifus: {total_w}\nTotal Animes: {total_a}\nTotal Harems: {total_h}", reply_markup=kb)

# --- EDIT COMMAND ---
@app.on_message(filters.command("edit") & filters.private)
async def edit_waifu(_, msg):
    if msg.from_user.id not in SUDO_USER_IDS: return
    if len(msg.command) < 2: return await msg.reply("Usage: /edit <character_id>")
    
    char = await collection.find_one({"id": msg.command[1]})
    if not char: return await msg.reply("Character not found!")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧩 Rename", callback_data=f"edit_rename_{char['id']}")],
        [InlineKeyboardButton("⛱️ Change Image", callback_data=f"edit_image_{char['id']}")],
        [InlineKeyboardButton("⛩️ Change Rarity", callback_data=f"edit_rarity_{char['id']}")],
        [InlineKeyboardButton("🎉 Edit Event", callback_data=f"edit_event_{char['id']}")],
        [InlineKeyboardButton("📢 Reset", callback_data=f"edit_reset_{char['id']}")],
        [InlineKeyboardButton("🗑️ Remove", callback_data=f"edit_remove_{char['id']}")]
    ])
    await msg.reply_photo(char["img_url"], caption=f"ID: {char['id']}\nName: {char['name']}\nAnime: {char['anime']}\nRarity: {char['rarity']}", reply_markup=kb)

# --- CALLBACK ROUTER ---
@app.on_callback_query()
async def callback_router(_, cb):
    uid = cb.from_user.id
    data = cb.data

    # Add Anime
    if data == "add_anime":
        user_states[uid] = {"state": "wait_anime_name"}
        await cb.message.edit_text("Enter new Anime name:")

    # Add Waifu Start
    elif data == "add_waifu":
        await cb.message.edit_text("Search and select anime first:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👾 Search Anime", switch_inline_query_current_chat="choose_anime ")]
        ]))

    # Selection from Inline Search
    elif data.startswith("add_waifu_"):
        anime = data.split('_', 2)[-1]
        user_states[uid] = {"state": "wait_waifu_name", "anime": anime}
        await cb.message.edit_text(f"Anime: {anime}\nNow send Character Name:")

    # Edit Callbacks
    elif data.startswith("edit_"):
        parts = data.split('_')
        action, cid = parts[1], parts[2]
        
        if action == "rename":
            user_states[uid] = {"state": "renaming", "cid": cid}
            await cb.message.edit_text(f"Send new name for ID {cid}:")
        elif action == "image":
            user_states[uid] = {"state": "changing_img", "cid": cid}
            await cb.message.edit_text(f"Send new photo for ID {cid}:")
        elif action == "rarity":
            btns = [[InlineKeyboardButton(r, callback_data=f"set_rarity_{r}_{cid}")] for r in rarity_emojis.keys()]
            await cb.message.edit_text("Select new rarity:", reply_markup=InlineKeyboardMarkup(btns))
        elif action == "event":
            btns = [[InlineKeyboardButton(e, callback_data=f"set_event_{e}_{cid}")] for e in event_emojis.keys()]
            btns.append([InlineKeyboardButton("Skip", callback_data=f"set_event_none_{cid}")])
            await cb.message.edit_text("Select Event:", reply_markup=InlineKeyboardMarkup(btns))
        elif action == "reset":
            await collection.update_one({"id": cid}, {"$set": {"global_grabbed": 0}})
            await cb.answer("✅ Reset Done!", show_alert=True)
        elif action == "remove":
            await collection.delete_one({"id": cid})
            await cb.message.edit_text(f"✅ Character {cid} removed!")

    # Setting Rarity/Event during Add/Edit
    elif data.startswith("set_rarity_"):
        _, _, rar, cid = data.split('_')
        await collection.update_one({"id": cid}, {"$set": {"rarity": rar}})
        await cb.message.edit_text(f"✅ Rarity updated to {rar}")

    elif data.startswith("set_event_"):
        _, _, evt, cid = data.split('_')
        emoji = event_emojis.get(evt, "") if evt != "none" else ""
        await collection.update_one({"id": cid}, {"$set": {"event_name": evt if evt != "none" else "", "event_emoji": emoji}})
        await cb.message.edit_text(f"✅ Event updated to {evt}")

    # Add Waifu Rarity Choice
    elif data.startswith("choice_rarity_"):
        rar = data.split('_')[-1]
        user_states[uid].update({"rarity": rar, "state": "wait_event_choice"})
        btns = [[InlineKeyboardButton(e, callback_data=f"choice_event_{e}")] for e in event_emojis.keys()]
        btns.append([InlineKeyboardButton("Skip", callback_data="choice_event_none")])
        await cb.message.edit_text("Choose Event:", reply_markup=InlineKeyboardMarkup(btns))

    # Add Waifu Event Choice
    elif data.startswith("choice_event_"):
        evt = data.split('_')[-1]
        emoji = event_emojis.get(evt, "") if evt != "none" else ""
        user_states[uid].update({"event_name": evt if evt != "none" else "", "event_emoji": emoji, "state": "wait_photo"})
        await cb.message.edit_text(f"Event: {evt}\nNow send the Photo/Image:")

# --- TEXT HANDLER ---
@app.on_message(filters.private & filters.text & ~filters.command(["start", "edit"]))
async def text_processor(_, msg):
    uid = msg.from_user.id
    if uid not in user_states: return
    state = user_states[uid].get("state")
    text = msg.text.strip()

    if state == "wait_anime_name":
        await collection.insert_one({"anime": text}) # Custom anime logic if needed
        await msg.reply(f"✅ Anime '{text}' added!")
        user_states.pop(uid)

    elif state == "wait_waifu_name":
        user_states[uid].update({"name": text, "state": "wait_rarity_choice"})
        btns = [[InlineKeyboardButton(r, callback_data=f"choice_rarity_{r}")] for r in rarity_emojis.keys()]
        await msg.reply("Select Rarity:", reply_markup=InlineKeyboardMarkup(btns))

    elif state == "renaming":
        cid = user_states[uid]["cid"]
        await collection.update_one({"id": cid}, {"$set": {"name": text}})
        await msg.reply(f"✅ ID {cid} renamed to {text}")
        user_states.pop(uid)

# --- PHOTO HANDLER ---
@app.on_message(filters.private & filters.photo)
async def photo_processor(_, msg):
    uid = msg.from_user.id
    if uid not in user_states: return
    state = user_states[uid].get("state")

    if state == "wait_photo":
        data = user_states[uid]
        new_id = await get_next_id()
        char_data = {
            "id": new_id, "name": data["name"], "anime": data["anime"],
            "rarity": data["rarity"], "img_url": msg.photo.file_id,
            "event_name": data.get("event_name", ""), "event_emoji": data.get("event_emoji", ""),
            "global_grabbed": 0
        }
        await collection.insert_one(char_data)
        
        caption = f"✅ Character Added!\nID: {new_id}\nName: {data['name']}\nAnime: {data['anime']}\nRarity: {data['rarity']}"
        await msg.reply(caption)
        await app.send_photo(CHARA_CHANNEL_ID, msg.photo.file_id, caption=caption)
        user_states.pop(uid)

    elif state == "changing_img":
        cid = user_states[uid]["cid"]
        await collection.update_one({"id": cid}, {"$set": {"img_url": msg.photo.file_id}})
        await msg.reply(f"✅ Image updated for ID {cid}")
        user_states.pop(uid)

# --- LOGS RETRIEVAL COMMAND ---
@app.on_message(filters.command("getlogs") & filters.user(SUDO_USER_IDS))
async def get_logs_file(_, msg):
    try:
        await msg.reply_document("bot_logs.txt", caption="📄 Current Bot Logs")
    except Exception as e:
        await msg.reply(f"Error getting logs: {e}")

# --- MAIN RUNNER ---
async def start_bot():
    await app.start()
    asyncio.create_task(scheduler())
    await send_sudo_log("🚨 Bot Restarted & Ready!")
    print("Bot is running...")
    await asyncio.idle()

if __name__ == "__main__":
    app.run(start_bot())
 
