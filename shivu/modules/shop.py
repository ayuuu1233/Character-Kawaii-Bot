from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, InputMediaPhoto
from motor.motor_asyncio import AsyncIOMotorClient
from shivu import shivuu as app
import random
import asyncio

# ---------------- CONFIG ---------------- #
CHARACTERS_PER_PAGE = 3
REFRESH_COST = 100

# MongoDB setup
mongo = AsyncIOMotorClient("mongodb://Ayuu123_db_user:kawaiiibot124@ac-rbf2miz-shard-00-00.jqv8tga.mongodb.net:27017,ac-rbf2miz-shard-00-01.jqv8tga.mongodb.net:27017,ac-rbf2miz-shard-00-02.jqv8tga.mongodb.net:27017/?ssl=true&replicaSet=atlas-5dvxad-shard-0&authSource=admin&appName=Cluster0")
db = mongo['mydb']
user_collection = db['users']
collection = db['characters']

# In-memory session storage for pagination
shop_sessions = {}  # user_id: {'characters': [...], 'page': 0}

# ---------------- HELPERS ---------------- #

async def get_random_characters(filter_query=None):
    try:
        pipeline = []
        if filter_query:
            pipeline.append({'$match': filter_query})
        pipeline.append({'$sample': {'size': CHARACTERS_PER_PAGE}})
        cursor = collection.aggregate(pipeline)
        characters = await cursor.to_list(length=None)
        return characters if characters else []
    except Exception as e:
        print(f"[ERROR get_random_characters]: {e}")
        return []

def generate_character_price(action_type):
    return 5000 if action_type == "sell" else 30000

async def generate_character_message(user_id, action_type):
    session = shop_sessions.get(user_id)
    if not session or not session['characters']:
        return None, None, None

    characters = session['characters']
    page = session['page']
    if page >= len(characters):
        return f"No characters available.", [], []

    current_char = characters[page]
    price = generate_character_price(action_type)
    user_mention = f"<a href='tg://user?id={user_id}'>User</a>"

    text = (
        f"╭──\n"
        f"| ➩ 🥂 ɴᴀᴍᴇ: {current_char['name']}\n"
        f"| ➩ ✨ ɪᴅ: {current_char['id']}\n"
        f"| ➩ ⛩️ ᴀɴɪᴍᴇ: {current_char['anime']}\n"
        f"▰▱▱▱▱▱▱▱▱▱▰\n"
        f"| 🍃 ᴘʀɪᴄᴇ: {price} ᴛᴏᴋᴇɴs\n"
        f"Requested by: {user_mention}"
    )

    media = [InputMediaPhoto(media=current_char['img_url'], caption=text)]

    # Buttons
    buttons = [[InlineKeyboardButton(
        "sᴇʟʟ 🛒" if action_type == "sell" else "Buy 🛒",
        callback_data=f"{action_type}_char_{current_char['id']}_{price}"
    )]]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ ᴘʀᴇᴠ", callback_data=f"{action_type}_prev"))
    if page < len(characters) - 1:
        nav_buttons.append(InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"{action_type}_next"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(f"ʀᴇғʀᴇsʜ 🔄 ({REFRESH_COST} ᴛᴏᴋᴇɴs)", callback_data=f"{action_type}_refresh")])

    return text, media, buttons

# ---------------- COMMANDS ---------------- #

@app.on_message(filters.command("cshop"))
async def shop(_, message: Message):
    user_id = message.from_user.id
    user_mention = f"<a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>"

    characters = await get_random_characters()
    if not characters:
        return await message.reply_text(f"{user_mention}, no characters available for purchase.")

    shop_sessions[user_id] = {'characters': characters, 'page': 0}

    text, media, buttons = await generate_character_message(user_id, "buy")
    await message.reply_photo(photo=media[0].media, caption=text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="html")

@app.on_message(filters.command("sell"))
async def sell(_, message: Message):
    user_id = message.from_user.id
    user = await user_collection.find_one({'id': user_id})
    user_mention = f"<a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>"

    if not user or 'characters' not in user or not user['characters']:
        return await message.reply_text(f"{user_mention}, you don't have any characters available for sale.")

    characters = random.sample(user['characters'], min(CHARACTERS_PER_PAGE, len(user['characters'])))
    shop_sessions[user_id] = {'characters': characters, 'page': 0}

    text, media, buttons = await generate_character_message(user_id, "sell")
    await message.reply_photo(photo=media[0].media, caption=text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="html")

# ---------------- CALLBACK HANDLER ---------------- #

@app.on_callback_query()
async def callback_query_handler(_, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data.split(":")

    action_type = data[0]
    action = data[1] if len(data) > 1 else None

    user = await user_collection.find_one({'id': user_id}) or {}
    tokens = user.get('tokens', 0)

    # Pagination
    if action in ["next", "prev"]:
        session = shop_sessions.get(user_id)
        if not session:
            await query.answer("Session expired. Please open shop again.", show_alert=True)
            return

        session['page'] += 1 if action == "next" else -1
        session['page'] = max(0, min(session['page'], len(session['characters']) - 1))

        text, media, buttons = await generate_character_message(user_id, action_type)
        await query.message.edit_media(media=media[0])
        await query.message.edit_caption(caption=text, reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer()

    # Refresh
    elif action == "refresh":
        if tokens < REFRESH_COST:
            await query.answer("Insufficient tokens for refresh.", show_alert=True)
            return

        await user_collection.update_one({'id': user_id}, {'$inc': {'tokens': -REFRESH_COST}})
        characters = await get_random_characters() if action_type == "buy" else user.get('characters', [])
        shop_sessions[user_id] = {'characters': characters, 'page': 0}

        text, media, buttons = await generate_character_message(user_id, action_type)
        await query.message.edit_media(media=media[0])
        await query.message.edit_caption(caption=text, reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer("Characters refreshed!")

    # Buy / Sell
    elif action == "char":
        character_id, price = data[2], int(data[3])
        if action_type == "buy":
            if tokens < price:
                await query.answer("Insufficient tokens to buy this character.", show_alert=True)
                return

            await user_collection.update_one(
                {'id': user_id},
                {'$inc': {'tokens': -price}, '$push': {'characters': {'id': character_id}}},
                upsert=True
            )
            await query.answer("Character purchased successfully!", show_alert=True)
        elif action_type == "sell":
            if any(char['id'] == character_id for char in user.get('characters', [])):
                await user_collection.update_one(
                    {'id': user_id},
                    {'$inc': {'tokens': price}, '$pull': {'characters': {'id': character_id}}}
                )
                await query.answer("Character sold successfully!", show_alert=True)
            else:
                await query.answer("Character not found in your collection.", show_alert=True)
