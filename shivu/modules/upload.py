import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent,
    ReplyKeyboardMarkup, KeyboardButton
)
from pymongo import ReturnDocument
from shivu import user_collection, collection, CHARA_CHANNEL_ID, SUPPORT_CHAT, shivuu as app, sudo_users, db
from pyrogram.errors import BadRequest

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
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
    '💞 Valentine': '💞',
}

event_emojis = {
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
    '⚽ Soccer': '⚽',
}

# In-memory state store
user_states = {}

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def is_sudo(user_id: int) -> bool:
    """Check if user is a sudo user (handles both int and str stored IDs)."""
    return str(user_id) in sudo_users or user_id in sudo_users


async def get_next_sequence_number(sequence_name: str) -> int:
    sequence_collection = db.sequences
    doc = await sequence_collection.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'sequence_value': 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc['sequence_value']


def pack(prefix: str, *parts) -> str:
    """
    Pack callback_data safely.
    Uses '|' as separator so emoji/space in parts don't break splits.
    Example: pack("set_rarity", "🟡 Legendary", "42") → "set_rarity|🟡 Legendary|42"
    """
    return prefix + "|" + "|".join(str(p) for p in parts)


def unpack(data: str, prefix: str):
    """
    Unpack callback_data packed with pack().
    Returns list of parts after the prefix.
    """
    return data[len(prefix) + 1:].split("|")


# ─────────────────────────────────────────────
#  /start
# ─────────────────────────────────────────────
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if not is_sudo(message.from_user.id):
        return
    user = await app.get_users(message.from_user.id)
    await message.reply_text(
        f"Hello [{user.first_name}](tg://user?id={message.from_user.id})!",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("⚙ Admin panel ⚙")]],
            resize_keyboard=True,
        ),
    )


# ─────────────────────────────────────────────
#  ADMIN PANEL
# ─────────────────────────────────────────────
@app.on_message(filters.text & filters.private & filters.regex(r"^⚙ Admin panel ⚙$"))
async def admin_panel(client, message):
    if not is_sudo(message.from_user.id):
        return await message.reply_text("You are not authorized.")

    total_waifus = await collection.count_documents({})
    total_animes = len(await collection.distinct("anime"))
    total_harems = await user_collection.count_documents({})

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🆕 Add Character", callback_data="add_waifu"),
            InlineKeyboardButton("Add Anime 🆕", callback_data="add_anime"),
        ],
        [InlineKeyboardButton("👾 Anime List", switch_inline_query_current_chat="choose_anime ")],
    ])
    await message.reply_text(
        f"**Admin Panel**\n\n"
        f"Total Waifus: {total_waifus}\n"
        f"Total Animes: {total_animes}\n"
        f"Total Harems: {total_harems}",
        reply_markup=kb,
    )


# ─────────────────────────────────────────────
#  /edit COMMAND
# ─────────────────────────────────────────────
@app.on_message(filters.command("edit") & filters.private)
async def edit_waifu_command(client, message):
    if not is_sudo(message.from_user.id):
        return await message.reply_text("You are not authorized.")
    if len(message.command) < 2:
        return await message.reply_text("Usage: /edit <waifu_id>")

    waifu_id = message.command[1]
    waifu = await collection.find_one({"id": waifu_id})
    if not waifu:
        return await message.reply_text("Character not found.")

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧩 Rename Character",  callback_data=pack("rename_waifu",  waifu_id))],
        [InlineKeyboardButton("⛱️ Change Image",      callback_data=pack("change_image",  waifu_id))],
        [InlineKeyboardButton("⛩️ Change Rarity",     callback_data=pack("change_rarity", waifu_id))],
        [InlineKeyboardButton("🎉 Edit Event",         callback_data=pack("change_event",  waifu_id))],
        [InlineKeyboardButton("📢 Reset Character",   callback_data=pack("reset_waifu",   waifu_id))],
        [InlineKeyboardButton("🗑️ Remove Character",  callback_data=pack("remove_waifu",  waifu_id))],
    ])
    await message.reply_photo(
        photo=waifu["img_url"],
        caption=f"👧 **Name:** {waifu['name']}\n🎥 **Anime:** {waifu['anime']}\n🏷 **Rarity:** {waifu['rarity']}",
        reply_markup=kb,
    )


# ─────────────────────────────────────────────
#  ADD ANIME flow
# ─────────────────────────────────────────────
@app.on_callback_query(filters.regex(r"^add_anime$"))
async def add_anime_callback(client, cb):
    if not is_sudo(cb.from_user.id):
        return await cb.answer("Not authorized.", show_alert=True)
    user_states[cb.from_user.id] = {"state": "adding_anime"}
    await cb.message.edit_text("Please enter the name of the anime you want to add:")


# ─────────────────────────────────────────────
#  ADD CHARACTER flow  (step 1 — pick anime)
# ─────────────────────────────────────────────
@app.on_callback_query(filters.regex(r"^add_waifu$"))
async def add_waifu_callback(client, cb):
    if not is_sudo(cb.from_user.id):
        return await cb.answer("Not authorized.", show_alert=True)
    await cb.message.edit_text(
        "Choose an anime to save the character in:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👾 Search Anime", switch_inline_query_current_chat="choose_anime ")],
            [InlineKeyboardButton("⚔️ Cancel", callback_data="cancel_add_waifu")],
        ]),
    )


# Triggered when user taps "Add Character" from inline result
@app.on_callback_query(filters.regex(r"^add_waifu\|"))
async def choose_anime_callback(client, cb):
    if not is_sudo(cb.from_user.id):
        return await cb.answer("Not authorized.", show_alert=True)
    selected_anime = unpack(cb.data, "add_waifu")[0]
    user_states[cb.from_user.id] = {
        "state": "awaiting_waifu_name",
        "anime": selected_anime,
        "name": None,
        "rarity": None,
        "event_emoji": "",
        "event_name": "",
    }
    await app.send_message(
        chat_id=cb.from_user.id,
        text=f"You've selected **{selected_anime}**.\nNow please enter the new character's name:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_add_waifu")]]),
    )


@app.on_callback_query(filters.regex(r"^cancel_add_waifu$"))
async def cancel_add_waifu_callback(client, cb):
    user_states.pop(cb.from_user.id, None)
    await cb.message.edit_text("Operation cancelled.")


# ─────────────────────────────────────────────
#  INLINE QUERY — anime search
# ─────────────────────────────────────────────
@app.on_inline_query()
async def search_anime(client, inline_query):
    if not is_sudo(inline_query.from_user.id):
        return

    query = inline_query.query.strip()
    if not query.lower().startswith("choose_anime"):
        return

    search_term = query[len("choose_anime"):].strip()

    anime_results = await collection.aggregate([
        {"$match": {"anime": {"$regex": search_term, "$options": "i"}}},
        {"$group": {"_id": "$anime", "waifu_count": {"$sum": 1}}},
        {"$limit": 10},
    ]).to_list(length=None)

    results = []
    for anime in anime_results:
        title = anime["_id"]
        count = anime["waifu_count"]
        # Truncate title so callback_data stays within Telegram 64-byte limit
        title_short = title[:25]
        results.append(
            InlineQueryResultArticle(
                title=title,
                description=f"Characters: {count}",
                input_message_content=InputTextMessageContent(
                    f"✏ **Title:** {title}\n🏷 **Characters:** {count}"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Add Character",  callback_data=pack("add_waifu",        title_short))],
                    [InlineKeyboardButton("✏️ Rename Anime",   callback_data=pack("rename_anime",     title_short))],
                    [InlineKeyboardButton("🗑️ Remove Anime",   callback_data=pack("remove_anime",     title_short))],
                    [InlineKeyboardButton("👁 View Characters", callback_data=pack("view_characters", title_short))],
                ]),
            )
        )

    await inline_query.answer(results, cache_time=1)


# ─────────────────────────────────────────────
#  VIEW / RENAME / REMOVE ANIME callbacks
# ─────────────────────────────────────────────
@app.on_callback_query(filters.regex(r"^view_characters\|"))
async def view_characters_callback(client, cb):
    anime_name = unpack(cb.data, "view_characters")[0]
    waifus = await collection.find({"anime": anime_name}).to_list(length=None)
    if waifus:
        lines = "\n".join(
            f"• {w.get('name','?')}  ({w.get('rarity','?')})" for w in waifus
        )
        await cb.message.edit_text(f"**Characters in '{anime_name}':**\n\n{lines}")
    else:
        await cb.message.edit_text("No characters found for this anime.")


@app.on_callback_query(filters.regex(r"^rename_anime\|"))
async def rename_anime_callback(client, cb):
    if not is_sudo(cb.from_user.id):
        return await cb.answer("Not authorized.", show_alert=True)
    selected_anime = unpack(cb.data, "rename_anime")[0]
    user_states[cb.from_user.id] = {"state": "renaming_anime", "anime": selected_anime}
    await app.send_message(
        chat_id=cb.from_user.id,
        text=f"Enter the new name for anime **'{selected_anime}'**:",
    )


@app.on_callback_query(filters.regex(r"^remove_anime\|"))
async def remove_anime_callback(client, cb):
    if not is_sudo(cb.from_user.id):
        return await cb.answer("Not authorized.", show_alert=True)
    selected_anime = unpack(cb.data, "remove_anime")[0]
    user_states[cb.from_user.id] = {"state": "confirming_removal", "anime": selected_anime}
    await app.send_message(
        chat_id=cb.from_user.id,
        text=f"Are you sure you want to delete **'{selected_anime}'** and all its characters?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes", callback_data="confirm_remove_anime")],
            [InlineKeyboardButton("❌ No",  callback_data="cancel_remove_anime")],
        ]),
    )


@app.on_callback_query(filters.regex(r"^confirm_remove_anime$"))
async def confirm_remove_anime_callback(client, cb):
    data = user_states.get(cb.from_user.id, {})
    if data.get("state") != "confirming_removal":
        return
    anime = data["anime"]
    await collection.delete_many({"anime": anime})
    await cb.message.edit_text(f"Anime **'{anime}'** and all its characters have been deleted.")
    await app.send_message(CHARA_CHANNEL_ID, f"📢 Sudo deleted anime: **{anime}**")
    await app.send_message(SUPPORT_CHAT,     f"📢 Sudo deleted anime: **{anime}**")
    user_states.pop(cb.from_user.id, None)


@app.on_callback_query(filters.regex(r"^cancel_remove_anime$"))
async def cancel_remove_anime_callback(client, cb):
    user_states.pop(cb.from_user.id, None)
    await cb.message.edit_text("Operation cancelled.")


# ─────────────────────────────────────────────
#  EDIT CHARACTER callbacks
# ─────────────────────────────────────────────

# --- Rename ---
@app.on_callback_query(filters.regex(r"^rename_waifu\|"))
async def rename_waifu_callback(client, cb):
    waifu_id = unpack(cb.data, "rename_waifu")[0]
    user_states[cb.from_user.id] = {"state": "renaming_waifu", "waifu_id": waifu_id}
    await cb.message.edit_text(f"Enter the new name for character ID **{waifu_id}**:")


# --- Change Image ---
@app.on_callback_query(filters.regex(r"^change_image\|"))
async def change_image_callback(client, cb):
    waifu_id = unpack(cb.data, "change_image")[0]
    user_states[cb.from_user.id] = {"state": "changing_image", "waifu_id": waifu_id}
    await cb.message.edit_text(
        f"Send the new image for character ID **{waifu_id}**:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_change_image")]]),
    )


@app.on_callback_query(filters.regex(r"^cancel_change_image$"))
async def cancel_change_image_callback(client, cb):
    user_states.pop(cb.from_user.id, None)
    await cb.message.edit_text("Operation cancelled.")


# --- Change Rarity ---
@app.on_callback_query(filters.regex(r"^change_rarity\|"))
async def change_rarity_callback(client, cb):
    waifu_id = unpack(cb.data, "change_rarity")[0]
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(r, callback_data=pack("set_rarity", r, waifu_id))]
        for r in rarity_emojis
    ])
    await cb.message.edit_text("Choose a new rarity:", reply_markup=kb)


@app.on_callback_query(filters.regex(r"^set_rarity\|"))
async def set_rarity_callback(client, cb):
    try:
        new_rarity, waifu_id = unpack(cb.data, "set_rarity")
        waifu = await collection.find_one_and_update(
            {"id": waifu_id},
            {"$set": {"rarity": new_rarity}},
            return_document=ReturnDocument.AFTER,
        )
        if not waifu:
            return await cb.answer("Character not found.", show_alert=True)

        caption = (
            f"🏅 **Rarity Update**\n"
            f"🆔 ID: {waifu['id']}\n"
            f"👤 Name: {waifu['name']}\n"
            f"🎌 Anime: {waifu['anime']}\n"
            f"🎖 New Rarity: {new_rarity}"
        )
        await app.send_photo(cb.from_user.id, photo=waifu["img_url"], caption=caption)
        await app.send_photo(CHARA_CHANNEL_ID,  photo=waifu["img_url"], caption=caption)
        await app.send_photo(SUPPORT_CHAT,       photo=waifu["img_url"], caption=caption)
        await cb.message.edit_text(f"✅ Rarity changed to **{new_rarity}** successfully.")
    except Exception as e:
        logger.error(f"set_rarity_callback: {e}", exc_info=True)
        await cb.answer("An error occurred.", show_alert=True)


# --- Change Event ---
@app.on_callback_query(filters.regex(r"^change_event\|"))
async def change_event_callback(client, cb):
    waifu_id = unpack(cb.data, "change_event")[0]
    user_states[cb.from_user.id] = {"state": "changing_event", "waifu_id": waifu_id}
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(e, callback_data=pack("set_new_event", e, waifu_id))] for e in event_emojis]
        + [[InlineKeyboardButton("Skip Event", callback_data=pack("set_new_event", "none", waifu_id))]]
    )
    await cb.message.edit_text("Choose a new event (or skip):", reply_markup=kb)


@app.on_callback_query(filters.regex(r"^set_new_event\|"))
async def set_new_event_callback(client, cb):
    try:
        evt, waifu_id = unpack(cb.data, "set_new_event")
        if evt == "none":
            await collection.update_one({"id": waifu_id}, {"$set": {"event_emoji": "", "event_name": ""}})
            await cb.message.edit_text(f"✅ Event cleared for ID **{waifu_id}**.")
        else:
            emoji = event_emojis.get(evt, "")
            await collection.update_one({"id": waifu_id}, {"$set": {"event_emoji": emoji, "event_name": evt}})
            await cb.message.edit_text(f"✅ Event updated to **{evt}** for ID **{waifu_id}**.")
        user_states.pop(cb.from_user.id, None)
    except Exception as e:
        logger.error(f"set_new_event_callback: {e}", exc_info=True)
        await cb.message.edit_text("An error occurred while updating the event.")


# --- Reset ---
@app.on_callback_query(filters.regex(r"^reset_waifu\|"))
async def reset_waifu_callback(client, cb):
    waifu_id = unpack(cb.data, "reset_waifu")[0]
    user_states[cb.from_user.id] = {"state": "confirming_reset", "waifu_id": waifu_id}
    await cb.message.edit_text(
        f"Reset character ID **{waifu_id}** global_grabbed to 0?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes", callback_data=pack("confirm_reset_waifu", waifu_id))],
            [InlineKeyboardButton("❌ No",  callback_data="cancel_reset_waifu")],
        ]),
    )


@app.on_callback_query(filters.regex(r"^confirm_reset_waifu\|"))
async def confirm_reset_waifu_callback(client, cb):
    waifu_id = unpack(cb.data, "confirm_reset_waifu")[0]
    waifu = await collection.find_one_and_update(
        {"id": waifu_id},
        {"$set": {"global_grabbed": 0}},
        return_document=ReturnDocument.AFTER,
    )
    if waifu:
        await cb.message.edit_text(f"✅ Character **{waifu_id}** reset successfully.")
        await app.send_photo(
            CHARA_CHANNEL_ID,
            photo=waifu["img_url"],
            caption=f"🔄 **Reset Notice**\nID: {waifu_id} | {waifu['name']} ({waifu['anime']}) reset.",
        )
    else:
        await cb.message.edit_text("Failed to reset — character not found.")
    user_states.pop(cb.from_user.id, None)


@app.on_callback_query(filters.regex(r"^cancel_reset_waifu$"))
async def cancel_reset_waifu_callback(client, cb):
    user_states.pop(cb.from_user.id, None)
    await cb.message.edit_text("Operation cancelled.")


# --- Remove ---
@app.on_callback_query(filters.regex(r"^remove_waifu\|"))
async def remove_waifu_callback(client, cb):
    waifu_id = unpack(cb.data, "remove_waifu")[0]
    user_states[cb.from_user.id] = {"state": "confirming_waifu_removal", "waifu_id": waifu_id}
    await cb.message.edit_text(
        f"Remove character ID **{waifu_id}**?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes", callback_data="confirm_remove_waifu")],
            [InlineKeyboardButton("❌ No",  callback_data="cancel_remove_waifu")],
        ]),
    )


@app.on_callback_query(filters.regex(r"^confirm_remove_waifu$"))
async def confirm_remove_waifu_callback(client, cb):
    data = user_states.get(cb.from_user.id, {})
    if data.get("state") != "confirming_waifu_removal":
        return
    waifu_id = data["waifu_id"]
    waifu = await collection.find_one_and_delete({"id": waifu_id})
    if waifu:
        caption = (
            f"🗑️ **Character Removed**\n"
            f"👤 Name: {waifu['name']}\n"
            f"🎌 Anime: {waifu['anime']}"
        )
        await cb.message.edit_text(f"✅ Character **{waifu_id}** removed.")
        await app.send_photo(CHARA_CHANNEL_ID, photo=waifu["img_url"], caption=caption)
        await app.send_photo(SUPPORT_CHAT,      photo=waifu["img_url"], caption=caption)
    else:
        await cb.message.edit_text("Character not found.")
    user_states.pop(cb.from_user.id, None)


@app.on_callback_query(filters.regex(r"^cancel_remove_waifu$"))
async def cancel_remove_waifu_callback(client, cb):
    user_states.pop(cb.from_user.id, None)
    await cb.message.edit_text("Operation cancelled.")


# ─────────────────────────────────────────────
#  ADD CHARACTER — rarity & event selection
# ─────────────────────────────────────────────
@app.on_callback_query(filters.regex(r"^select_rarity\|"))
async def select_rarity_callback(client, cb):
    selected_rarity = unpack(cb.data, "select_rarity")[0]
    if cb.from_user.id not in user_states:
        return await cb.answer("Session expired. Start again.", show_alert=True)
    user_states[cb.from_user.id]["rarity"] = selected_rarity
    user_states[cb.from_user.id]["state"] = "selecting_event"

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(e, callback_data=pack("set_event", e))] for e in event_emojis]
        + [[InlineKeyboardButton("Skip Event", callback_data="set_event|none")]]
    )
    await cb.message.edit_text("Choose an event (or skip):", reply_markup=kb)


@app.on_callback_query(filters.regex(r"^set_event\|"))
async def set_event_callback(client, cb):
    evt = unpack(cb.data, "set_event")[0]
    if cb.from_user.id not in user_states:
        return await cb.answer("Session expired. Start again.", show_alert=True)
    if evt == "none":
        user_states[cb.from_user.id]["event_emoji"] = ""
        user_states[cb.from_user.id]["event_name"] = ""
    else:
        user_states[cb.from_user.id]["event_emoji"] = event_emojis.get(evt, "")
        user_states[cb.from_user.id]["event_name"] = evt
    user_states[cb.from_user.id]["state"] = "awaiting_waifu_image"
    await cb.message.edit_text("Now send the character's image/photo:")


# ─────────────────────────────────────────────
#  TEXT MESSAGE HANDLER  (single, unified)
# ─────────────────────────────────────────────
@app.on_message(filters.private & filters.text & ~filters.regex(r"^⚙ Admin panel ⚙$"))
async def receive_text_message(client, message):
    # Ignore bot commands — let command handlers deal with them
    if message.text and message.text.startswith("/"):
        return

    uid = message.from_user.id
    data = user_states.get(uid)
    if not data:
        return

    state = data.get("state")
    text = message.text.strip()

    # ── Adding anime ──
    if state == "adding_anime":
        existing = await collection.find_one({"anime": text})
        if existing:
            await message.reply_text(f"Anime **'{text}'** already exists.")
        else:
            await message.reply_text(f"✅ Anime **'{text}'** noted! Use Add Character to add characters to it.")
        user_states.pop(uid, None)

    # ── Character name ──
    elif state == "awaiting_waifu_name":
        user_states[uid]["name"] = text
        user_states[uid]["state"] = "awaiting_waifu_rarity"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(r, callback_data=pack("select_rarity", r))]
            for r in rarity_emojis
        ])
        await message.reply_text("Choose the character's rarity:", reply_markup=kb)

    # ── Rename anime ──
    elif state == "renaming_anime":
        old = data["anime"]
        await collection.update_many({"anime": old}, {"$set": {"anime": text}})
        await message.reply_text(f"✅ Anime renamed from **'{old}'** to **'{text}'**.")
        await app.send_message(CHARA_CHANNEL_ID, f"#RENAMEANIME\n'{old}' → '{text}'")
        await app.send_message(SUPPORT_CHAT,     f"#RENAMEANIME\n'{old}' → '{text}'")
        user_states.pop(uid, None)

    # ── Rename character ──
    elif state == "renaming_waifu":
        waifu_id = data["waifu_id"]
        waifu = await collection.find_one({"id": waifu_id})
        if waifu:
            old_name = waifu["name"]
            await collection.update_one({"id": waifu_id}, {"$set": {"name": text}})
            await message.reply_text(f"✅ Character renamed to **'{text}'**.")
            caption = (
                f"#CHANGEDNAME\n"
                f"By: {message.from_user.first_name}\n"
                f"'{old_name}' → '{text}'"
            )
            await app.send_photo(CHARA_CHANNEL_ID, photo=waifu["img_url"], caption=caption)
            await app.send_photo(SUPPORT_CHAT,      photo=waifu["img_url"], caption=caption)
        else:
            await message.reply_text("Character not found.")
        user_states.pop(uid, None)


# ─────────────────────────────────────────────
#  PHOTO HANDLER
# ─────────────────────────────────────────────
@app.on_message(filters.private & filters.photo)
async def receive_photo(client, message):
    uid = message.from_user.id
    data = user_states.get(uid)
    if not data:
        return

    state = data.get("state")

    # ── Save new character ──
    if state == "awaiting_waifu_image":
        try:
            photo_id = message.photo.file_id
            waifu_id = str(await get_next_sequence_number('character_id')).zfill(2)
            character = {
                'img_url':     photo_id,
                'name':        data["name"],
                'anime':       data["anime"],
                'rarity':      data["rarity"],
                'id':          waifu_id,
                'event_emoji': data.get("event_emoji", ""),
                'event_name':  data.get("event_name",  ""),
                'global_grabbed': 0,
            }
            await collection.insert_one(character)

            caption = (
                f"OwO! New character!\n\n"
                f"**{data['anime']}**\n"
                f"`{waifu_id}`: {data['name']} {character['event_emoji']}\n"
                f"(RARITY: {data['rarity']})\n"
                f"{character['event_name']}\n\n"
                f"➼ Added by: [{message.from_user.first_name}](tg://user?id={uid})"
            )
            await message.reply_text(f"✅ Character **{data['name']}** added! ID: `{waifu_id}`")
            await app.send_photo(CHARA_CHANNEL_ID, photo=photo_id, caption=caption)
            await app.send_photo(SUPPORT_CHAT,      photo=photo_id, caption=caption)
            user_states.pop(uid, None)
        except Exception as e:
            logger.error(f"receive_photo (add): {e}", exc_info=True)
            await message.reply_text("An error occurred while saving the character.")

    # ── Change existing image ──
    elif state == "changing_image":
        try:
            waifu_id = data["waifu_id"]
            new_img = message.photo.file_id
            waifu = await collection.find_one_and_update(
                {"id": waifu_id},
                {"$set": {"img_url": new_img}},
                return_document=ReturnDocument.AFTER,
            )
            if waifu:
                caption = (
                    f"🖼 Image Updated!\n"
                    f"🆔 ID: {waifu_id}\n"
                    f"👤 Name: {waifu['name']}\n"
                    f"🎌 Anime: {waifu['anime']}"
                )
                await message.reply_text("✅ Image updated successfully.")
                await app.send_photo(CHARA_CHANNEL_ID, photo=new_img, caption=caption)
                await app.send_photo(SUPPORT_CHAT,      photo=new_img, caption=caption)
            else:
                await message.reply_text("Character not found.")
            user_states.pop(uid, None)
        except Exception as e:
            logger.error(f"receive_photo (change_image): {e}", exc_info=True)
            await message.reply_text("An error occurred while updating the image.")
            
