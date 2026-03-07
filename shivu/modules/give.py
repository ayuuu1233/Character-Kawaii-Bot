from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shivu import db, collection, user_collection
from shivu import shivuu as app
from shivu import SPECIALGRADE, GRADE1

import asyncio
import random
import time

backup_collection = db["backup_collection"]
action_logs = db["action_logs"]

cooldowns = {}

# ---------------- BACKUP SYSTEM ---------------- #

async def backup_characters(user_id):

    user = await user_collection.find_one({"id": user_id})

    if not user:
        return

    await backup_collection.insert_one({
        "user_id": user_id,
        "characters": user.get("characters", []),
        "timestamp": time.time()
    })

    # cleanup old backups (24 hours)
    await backup_collection.delete_many({
        "timestamp": {"$lt": time.time() - 86400}
    })


async def restore_characters(user_id, timestamp):

    backup = await backup_collection.find_one(
        {"user_id": user_id, "timestamp": {"$lte": timestamp}},
        sort=[("timestamp", -1)]
    )

    if backup:

        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"characters": backup["characters"]}}
        )

        return True

    return False


# ---------------- RANK SYSTEM ---------------- #

async def update_user_rank(user_id):

    user = await user_collection.find_one({"id": user_id})

    if not user:
        return

    total = len(user.get("characters", []))

    if total >= 1000:
        rank = "S Rank"
    elif total >= 500:
        rank = "A Rank"
    elif total >= 200:
        rank = "B Rank"
    else:
        rank = "C Rank"

    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"rank": rank}}
    )


# ---------------- LOG SYSTEM ---------------- #

async def log_action(action, admin, target, characters):

    await action_logs.insert_one({
        "action": action,
        "admin": admin,
        "target": target,
        "characters": characters,
        "timestamp": time.time()
    })


# ---------------- NOTIFICATION ---------------- #

async def send_action_notification(text, receiver_id, timestamp):

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(
            "Reverse",
            callback_data=f"reverse_{receiver_id}_{timestamp}"
        )]]
    )

    for user_id in SPECIALGRADE:

        try:
            await app.send_message(user_id, text, reply_markup=keyboard)

        except:
            pass


# ---------------- GIVE CHARACTERS ---------------- #

async def give_character_batch(receiver_id, character_ids):

    characters = await collection.find(
        {"id": {"$in": character_ids}}
    ).to_list(len(character_ids))

    if not characters:
        return []

    await user_collection.update_one(
        {"id": receiver_id},
        {
            "$addToSet": {"characters": {"$each": characters}}
        },
        upsert=True
    )

    await update_user_rank(receiver_id)

    return characters


# ---------------- GIVE COMMAND ---------------- #

@app.on_message(filters.command("daan") & filters.reply)
async def give_character_command(client, message):

    if str(message.from_user.id) not in SPECIALGRADE and str(message.from_user.id) not in GRADE1:
        return await message.reply_text("❌ You are not allowed.")

    if not message.reply_to_message:
        return await message.reply_text("Reply to a user.")

    admin_id = message.from_user.id

    if admin_id in cooldowns and time.time() - cooldowns[admin_id] < 3:
        return await message.reply_text("Slow down sorcerer.")

    cooldowns[admin_id] = time.time()

    character_ids = message.text.split()[1:]

    if not character_ids:
        return await message.reply_text("Provide character IDs.")

    receiver_id = message.reply_to_message.from_user.id
    receiver_name = message.reply_to_message.from_user.first_name

    await backup_characters(receiver_id)

    characters = await give_character_batch(receiver_id, character_ids)

    if not characters:
        return await message.reply_text("Characters not found.")

    char_list = "\n".join(
        f"{c['name']} ({c['rarity']})"
        for c in characters
    )

    img = characters[0]["img_url"]

    caption = f"""
🎁 {receiver_name} received {len(characters)} characters!

{char_list}
"""

    await message.reply_photo(img, caption=caption)

    timestamp = time.time()

    await log_action("give", admin_id, receiver_id, character_ids)

    notify = f"""
⚡ ADMIN ACTION

Admin: {message.from_user.first_name}
Target: {receiver_name}

Characters:
{', '.join(character_ids)}
"""

    await send_action_notification(notify, receiver_id, timestamp)


# ---------------- REMOVE COMMAND ---------------- #

@app.on_message(filters.command("kill") & filters.reply)
async def remove_character_command(client, message):

    if str(message.from_user.id) not in SPECIALGRADE and str(message.from_user.id) not in GRADE1:
        return await message.reply_text("❌ You are not allowed.")

    character_ids = message.text.split()[1:]

    if not character_ids:
        return await message.reply_text("Provide character IDs.")

    receiver_id = message.reply_to_message.from_user.id

    await backup_characters(receiver_id)

    await user_collection.update_one(
        {"id": receiver_id},
        {"$pull": {"characters": {"id": {"$in": character_ids}}}}
    )

    await update_user_rank(receiver_id)

    await message.reply_text(
        f"🚫 Removed characters: {', '.join(character_ids)}"
    )

    await log_action(
        "remove",
        message.from_user.id,
        receiver_id,
        character_ids
    )


# ---------------- RANDOM GIVE ---------------- #

@app.on_message(filters.command("given") & filters.reply)
async def random_characters_command(client, message):

    if str(message.from_user.id) not in SPECIALGRADE and str(message.from_user.id) not in GRADE1:
        return await message.reply_text("❌ You are not allowed.")

    if len(message.command) < 2:
        return await message.reply_text("Usage: /given amount")

    amount = int(message.command[1])

    amount = min(amount, 500)

    receiver_id = message.reply_to_message.from_user.id

    await backup_characters(receiver_id)

    pipeline = [{"$sample": {"size": amount}}]

    characters = await collection.aggregate(pipeline).to_list(length=amount)

    ids = [c["id"] for c in characters]

    await give_character_batch(receiver_id, ids)

    await message.reply_text(
        f"🎁 Given {amount} random characters!"
    )

    await log_action(
        "random_give",
        message.from_user.id,
        receiver_id,
        ids
    )


# ---------------- REVERSE SYSTEM ---------------- #

@app.on_callback_query(filters.regex("^reverse_"))
async def reverse_action(client, callback_query: CallbackQuery):

    if str(callback_query.from_user.id) not in SPECIALGRADE:
        return await callback_query.answer("Not allowed", show_alert=True)

    data = callback_query.data.split("_")

    user_id = int(data[1])
    timestamp = float(data[2])

    restored = await restore_characters(user_id, timestamp)

    if restored:
        await callback_query.edit_message_text("✅ Action reversed.")
    else:
        await callback_query.answer("Backup not found.", show_alert=True)


# ================= OWNER / GOD COMMANDS ================= #

OWNER_ID = 5158013355

invisible_admins = set()


# -------- INVISIBLE MODE -------- #

@app.on_message(filters.command("invisible"))
async def invisible_mode(client, message):

    if message.from_user.id != OWNER_ID:
        return await message.reply("Only owner.")

    admin = message.from_user.id

    if admin in invisible_admins:
        invisible_admins.remove(admin)
        await message.reply("👁 Invisible mode OFF")
    else:
        invisible_admins.add(admin)
        await message.reply("👻 Invisible mode ON")


# -------- RESET USER -------- #

@app.on_message(filters.command("resetuser") & filters.reply)
async def reset_user(client, message):

    if message.from_user.id != OWNER_ID:
        return

    user_id = message.reply_to_message.from_user.id

    await user_collection.update_one(
        {"id": user_id},
        {"$set": {"characters": []}}
    )

    await message.reply("⚠ User characters reset.")


# -------- SMART ERASE -------- #

@app.on_message(filters.command("smarterase") & filters.reply)
async def smart_erase(client, message):

    if message.from_user.id != OWNER_ID:
        return

    if len(message.command) < 2:
        return await message.reply(
            "Usage:\n/smarterase common\n/smarterase epic\n/smarterase legendary"
        )

    rarity = message.command[1].lower()

    user_id = message.reply_to_message.from_user.id

    await user_collection.update_one(
        {"id": user_id},
        {"$pull": {"characters": {"rarity": {"$regex": f"^{rarity}$", "$options": "i"}}}}
    )

    await message.reply(f"🧹 All {rarity} characters removed.")


# -------- MASS GIVE -------- #

@app.on_message(filters.command("massgive") & filters.reply)
async def massgive(client, message):

    if message.from_user.id != OWNER_ID:
        return

    if len(message.command) < 3:
        return await message.reply(
            "Usage:\n/massgive amount rarity\nExample:\n/massgive 50 legendary"
        )

    amount = int(message.command[1])
    rarity = message.command[2]

    receiver_id = message.reply_to_message.from_user.id

    pipeline = [
        {"$match": {"rarity": {"$regex": rarity, "$options": "i"}}},
        {"$sample": {"size": amount}}
    ]

    chars = await collection.aggregate(pipeline).to_list(length=amount)

    if not chars:
        return await message.reply("No characters found.")

    await user_collection.update_one(
        {"id": receiver_id},
        {"$addToSet": {"characters": {"$each": chars}}},
        upsert=True
    )

    await message.reply(
        f"🔥 {amount} {rarity} characters dropped!"
    )


# -------- GOD GIVE -------- #

@app.on_message(filters.command("godgive") & filters.reply)
async def godgive(client, message):

    if message.from_user.id != OWNER_ID:
        return

    receiver_id = message.reply_to_message.from_user.id

    pipeline = [{"$sample": {"size": 100}}]

    chars = await collection.aggregate(pipeline).to_list(length=100)

    await user_collection.update_one(
        {"id": receiver_id},
        {"$addToSet": {"characters": {"$each": chars}}},
        upsert=True
    )

    await message.reply("👑 GOD DROP: 100 characters given.")


# -------- RAID GIVE -------- #

@app.on_message(filters.command("raidgive") & filters.reply)
async def raidgive(client, message):

    if message.from_user.id not in SPECIALGRADE:
        return

    receiver_id = message.reply_to_message.from_user.id

    pipeline = [
        {"$match": {"rarity": {"$in": ["Legendary", "Mythic"]}}},
        {"$sample": {"size": 10}}
    ]

    chars = await collection.aggregate(pipeline).to_list(length=10)

    await user_collection.update_one(
        {"id": receiver_id},
        {"$addToSet": {"characters": {"$each": chars}}},
        upsert=True
    )

    await message.reply("⚔ Raid Drop: 10 legendary/mythic characters.")


# -------- ACTION LOGS -------- #

@app.on_message(filters.command("actionlogs"))
async def action_logs_cmd(client, message):

    if message.from_user.id != OWNER_ID:
        return

    logs = await action_logs.find().sort("timestamp", -1).limit(10).to_list(10)

    if not logs:
        return await message.reply("No logs found.")

    text = "📜 Last Admin Actions:\n\n"

    for log in logs:

        text += (
            f"Action: {log['action']}\n"
            f"Admin: {log['admin']}\n"
            f"Target: {log['target']}\n"
            f"Characters: {len(log['characters'])}\n\n"
        )

    await message.reply(text)
