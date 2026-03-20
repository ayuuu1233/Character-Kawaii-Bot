import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineQueryResultPhoto
)

from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    InlineQueryHandler,
    filters
)

from pymongo import ReturnDocument
from shivu import application, collection, user_collection, sudo_users, CHARA_CHANNEL_ID, SUPPORT_CHAT
# ------------------ LOGGING ------------------ #
logging.basicConfig(level=logging.INFO)

# ------------------ GLOBAL STATE ------------------ #
user_states = {}

# ------------------ COUNTER FUNCTION ------------------ #
def get_next_sequence_number(name):
    counter = collection.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return counter["seq"]

# ------------------ EMOJIS ------------------ #
rarity_emojis = {
        '⚪️ Common': '⚪️',
        '🔮 Limited Edition': '🔮',
        '🫧 Premium': '🫧',
        '🌸 Exotic': '🌸',
        '💮 Exclusive': '💮',
        '👶 Chibi': '👶',
        '🟡 Legendary': '🟡',
        '🟠 Rare': '🟠',
        '🔵 Medium': '🔵',
        '🎐 Astral': '🎐',
        '💞 Valentine': '💞'
}

event_emojis = {
    "none": "Normal",
    '🩺 Nurse': '🩺',
    '🐰 Bunny': '🐰',
    '🧹 Maid': '🧹',
    '🎃 Halloween': '🎃',
    '🎄 Christmas': '🎄',
    '🎩 Tuxedo': '🎩',
    '☃️ Winter': '☃️',
    '👘 Kimono': '👘',
    '🎒 School': '🎒',
    '🥻 Saree': '🥻',
    '🏖️ Summer': '🏖️',
    '🏀 Basketball': '🏀',
    '⚽ Soccer': '⚽'
}

# ------------------ START ------------------ #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in sudo_users:
        return

    keyboard = [
        [InlineKeyboardButton("⚙ Admin Panel ⚙", callback_data="admin_panel")]
    ]
    await update.message.reply_text(
        "Welcome Admin 👑",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ------------------ UPLOAD PANEL ------------------ #
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name

    if user_id not in sudo_users:
        await update.message.reply_text("❌ Access Denied — This realm is not for you...")
        return

    text = f"""
╭━━━〔 🌸 WAIFU REALM 🌸 〕━━━╮

✨ Welcome, {name}-senpai 💖  
You have unlocked the Creator Panel...

🎴 “Create. Customize. Dominate.”

💫 Select your action below:

╰━━━〔 💎 MAKE IT LEGENDARY 💎 〕━━━╯
"""

    keyboard = [
        [
            InlineKeyboardButton("🌸 CREATE WAIFU", callback_data="add_waifu"),
            InlineKeyboardButton("🎴 ANIME ZONE", callback_data="anime_list")
        ],
        [
            InlineKeyboardButton("⚙ ADMIN PANEL", callback_data="admin_panel")
        ],
        [
            InlineKeyboardButton("❌ CLOSE", callback_data="close_panel")
        ]
    ]

    await  update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )      

# ------------------ ADMIN PANEL ------------------ #
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
await query.answer()

    total_waifus = collection.count_documents({"type": "waifu"})
    total_anime = collection.distinct("anime")
    total_harem = user_collection.count_documents({})

    text = f"""
📊 Stats:
Waifus: {total_waifus}
Animes: {len(total_anime)}
Users: {total_harem}
"""

    keyboard = [
        [InlineKeyboardButton("➕ Add Character", callback_data="add_waifu")],
        [InlineKeyboardButton("📺 Anime List", callback_data="anime_list")]
    ]

  await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ------------------ ADD WAIFU FLOW ------------------ #
async def add_waifu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
await query.answer()

    user_states[query.from_user.id] = {"step": "search_anime"}

 await query.edit_message_text("🔍 Send anime name to search...")

# ------------------ TEXT HANDLER ------------------ #
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_states:
        return

    state = user_states[user_id]

    # STEP 1: ANIME
    if state["step"] == "search_anime":
        anime = update.message.text
        state["anime"] = anime
        state["step"] = "name"

   await update.message.reply_text("✏ Send character name")

    # STEP 2: NAME
    elif state["step"] == "name":
        state["name"] = update.message.text
        state["step"] = "rarity"

        keyboard = [
            [InlineKeyboardButton(v, callback_data=f"rarity_{k}")]
            for k, v in rarity_emojis.items()
        ]

   await update.message.reply_text(
            "Select Rarity:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ------------------ RARITY ------------------ #
async def select_rarity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    rarity = query.data.split("_")[1]
    user_states[user_id]["rarity"] = rarity
    user_states[user_id]["step"] = "event"

    keyboard = [
        [InlineKeyboardButton(v, callback_data=f"event_{k}")]
        for k, v in event_emojis.items()
    ]

 await query.edit_message_text(
        "Select Event:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ------------------ EVENT ------------------ #
async def select_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    event = query.data.split("_")[1]
    user_states[user_id]["event"] = event
    user_states[user_id]["step"] = "photo"

await query.edit_message_text("📸 Send character photo")

# ------------------ PHOTO ------------------ #
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_states:
        return

    state = user_states[user_id]

    if state["step"] != "photo":
        return

    photo = update.message.photo[-1].file_id

    waifu_id = get_next_sequence_number("waifu_id")

    data = {
        "type": "waifu",
        "id": waifu_id,
        "name": state["name"],
        "anime": state["anime"],
        "rarity": state["rarity"],
        "event": state["event"],
        "img": photo
    }

    collection.insert_one(data)

 await update.message.reply_text(
        f"✅ Character Added!\nID: {waifu_id}\n{state['name']}"
    )

    del user_states[user_id]

# ------------------ EDIT ------------------ #
async def edit_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in sudo_users:
        return

    try:
        waifu_id = int(context.args[0])
    except:
    await update.message.reply_text("Usage: /edit <id>")
        return

    waifu = collection.find_one({"id": waifu_id})

    if not waifu:
    await update.message.reply_text("Not Found")
        return

    keyboard = [
        [InlineKeyboardButton("Rename", callback_data=f"rename_{waifu_id}")],
        [InlineKeyboardButton("Change Image", callback_data=f"img_{waifu_id}")],
        [InlineKeyboardButton("Change Rarity", callback_data=f"rarityedit_{waifu_id}")],
        [InlineKeyboardButton("Change Event", callback_data=f"eventedit_{waifu_id}")]
    ]

 await update.message.reply_photo(
        waifu["img"],
        caption=f"{waifu['name']} ({waifu['anime']})",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ------------------ RESET ------------------ #
async def reset_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    waifu_id = int(query.data.split("_")[1])

    collection.update_one({"id": waifu_id}, {"$set": {"grabbed": 0}})
    user_collection.update_many({}, {"$pull": {"harem": waifu_id}})

 await query.answer("Reset Done ✅")

# ------------------ REMOVE ------------------ #
async def remove_waifu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    waifu_id = int(query.data.split("_")[1])

    collection.delete_one({"id": waifu_id})

 await query.edit_message_text("❌ Deleted")

# ------------------ INLINE SEARCH ------------------ #
async def search_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query

    results = []
    animes = collection.distinct("anime")

    for anime in animes:
        if query.lower() in anime.lower():
            count = collection.count_documents({"anime": anime})
            results.append(
                InlineQueryResultArticle(
                    id=anime,
                    title=anime,
                    description=f"{count} characters",
                    input_message_content=InputTextMessageContent(anime)
                )
            )

 await update.inline_query.answer(results[:20])

async def close_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
  await query.answer()

  await query.edit_message_text("✨ Panel closed... Come back anytime Senpai 💖")

# ------------------ MAIN ------------------ #
def main():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("upload", upload_command))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="admin_panel"))
    application.add_handler(CallbackQueryHandler(add_waifu_callback, pattern="add_waifu"))
    application.add_handler(CallbackQueryHandler(select_rarity, pattern="rarity_"))
    application.add_handler(CallbackQueryHandler(select_event, pattern="event_"))
    application.add_handler(CallbackQueryHandler(close_panel, pattern="close_panel"))

    application.add_handler(CommandHandler("edit", edit_waifu))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))
    application.add_handler(MessageHandler(filters.PHOTO, receive_photo))

    application.add_handler(InlineQueryHandler(search_anime))

    application.run_polling()

if __name__ == "__main__":
    main()
