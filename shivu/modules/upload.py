import logging
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, 
    Message, InlineQueryResultArticle, InputTextMessageContent, 
    ReplyKeyboardMarkup, KeyboardButton
)
from pymongo import ReturnDocument
from shivu import user_collection, collection, CHARA_CHANNEL_ID, SUPPORT_CHAT, shivuu as app, sudo_users, db

# State Dictionary
user_states = {}

# Mappings
rarity_emojis = {
    '⚪️ Common': '⚪️', '🔮 Limited Edition': '🔮', '🫧 Premium': '🫧',
    '🌸 Exotic': '🌸', '💮 Exclusive': '💮', '👶 Chibi': '👶',
    '🟡 Legendary': '🟡', '🟠 Rare': '🟠', '🔵 Medium': '🔵',
    '🎐 Astral': '🎐', '💞 Valentine': '💞'
}

event_emojis = {
    '🩺 Nurse': '🩺', '🐰 Bunny': '🐰', '🧹 Maid': '🧹',
    '🎃 Halloween': '🎃', '🎄 Christmas': '🎄', '🎩 Tuxedo': '🎩',
    '☃️ Winter': '☃️', '👘 Kimono': '👘', '🎒 School': '🎒',
    '🥻 Saree': '🥻', '🏖️ Summer': '🏖️', '🏀 Basketball': '🏀', '⚽ Soccer': '⚽'
}

async def get_next_sequence_number(sequence_name):
    sequence_collection = db.sequences
    sequence_document = await sequence_collection.find_one_and_update(
        {'_id': sequence_name}, 
        {'$inc': {'sequence_value': 1}}, 
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return sequence_document['sequence_value']

# --- COMMANDS ---

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if str(message.from_user.id) in sudo_users:
        await message.reply_text(
            f"✨ **Kon'nichiwa Admin-sama!** ✨\n\nWelcome back to the sanctuary. Use the button below or type /upload to manage the database!",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("⚙ Admin panel ⚙")]],
                resize_keyboard=True
            )
        )

@app.on_message((filters.command("upload") | filters.regex("^⚙ Admin panel ⚙$")) & filters.private)
async def admin_panel_kawaii(client, message):
    if str(message.from_user.id) not in sudo_users:
        await message.reply_text("Gomen'nasai! This command is only for my Master. 🌸")
        return
    
    total_waifus = await collection.count_documents({})
    total_animes = len(await collection.distinct("anime"))
    total_harems = await user_collection.count_documents({})
    
    welcome_text = (
        "🌸 **Wᴇʟᴄᴏᴍᴇ ᴛᴏ Aɴɪᴍᴇ Pᴀɴᴇʟ Kᴀᴡᴀɪɪ** 🌸\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ *Hello Master! Everything is ready for you...*\n\n"
        f"📊 **Cᴜʀʀᴇɴᴛ Sᴛᴀᴛɪsᴛɪᴄs:**\n"
        f"  │\n"
        f"  ├─ 👧 **Tᴏᴛᴀʟ Wᴀɪғᴜs:** `{total_waifus}`\n"
        f"  ├─ 🎥 **Tᴏᴛᴀʟ Aɴɪᴍᴇs:** `{total_animes}`\n"
        f"  └─ 🏰 **Tᴏᴛᴀʟ Hᴀʀᴇᴍs:** `{total_harems}`\n\n"
        "**What would you like to do today?** 🐾"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Add Character", callback_data="add_waifu"),
         InlineKeyboardButton("Add Anime 🆕", callback_data="add_anime")],
        [InlineKeyboardButton("👾 Explore Anime List", switch_inline_query_current_chat="choose_anime ")]
    ])
    
    await message.reply_text(welcome_text, reply_markup=keyboard)

@app.on_message(filters.command("edit") & filters.private)
async def edit_waifu_command(client, message):
    if str(message.from_user.id) not in sudo_users:
        return
    if len(message.command) < 2:
        await message.reply_text("Usage: /edit <waifu_id>")
        return

    waifu_id = message.command[1]
    waifu = await collection.find_one({"id": waifu_id})
    if waifu:
        await message.reply_photo(
            photo=waifu["img_url"],
            caption=f"👧 Name: {waifu['name']}\n🎥 Anime: {waifu['anime']}\n🏷 Rarity: {waifu['rarity']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🧩 Rename Character", callback_data=f"rename_waifu_{waifu_id}")],
                [InlineKeyboardButton("⛱️ Change Image", callback_data=f"change_image_{waifu_id}")],
                [InlineKeyboardButton("⛩️ Change Rarity", callback_data=f"change_rarity_{waifu_id}")],
                [InlineKeyboardButton("🎉 Edit Event", callback_data=f"change_event_{waifu_id}")],
                [InlineKeyboardButton("🗑️ Remove Character", callback_data=f"remove_waifu_{waifu_id}")]
            ])
        )
    else:
        await message.reply_text("Character not found.")



# --- CALLBACK HANDLERS (CLEANED & FIXED) ---

@app.on_callback_query()
async def handle_callbacks(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    # 1. ADD ANIME
    if data == "add_anime":
        user_states[user_id] = {"state": "adding_anime"}
        await callback_query.message.edit_text("📝 **Master, naye Anime ka naam bhejiye:**")

    # 2. ADD WAIFU (SEARCH)
    elif data == "add_waifu":
        await callback_query.message.edit_text(
            "🔍 **Anime search karein jisme character add karna hai:**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 Search Anime", switch_inline_query_current_chat="choose_anime ")
            ]])
        )

    # 3. SELECT ANIME FROM INLINE
    elif data.startswith("add_waifu_"):
        anime_name = data.replace("add_waifu_", "")
        user_states[user_id] = {"state": "awaiting_waifu_name", "anime": anime_name}
        await callback_query.message.edit_text(f"🎬 **Anime:** `{anime_name}`\n\n✨ **Character ka naam bhejiye:**")

    # 4. SELECT RARITY (DURING ADD)
    elif data.startswith("select_rarity_"):
        rarity = data.replace("select_rarity_", "")
        if user_id in user_states:
            user_states[user_id].update({"rarity": rarity, "state": "awaiting_waifu_image"})
            await callback_query.message.edit_text(f"✨ **Rarity:** {rarity}\n\n🖼️ **Ab Character ki Photo bhejiye:**")

    # --- EDIT / REMOVE LOGIC ---

    elif data.startswith("remove_waifu_"):
        waifu_id = data.split("_")[-1]
        result = await collection.delete_one({"id": waifu_id})
        if result.deleted_count > 0:
            await callback_query.message.edit_text(f"🗑️ **Character (ID: {waifu_id}) database se delete kar diya gaya hai.**")
        else:
            await callback_query.answer("❌ Character nahi mila!", show_alert=True)

    elif data.startswith("change_rarity_"):
        waifu_id = data.split("_")[-1]
        btns = [[InlineKeyboardButton(r, callback_data=f"set_rarity_{r}_{waifu_id}")] for r in rarity_emojis.keys()]
        await callback_query.message.edit_text("✨ **New Rarity select karein:**", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith("set_rarity_"):
        # Format: set_rarity_RARITYNAME_ID
        parts = data.split("_")
        waifu_id = parts[-1]
        new_rarity = parts[2] # Adjusting index based on split
        await collection.update_one({"id": waifu_id}, {"$set": {"rarity": new_rarity}})
        await callback_query.message.edit_text(f"✅ **Rarity updated to:** {new_rarity}")

# --- MESSAGE HANDLERS (FIXED FLOW) ---

@app.on_message(filters.private & (filters.text | filters.photo))
async def handle_inputs(client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_states: return
    
    state_data = user_states[user_id]
    current_state = state_data.get("state")

    # Adding New Anime
    if current_state == "adding_anime" and message.text:
        await collection.insert_one({"anime": message.text.strip(), "is_anime_only": True})
        await message.reply_text(f"✅ **Anime Added:** {message.text}")
        user_states.pop(user_id)

    # Renaming Existing Waifu
    elif current_state == "renaming_waifu" and message.text:
        await collection.update_one({"id": state_data["waifu_id"]}, {"$set": {"name": message.text.strip()}})
        await message.reply_text(f"✅ **Name Updated:** {message.text}")
        user_states.pop(user_id)

    # Awaiting Name for New Waifu
    elif current_state == "awaiting_waifu_name" and message.text:
        user_states[user_id].update({"name": message.text.strip(), "state": "selecting_rarity_state"})
        btns = [[InlineKeyboardButton(r, callback_data=f"select_rarity_{r}")] for r in rarity_emojis.keys()]
        await message.reply_text("✨ **Rarity select karein:**", reply_markup=InlineKeyboardMarkup(btns))

    # Awaiting Photo for New Waifu
    elif current_state == "awaiting_waifu_image" and message.photo:
        waifu_id = str(await get_next_sequence_number('character_id')).zfill(2)
        char = {
            "id": waifu_id, 
            "name": state_data["name"], 
            "anime": state_data["anime"],
            "rarity": state_data["rarity"], 
            "img_url": message.photo.file_id,
            "event_emoji": state_data.get("event_emoji", ""), 
            "event_name": state_data.get("event_name", "")
        }
        await collection.insert_one(char)
        await message.reply_photo(
            photo=message.photo.file_id,
            caption=f"✅ **Character Added Successfully!**\n\n🆔 ID: `{waifu_id}`\n👧 Name: {state_data['name']}\n🎬 Anime: {state_data['anime']}"
        )
        user_states.pop(user_id)

# --- INLINE QUERY ---
@app.on_inline_query()
async def inline_search(client, query):
    term = query.query.replace("choose_anime ", "").strip()
    animes = await collection.aggregate([
        {"$match": {"anime": {"$regex": term, "$options": "i"}}},
        {"$group": {"_id": "$anime", "count": {"$sum": 1}}},
        {"$limit": 10}
    ]).to_list(10)
    
    results = [InlineQueryResultArticle(
        title=a["_id"], description=f"Chars: {a['count']}",
        input_message_content=InputTextMessageContent(f"Anime: {a['_id']}"),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Character", callback_data=f"add_waifu_{a['_id']}")]])) 
    for a in animes]
    await query.answer(results, cache_time=1)

if __name__ == "__main__":
    app.run()
