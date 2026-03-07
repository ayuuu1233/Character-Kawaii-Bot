from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shivu import user_collection, collection, shivuu as app
import random
import math

user_data = {}

RARITIES = [
    "⚪️ Common",
    "🔮 Limited Edition",
    "🫧 Premium",
    "🌸 Exotic",
    "💮 Exclusive",
    "👶 Chibi",
    "🟡 Legendary",
    "🟠 Rare",
    "🔵 Medium",
    "🎐 Astral",
    "💞 Valentine"
]

AI_PRIORITY = [
    "🟡 Legendary",
    "💮 Exclusive",
    "🫧 Premium",
    "🌸 Exotic",
    "🟠 Rare",
    "🔮 Limited Edition",
    "🔵 Medium",
    "⚪️ Common"
]


# ---------------- MAIN MENU ---------------- #

async def hmode(client, message):

    user_id = message.from_user.id
    user_data[user_id] = True

    img = "https://files.catbox.moe/0yr8f9.jpg"

    keyboard = [
        [InlineKeyboardButton("🧠 Auto Sort (AI)", callback_data="ai_sort")],
        [InlineKeyboardButton("🧩 Sort by Rarity", callback_data="sort_rarity")],
        [InlineKeyboardButton("🎲 Random Rarity Mode", callback_data="random_rarity")],
        [InlineKeyboardButton("🎴 Filter Characters", callback_data="filter_menu")],
        [InlineKeyboardButton("💎 Harem Stats", callback_data="harem_stats")],
        [InlineKeyboardButton("🎏 Reset Preferences", callback_data="reset_preferences")],
        [InlineKeyboardButton("🧧 Close", callback_data="close")]
    ]

    await message.reply_photo(
        img,
        caption="🌸 **Harem Interface Settings** 🌸",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- CALLBACK ---------------- #

@app.on_callback_query(filters.regex("^(ai_sort|sort_rarity|random_rarity|filter_menu|harem_stats|reset_preferences|close)"))
async def hmode_callback(client, callback_query: CallbackQuery):

    user_id = callback_query.from_user.id

    if user_id not in user_data:
        await callback_query.answer("Session expired. Use /hmode again.", show_alert=True)
        return

    data = callback_query.data

    if data == "close":
        await callback_query.message.delete()

    elif data == "sort_rarity":
        await send_rarity_preferences(callback_query)

    elif data == "random_rarity":

        rarity = random.choice(RARITIES)

        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"rarity_preference": rarity}},
            upsert=True
        )

        await callback_query.message.edit_text(f"🎲 Random rarity selected:\n\n{rarity}")

    elif data == "ai_sort":

        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"rarity_preference": "AI"}},
            upsert=True
        )

        await callback_query.message.edit_text(
            "🧠 **AI Sorting Enabled**\n\nBest characters will appear first."
        )

    elif data == "filter_menu":

        keyboard = [
            [InlineKeyboardButton(r, callback_data=f"filter_{r}_0")]
            for r in RARITIES
        ]

        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_hmode")])

        await callback_query.message.edit_text(
            "🎴 Select rarity to filter",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "harem_stats":

        user = await user_collection.find_one({"id": user_id})

        characters = user.get("characters", [])

        total = len(characters)
        unique = len(set([c["name"] for c in characters])) if characters else 0

        rarity_count = {}

        for c in characters:
            r = c.get("rarity", "Unknown")
            rarity_count[r] = rarity_count.get(r, 0) + 1

        text = f"💎 **Harem Stats**\n\n"
        text += f"Total Characters: {total}\n"
        text += f"Unique Characters: {unique}\n\n"

        for r, count in rarity_count.items():
            text += f"{r} : {count}\n"

        await callback_query.message.edit_text(text)

    elif data == "reset_preferences":

        await user_collection.update_one(
            {"id": user_id},
            {"$unset": {"rarity_preference": ""}}
        )

        await callback_query.message.edit_text(
            "✅ Preferences reset successfully."
        )


# ---------------- RARITY MENU ---------------- #

async def send_rarity_preferences(callback_query):

    keyboard = [
        [InlineKeyboardButton(r, callback_data=f"rarity_{r}")]
        for r in RARITIES
    ]

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_hmode")])

    await callback_query.message.edit_text(
        "🎴 Choose rarity",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- SET RARITY ---------------- #

@app.on_callback_query(filters.regex("^rarity_"))
async def rarity_callback(client, callback_query):

    user_id = callback_query.from_user.id
    rarity = callback_query.data.replace("rarity_", "")

    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"rarity_preference": rarity}},
        upsert=True
    )

    await callback_query.message.edit_text(
        f"✨ Preference set:\n\n{rarity}"
    )


# ---------------- FILTER PAGINATION ---------------- #

@app.on_callback_query(filters.regex("^filter_"))
async def filter_characters(client, callback_query):

    user_id = callback_query.from_user.id

    data = callback_query.data.split("_")

    rarity = data[1]
    page = int(data[2])

    user = await user_collection.find_one({"id": user_id})

    characters = [c for c in user.get("characters", []) if c["rarity"] == rarity]

    per_page = 5
    total_pages = max(1, math.ceil(len(characters) / per_page))

    start = page * per_page
    end = start + per_page

    chars = characters[start:end]

    text = f"🎴 {rarity} Characters\n\n"

    for c in chars:
        text += f"• {c['name']}\n"

    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton("⬅ Prev", callback_data=f"filter_{rarity}_{page-1}")
        )

    if page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton("➡ Next", callback_data=f"filter_{rarity}_{page+1}")
        )

    keyboard = [buttons] if buttons else []

    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="filter_menu")])

    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- BACK ---------------- #

@app.on_callback_query(filters.regex("^back_hmode$"))
async def back_hmode(client, callback_query):

    keyboard = [
        [InlineKeyboardButton("🧠 Auto Sort (AI)", callback_data="ai_sort")],
        [InlineKeyboardButton("🧩 Sort by Rarity", callback_data="sort_rarity")],
        [InlineKeyboardButton("🎲 Random Rarity Mode", callback_data="random_rarity")],
        [InlineKeyboardButton("🎴 Filter Characters", callback_data="filter_menu")],
        [InlineKeyboardButton("💎 Harem Stats", callback_data="harem_stats")],
        [InlineKeyboardButton("🎏 Reset Preferences", callback_data="reset_preferences")],
        [InlineKeyboardButton("🧧 Close", callback_data="close")]
    ]

    await callback_query.message.edit_text(
        "🌸 **Harem Interface Settings** 🌸",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- COMMAND ---------------- #

@app.on_message(filters.command("hmode"))
async def hmode_command(client, message):
    await hmode(client, message)
