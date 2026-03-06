import random
import asyncio
from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from shivu import shivuu as app, user_collection

COOLDOWN_DURATION = 300  # 5 minutes

# Track user cooldowns and running adventures
user_cooldowns = {}
ongoing_explorations = {}

# Exploration locations
exploration_options = [
    "Dungeon 🏰", "Demon Village 😈", "Sonagachi 💃", "Russian Harem 💋",
    "Ambani House 🏦", "Sex City 🏙️", "Fusha Village 🏞️", "Mystic Forest 🌲",
    "Dragon's Lair 🐉", "Pirate Cove 🏴‍☠️", "Haunted Mansion 👻",
    "Enchanted Garden 🌸", "Lost City 🏙️", "Viking Stronghold ⚔️",
    "Samurai Dojo 🥋", "Wizard Tower 🧙‍♂️", "Crystal Cave 💎",
    "Mermaid Lagoon 🧜‍♀️", "Gnome Village 🧝", "Fairy Forest 🧚",
    "Goblin Camp 👺", "Minotaur Labyrinth 🐂", "Phoenix Nest 🔥",
    "Treasure Island 🏝️", "Jungle Temple 🏯"
]

# Animation messages
exploration_animations = [
    "🔍 Scanning the area for hidden treasures...",
    "👣 Treading carefully through unknown paths...",
    "✨ A mysterious energy surrounds your journey...",
    "🕵️ Searching for ancient secrets...",
    "🧭 Following the compass to the unknown..."
]

# Result messages
place_messages = {
    "Dungeon 🏰": "💀 You braved the Dungeon and found ancient treasure!",
    "Demon Village 😈": "😈 You escaped the demons with rare jewels!",
    "Sonagachi 💃": "💃 A wild night rewarded you with unexpected riches!",
    "Russian Harem 💋": "💋 Exotic adventure rewarded you with artifacts!",
    "Ambani House 🏦": "🏦 You cracked the vault and escaped rich!",
    "Sex City 🏙️": "🌆 The dark alleys hid unimaginable wealth!",
    "Fusha Village 🏞️": "🍃 Nature blessed you with hidden fortune!",
    "Mystic Forest 🌲": "🌲 You found enchanted coins in the fog!",
    "Dragon's Lair 🐉": "🔥 You escaped with the dragon's hoard!",
    "Pirate Cove 🏴‍☠️": "🏴‍☠️ Pirate gold is now yours!",
    "Haunted Mansion 👻": "👻 Even ghosts couldn't stop your treasure hunt!",
    "Enchanted Garden 🌸": "🌸 The fairies gifted you magical gold!",
    "Lost City 🏙️": "🏙️ Ancient ruins hid priceless treasure!",
    "Viking Stronghold ⚔️": "⚔️ Vikings left behind their legendary treasure!",
    "Samurai Dojo 🥋": "🥋 Honor revealed hidden gems!",
    "Wizard Tower 🧙‍♂️": "🔮 You stole mystical artifacts!",
    "Crystal Cave 💎": "💎 You found dazzling crystals!",
    "Mermaid Lagoon 🧜‍♀️": "🧜‍♀️ Mermaids' hidden treasure is yours!",
    "Gnome Village 🧝": "🧝 Gnomes rewarded your bravery with gold!",
    "Fairy Forest 🧚": "🧚 Fairies revealed secret riches!",
    "Goblin Camp 👺": "👺 You raided the goblin camp!",
    "Minotaur Labyrinth 🐂": "🐂 You defeated the Minotaur!",
    "Phoenix Nest 🔥": "🔥 A fiery treasure awaits you!",
    "Treasure Island 🏝️": "🏝️ Legendary pirate treasure found!",
    "Jungle Temple 🏯": "🏯 Ancient temple revealed hidden wealth!"
}


# Start exploration
@app.on_message(filters.command("crime"))
async def explore_command(client, message):

    user_id = message.from_user.id

    if message.chat.type == "private":
        return await message.reply_text(
            "⚠️ <b>This command only works in groups!</b>"
        )

    if user_id in ongoing_explorations:
        return await message.reply_text(
            "🕰️ <b>You are already on an adventure!</b>"
        )

    if user_id in user_cooldowns:
        diff = datetime.utcnow() - user_cooldowns[user_id]
        if diff < timedelta(seconds=COOLDOWN_DURATION):
            remain = COOLDOWN_DURATION - diff.total_seconds()
            return await message.reply_text(
                f"⏳ Wait {int(remain)} seconds before exploring again."
            )

    ongoing_explorations[user_id] = True

    options = random.sample(exploration_options, 2)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(options[0], callback_data=f"explore_{user_id}_{options[0]}")],
        [InlineKeyboardButton(options[1], callback_data=f"explore_{user_id}_{options[1]}")]
    ])

    await message.reply_text(
        "🗺️ <b>Choose your adventure location:</b>",
        reply_markup=keyboard
    )


# Handle exploration
@app.on_callback_query(filters.regex("^explore_"))
async def explore_callback(client, callback_query: CallbackQuery):

    user_id = callback_query.from_user.id
    data = callback_query.data.split("_")

    cmd_user = int(data[1])
    place = "_".join(data[2:])

    if user_id != cmd_user:
        return await callback_query.answer(
            "⚠️ This adventure isn't yours!", show_alert=True
        )

    # Animation
    for text in exploration_animations:
        await callback_query.message.edit_text(text)
        await asyncio.sleep(1)

    reward = random.randint(1000, 5000)

    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": reward}}
    )

    ongoing_explorations.pop(user_id, None)
    user_cooldowns[user_id] = datetime.utcnow()

    result = place_messages.get(
        place,
        f"✨ You explored {place} and found hidden treasure!"
    )

    await callback_query.message.edit_text(
        f"{result}\n\n🎉 <b>You earned {reward} tokens! 💰</b>"
  )
  # ================= NEW CRIME FEATURES =================

JAIL_TIME = 120
user_jail = {}

@app.on_callback_query(filters.regex(r"^explore_"))
async def extra_crime_logic(client, callback_query: CallbackQuery):

    user_id = callback_query.from_user.id

    # Jail check
    if user_id in user_jail:
        if datetime.utcnow() < user_jail[user_id]:
            remaining = (user_jail[user_id] - datetime.utcnow()).seconds
            return await callback_query.answer(
                f"🚔 You're in jail for {remaining} seconds!", show_alert=True
            )
        else:
            user_jail.pop(user_id)

    chance = random.randint(1,100)

    # FAIL EVENT
    if chance <= 25:
        user_jail[user_id] = datetime.utcnow() + timedelta(seconds=JAIL_TIME)

        await callback_query.message.reply_text(
            "🚔 <b>Police caught you during the crime!</b>\n"
            f"🔒 You're jailed for {JAIL_TIME} seconds."
        )

    # JACKPOT EVENT
    elif chance >= 97:
        jackpot = random.randint(20000,50000)

        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"balance": jackpot}}
        )

        await callback_query.message.reply_text(
            f"🎰 <b>ULTRA JACKPOT!!!</b>\n\n"
            f"💰 You found a hidden treasure worth {jackpot} tokens!"
        )
      # ================= ROB USER SYSTEM =================

rob_cooldown = {}
ROB_COOLDOWN = 600

@app.on_message(filters.command("rob"))
async def rob_user(client, message):

    user_id = message.from_user.id

    if not message.reply_to_message:
        return await message.reply_text("⚠️ Reply to a user to rob them.")

    target = message.reply_to_message.from_user.id

    if user_id == target:
        return await message.reply_text("😂 You can't rob yourself.")

    if user_id in rob_cooldown:
        diff = datetime.utcnow() - rob_cooldown[user_id]
        if diff < timedelta(seconds=ROB_COOLDOWN):
            remain = ROB_COOLDOWN - diff.total_seconds()
            return await message.reply_text(f"⏳ Wait {int(remain)} seconds.")

    chance = random.randint(1,100)

    if chance <= 40:
        return await message.reply_text("🚔 Police caught you while robbing!")

    steal = random.randint(500,3000)

    await user_collection.update_one(
        {"id": target},
        {"$inc": {"balance": -steal}}
    )

    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": steal}}
    )

    rob_cooldown[user_id] = datetime.utcnow()

    await message.reply_text(
        f"💰 Successful robbery!\n\nYou stole {steal} tokens."
    )
  # ================= BANK HEIST =================

HEIST_COOLDOWN = 1800
heist_cooldown = {}

@app.on_message(filters.command("heist"))
async def bank_heist(client, message):

    user_id = message.from_user.id

    if user_id in heist_cooldown:
        diff = datetime.utcnow() - heist_cooldown[user_id]

        if diff < timedelta(seconds=HEIST_COOLDOWN):
            remain = HEIST_COOLDOWN - diff.total_seconds()
            return await message.reply_text(
                f"🏦 Next heist available in {int(remain)} seconds."
            )

    await message.reply_text("🏦 Breaking into the bank vault...")

    await asyncio.sleep(2)

    chance = random.randint(1,100)

    if chance <= 50:
        return await message.reply_text(
            "🚔 Bank security caught you!"
        )

    reward = random.randint(5000,20000)

    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"balance": reward}}
    )

    heist_cooldown[user_id] = datetime.utcnow()

    await message.reply_text(
        f"💰 BANK HEIST SUCCESS!\n\nReward: {reward} tokens"
    )
  # ================= CRIME LEADERBOARD =================

@app.on_message(filters.command("crime_top"))
async def crime_top(client, message):

    users = user_collection.find().sort("balance",-1).limit(10)

    text = "🏆 Top Criminals\n\n"

    rank = 1

    async for user in users:
        text += f"{rank}. {user['id']} — {user.get('balance',0)} coins\n"
        rank += 1

    await message.reply_text(text)
  # ================= POLICE RAID EVENT =================

RAID_COOLDOWN = 900
last_raid = None

@app.on_message(filters.command("raid"))
async def police_raid(client, message):

    global last_raid

    if last_raid:
        diff = datetime.utcnow() - last_raid
        if diff < timedelta(seconds=RAID_COOLDOWN):
            remain = RAID_COOLDOWN - diff.total_seconds()
            return await message.reply_text(
                f"🚔 Next police raid in {int(remain)} seconds."
            )

    await message.reply_text("🚔 Police raid started! Searching criminals...")

    users = user_collection.find()

    raid_text = "🚔 Police Raid Results\n\n"

    async for user in users:

        balance = user.get("balance",0)

        if balance <= 0:
            continue

        fine = int(balance * 0.10)

        await user_collection.update_one(
            {"id": user["id"]},
            {"$inc": {"balance": -fine}}
        )

        raid_text += f"User {user['id']} fined {fine} coins\n"

    last_raid = datetime.utcnow()

    await message.reply_text(raid_text)
