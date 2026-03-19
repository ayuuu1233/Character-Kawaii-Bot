import logging
import asyncio
import random
from datetime import datetime, time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message, InlineQueryResultArticle, InputTextMessageContent, InlineQueryResultPhoto, ReplyKeyboardMarkup, KeyboardButton
from pymongo import ReturnDocument
from shivu import user_collection, collection, CHARA_CHANNEL_ID, SUPPORT_CHAT, shivuu as app, sudo_users, db
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.errors import BadRequest



# --- Configuration & Emojis ---
RARITY_EMOJIS = {
    '⚪️ Common': '⚪️', '🔮 Limited Edition': '🔮', '🫧 Premium': '🫧',
    '🌸 Exotic': '🌸', '💮 Exclusive': '💮', '👶 Chibi': '👶',
    '🟡 Legendary': '🟡', '🟠 Rare': '🟠', '🔵 Medium': '🔵',
    '🎐 Astral': '🎐', '💞 Valentine': '💞'
}

EVENT_EMOJIS = {
    '🩺 Nurse': '🩺', '🐰 Bunny': '🐰', '🧹 Maid': '🧹', '🎃 Halloween': '🎃',
    '🎄 Christmas': '🎄', '🎩 Tuxedo': '🎩', '☃️ Winter': '☃️', '👘 Kimono': '👘',
    '🎒 School': '🎒', '🥻 Saree': '🥻', '🏖️ Summer': '🏖️', '🏀 Basketball': '🏀'
}

user_states = {}

# --- Helper: ID Generator ---
async def get_next_id():
    seq = await db.sequences.find_one_and_update(
        {'_id': 'character_id'}, {'$inc': {'sequence_value': 1}},
        upsert=True, return_document=ReturnDocument.AFTER
    )
    return str(seq['sequence_value']).zfill(2)

# --- ⚙️ ADMIN PANEL & START ---
@app.on_message(filters.command("start") & filters.private)
async def start(_, message):
    if str(message.from_user.id) in sudo_users:
        await message.reply_text(
            f"✨ **Welcome back, Boss!**",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("⚙ Admin panel ⚙")]], resize_keyboard=True)
        )

@app.on_message(filters.regex("^⚙ Admin panel ⚙$") & filters.private)
async def admin_panel(_, message):
    if str(message.from_user.id) not in sudo_users: return
    counts = {"waifus": await collection.count_documents({}), "animes": len(await collection.distinct("anime"))}
    
    text = f"🎀 **Admin Panel** 🎀\n\n🎎 Waifus: `{counts['waifus']}`\n⛩️ Animes: `{counts['animes']}`"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Add Character", callback_data="add_waifu"),
         InlineKeyboardButton("Add Anime 🆕", callback_data="add_anime")],
        [InlineKeyboardButton("👾 Search Anime List", switch_inline_query_current_chat="choose_anime ")]
    ])
    await message.reply_text(text, reply_markup=kb)

# --- 🛠️ EDIT CHARACTER COMMAND ---
@app.on_message(filters.command("edit") & filters.private)
async def edit_waifu_cmd(_, message):
    if str(message.from_user.id) not in sudo_users: return
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/edit (id)`")

    waifu_id = message.command[1]
    waifu = await collection.find_one({"id": waifu_id})
    if not waifu: return await message.reply_text("Character not found.")

    caption = (f"📝 **Editing:** {waifu['name']}\n"
               f"🆔 ID: `{waifu_id}`\n"
               f"⛩️ Anime: {waifu['anime']}\n"
               f"🏷️ Rarity: {waifu['rarity']}")
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧩 Rename", callback_data=f"edit_name_{waifu_id}"),
         InlineKeyboardButton("🖼️ New Image", callback_data=f"edit_img_{waifu_id}")],
        [InlineKeyboardButton("⛩️ Change Rarity", callback_data=f"edit_rarity_{waifu_id}"),
         InlineKeyboardButton("🎉 Edit Event", callback_data=f"edit_event_{waifu_id}")],
        [InlineKeyboardButton("🔄 Reset Grabbed", callback_data=f"confirm_reset_{waifu_id}"),
         InlineKeyboardButton("🗑️ Remove", callback_data=f"confirm_del_{waifu_id}")]
    ])
    await message.reply_photo(photo=waifu["img_url"], caption=caption, reply_markup=kb)

# --- 🏗️ ADD CHARACTER FLOW ---
@app.on_callback_query(filters.regex('^add_waifu$'))
async def init_add(_, query):
    await query.message.edit_text("✨ **Step 1:** Use Search to pick an Anime:", 
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Search", switch_inline_query_current_chat="choose_anime ")]]))

@app.on_callback_query(filters.regex('^add_waifu_'))
async def set_anime(_, query):
    anime = query.data.replace("add_waifu_", "")
    user_states[query.from_user.id] = {"state": "ADD_NAME", "anime": anime}
    await app.send_message(query.from_user.id, f"✅ Anime: `{anime}`\n\nEnter Character Name:")
    await query.answer()

# --- ⌨️ UNIFIED TEXT HANDLER (CRITICAL FIX) ---
@app.on_message(filters.private & filters.text & ~filters.command(["start", "edit"]))
async def handle_text(_, message):
    user_id = message.from_user.id
    if user_id not in user_states: return
    
    state_data = user_states[user_id]
    state = state_data.get("state")
    text = message.text.strip()

    if state == "ADD_NAME":
        user_states[user_id].update({"state": "ADD_RARITY", "name": text})
        kb = [[InlineKeyboardButton(r, callback_data=f"sel_rarity_{r}")] for r in RARITY_EMOJIS.keys()]
        await message.reply_text("Select Rarity:", reply_markup=InlineKeyboardMarkup(kb))

    elif state == "add_anime":
        if await collection.find_one({"anime": text}):
            await message.reply_text("Already exists!")
        else:
            await collection.insert_one({"anime": text})
            await message.reply_text(f"✅ Added {text}!")
        user_states.pop(user_id, None)

    elif state == "RENAMING_WAIFU":
        await collection.update_one({"id": state_data["id"]}, {"$set": {"name": text}})
        await message.reply_text("✅ Name Updated!")
        user_states.pop(user_id, None)

# --- 🎭 RARITY & EVENT LOGIC ---
@app.on_callback_query(filters.regex('^sel_rarity_'))
async def sel_rarity(_, query):
    rarity = query.data.replace("sel_rarity_", "")
    user_states[query.from_user.id].update({"state": "ADD_EVENT", "rarity": rarity})
    kb = [[InlineKeyboardButton(e, callback_data=f"sel_event_{e}")] for e in EVENT_EMOJIS.keys()]
    kb.append([InlineKeyboardButton("⏩ Skip", callback_data="sel_event_none")])
    await query.message.edit_text(f"Rarity: `{rarity}`\nSelect Event:", reply_markup=InlineKeyboardMarkup(kb))

@app.on_callback_query(filters.regex('^sel_event_'))
async def sel_event(_, query):
    event_raw = query.data.replace("sel_event_", "")
    user_states[query.from_user.id].update({
        "state": "ADD_IMG", 
        "event_name": "" if event_raw == "none" else event_raw,
        "event_emoji": EVENT_EMOJIS.get(event_raw, "")
    })
    await query.message.edit_text("🖼️ Send the Character Image now.")

# --- 🖼️ PHOTO HANDLER ---
@app.on_message(filters.private & filters.photo)
async def handle_photo(_, message):
    user_id = message.from_user.id
    if user_id not in user_states: return
    data = user_states[user_id]

    if data.get("state") == "ADD_IMG":
        new_id = await get_next_id()
        char = {"id": new_id, "name": data["name"], "anime": data["anime"], 
                "rarity": data["rarity"], "img_url": message.photo.file_id,
                "event_emoji": data["event_emoji"], "event_name": data["event_name"]}
        await collection.insert_one(char)
        await message.reply_text(f"✅ Character Added! ID: `{new_id}`")
        user_states.pop(user_id, None)

    elif data.get("state") == "EDIT_IMG":
        await collection.update_one({"id": data["id"]}, {"$set": {"img_url": message.photo.file_id}})
        await message.reply_text("✅ Image Updated!")
        user_states.pop(user_id, None)

# --- 🗑️ DELETE & RESET LOGIC ---
@app.on_callback_query(filters.regex('^confirm_del_'))
async def delete_waifu(_, query):
    waifu_id = query.data.replace("confirm_del_", "")
    await collection.delete_one({"id": waifu_id})
    await query.message.edit_text(f"🗑️ ID `{waifu_id}` has been deleted.")

@app.on_callback_query(filters.regex('^confirm_reset_'))
async def reset_grabbed(_, query):
    waifu_id = query.data.replace("confirm_reset_", "")
    await collection.update_one({"id": waifu_id}, {"$set": {"global_grabbed": 0}})
    await query.message.edit_text(f"🔄 Reset successful for ID `{waifu_id}`.")

# --- 👾 INLINE SEARCH ---
@app.on_inline_query()
async def search_anime(_, inline_query):
    if str(inline_query.from_user.id) not in sudo_users: return
    query = inline_query.query.replace("choose_anime ", "").strip().lower()
    
    results = await collection.aggregate([
        {"$match": {"anime": {"$regex": query, "$options": "i"}}},
        {"$group": {"_id": "$anime", "count": {"$sum": 1}}},
        {"$limit": 10}
    ]).to_list(10)
    
    articles = [InlineQueryResultArticle(
        title=a["_id"], description=f"Characters: {a['count']}",
        input_message_content=InputTextMessageContent(f"⛩️ Anime: {a['_id']}"),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Select", callback_data=f"add_waifu_{a['_id']}")]])
    ) for a in results]
    await inline_query.answer(articles, cache_time=1)

if __name__ == "__main__":
    app.run()
