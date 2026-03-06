from pyrogram import filters
from shivu import db, user_collection, SPECIALGRADE, GRADE1
from shivu import shivuu as app
import random
import datetime
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

backup_collection = db["backup_collection"]

# CONFIG
MAX_ERASE_LIMIT = 1000
PROTECTED_RARITY = ["Legendary", "Mythic"]

# Backup characters
async def backup_characters(user_id, characters):
    await backup_collection.insert_one({
        "user_id": user_id,
        "characters": characters,
        "time": datetime.datetime.utcnow()
    })

# Count rarity
def count_characters_by_rarity(characters):
    rarity_count = {}
    for character in characters:
        rarity = character.get("rarity", "Unknown")
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
    return rarity_count

# Erase characters
async def erase_characters_for_user(user_id, num_characters):

    user = await user_collection.find_one({'id': user_id})

    if not user:
        return f"❌ User with ID {user_id} not found."

    characters = user.get("characters", [])

    if not characters:
        return f"⚠️ <a href='tg://user?id={user_id}'>{user.get('first_name','User')}</a> has no characters."

    total_characters = len(characters)

    num_characters_to_remove = min(num_characters, total_characters)

    # protect rarities
    removable_characters = [
        c for c in characters
        if c.get("rarity") not in PROTECTED_RARITY
    ]

    if not removable_characters:
        return "🛡 All characters are protected rarity."

    num_characters_to_remove = min(num_characters_to_remove, len(removable_characters))

    characters_to_remove = random.sample(removable_characters, num_characters_to_remove)

    remaining_characters = [
        c for c in characters if c not in characters_to_remove
    ]

    # Backup
    await backup_characters(user_id, characters)

    # Update DB
    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"characters": remaining_characters}}
    )

    # Rarity stats
    rarity_removed = count_characters_by_rarity(characters_to_remove)
    rarity_remaining = count_characters_by_rarity(remaining_characters)

    max_rarity = max(rarity_removed, key=rarity_removed.get)

    removed_msg = "\n".join([f"• {r}: {c}" for r, c in rarity_removed.items()])
    remaining_msg = "\n".join([f"• {r}: {c}" for r, c in rarity_remaining.items()])

    return (
        f"⚔️ <b>Harem Erase Report</b>\n\n"
        f"👤 <b>User:</b> <a href='tg://user?id={user_id}'>{user.get('first_name','User')}</a>\n\n"
        f"🗑 <b>Removed:</b> {num_characters_to_remove}\n"
        f"📦 <b>Remaining:</b> {len(remaining_characters)}\n\n"
        f"🔥 <b>Most Erased Rarity:</b> {max_rarity}\n\n"
        f"📉 <b>Removed Rarity</b>\n{removed_msg}\n\n"
        f"📊 <b>Remaining Rarity</b>\n{remaining_msg}"
    )

# Restore characters
async def restore_characters(user_id):

    backup = await backup_collection.find_one(
        {"user_id": user_id},
        sort=[("time", -1)]
    )

    if not backup:
        return False

    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"characters": backup["characters"]}}
    )

    await backup_collection.delete_one({"_id": backup["_id"]})

    return True

# ERASE COMMAND
@app.on_message(filters.command(["erase"]))
async def erase_characters_command(client, message):

    admin_id = str(message.from_user.id)

    if admin_id not in SPECIALGRADE and admin_id not in GRADE1:
        await message.reply_text("🚫 Only Special Grade or Grade 1 can use this command.")
        return

    if not message.reply_to_message:
        await message.reply_text("❌ Reply to a user to erase characters.")
        return

    target_user = message.reply_to_message.from_user
    target_id = target_user.id

    # self protection
    if target_id == message.from_user.id:
        await message.reply_text("⚠️ You cannot erase your own characters.")
        return

    # special grade protection
    if str(target_id) in SPECIALGRADE and admin_id not in SPECIALGRADE:
        await message.reply_text("🚫 You cannot erase Special Grade user's characters.")
        return

    if len(message.command) != 2:
        await message.reply_text("Usage: /erase {number}")
        return

    if not message.command[1].isdigit():
        await message.reply_text("❌ Enter a valid number.")
        return

    num = int(message.command[1])

    if num > MAX_ERASE_LIMIT:
        await message.reply_text(f"⚠️ Max erase limit is {MAX_ERASE_LIMIT}.")
        return

    result = await erase_characters_for_user(target_id, num)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔁 Reverse", callback_data=f"reverse_{target_id}")]
    ])

    await message.reply_text(result, reply_markup=keyboard)

# REVERSE ERASE
@app.on_callback_query(filters.regex(r"^reverse_\d+$"))
async def reverse_erase(client, callback_query: CallbackQuery):

    target_id = int(callback_query.data.split("_")[1])

    if str(callback_query.from_user.id) not in SPECIALGRADE:
        await callback_query.answer("🚫 You cannot reverse this.", show_alert=True)
        return

    restored = await restore_characters(target_id)

    if restored:
        await callback_query.edit_message_text("✅ Characters restored successfully.")
    else:
        await callback_query.answer("⚠️ No backup found.", show_alert=True)
