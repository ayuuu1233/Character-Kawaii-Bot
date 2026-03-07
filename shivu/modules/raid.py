import time
import asyncio
import random
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from shivu import shivuu as app
from shivu import user_collection

MUST_JOIN = "upper_moon_chat"
LOG_GROUP_CHAT_ID = -1001945969614

# ---------------- BEAST POWER SYSTEM ---------------- #

BEAST_POWER = {
    "wolf": 5,
    "tiger": 8,
    "dragon": 15,
    "phoenix": 20
}

def get_beast_power(user):

    beasts = user.get("beasts", [])

    if not beasts:
        return 0

    beast = str(beasts[0]).lower()

    return BEAST_POWER.get(beast, 3)

# ---------------- GEM DATA ---------------- #

gem_prices = {
    "Wood": {"price": 2, "emoji": "🪵"},
    "Iron": {"price": 5, "emoji": "🔩"},
    "Silver": {"price": 7, "emoji": "🥈"},
    "Gold": {"price": 10, "emoji": "🥇"},
    "Diamond": {"price": 20, "emoji": "💎"},
    "Platinum": {"price": 25, "emoji": "🏆"},
    "Emerald": {"price": 30, "emoji": "🟢"},
    "Ruby": {"price": 35, "emoji": "🔴"},
    "Sapphire": {"price": 40, "emoji": "🔵"},
    "Amethyst": {"price": 45, "emoji": "🟣"},
    "Obsidian": {"price": 50, "emoji": "⚫"}
}

# weighted drop rates
gem_drop_rates = {
    "Wood": 40,
    "Iron": 30,
    "Silver": 15,
    "Gold": 8,
    "Diamond": 4,
    "Emerald": 1.5,
    "Ruby": 0.8,
    "Sapphire": 0.5,
    "Amethyst": 0.15,
    "Platinum": 0.04,
    "Obsidian": 0.01
}

cooldown = 60
last_hunt = {}

# ---------------- UTILS ---------------- #

async def send_log(text):
    try:
        await app.send_message(LOG_GROUP_CHAT_ID, text)
    except:
        pass


def random_gem():
    gems = list(gem_drop_rates.keys())
    weights = list(gem_drop_rates.values())
    return random.choices(gems, weights=weights, k=1)[0]


# ---------------- INVENTORY ---------------- #

@app.on_message(filters.command("sbag"))
async def inventory(client, message: Message):

    user = await user_collection.find_one({"id": message.from_user.id})

    if not user or "gems" not in user:
        return await message.reply("❌ You have no items.")

    text = "🎒 **YOUR INVENTORY**\n\n"

    for gem, amount in user["gems"].items():
        emoji = gem_prices.get(gem, {}).get("emoji", "❓")
        text += f"{emoji} **{gem}** × {amount}\n"

    await message.reply(text)


# ---------------- SELL ---------------- #

@app.on_message(filters.command("sellitem"))
async def sell_item(client, message: Message):

    args = message.text.split()

    if len(args) != 3:
        return await message.reply("Usage:\n`/sellitem gem amount`")

    gem = args[1].capitalize()
    amount = int(args[2])

    if gem not in gem_prices:
        return await message.reply("❌ Invalid item")

    user = await user_collection.find_one({"id": message.from_user.id})

    if not user or user.get("gems", {}).get(gem, 0) < amount:
        return await message.reply("❌ Not enough items")

    price = gem_prices[gem]["price"] * amount

    await user_collection.update_one(
        {"id": message.from_user.id},
        {
            "$inc": {
                f"gems.{gem}": -amount,
                "tokens": price
            }
        }
    )

    await message.reply(
        f"💰 Sold **{amount} {gem}** for **{price} tokens**"
    )



# ---------------- HUNT SYSTEM ---------------- #

@app.on_message(filters.command("hunt"))
async def hunt(client, message: Message):

    user_id = message.from_user.id
    now = time.time()

    # cooldown check
    if user_id in last_hunt:
        left = cooldown - (now - last_hunt[user_id])
        if left > 0:
            return await message.reply(f"⏳ Wait {int(left)}s before hunting again.")

    last_hunt[user_id] = now

    # must join check
    try:
        await app.get_chat_member(MUST_JOIN, user_id)
    except UserNotParticipant:
        return await message.reply(
            "🔒 Join support group first",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Join", url=f"https://t.me/{MUST_JOIN}")]]
            )
        )

    # get user data
    user = await user_collection.find_one({"id": user_id})

    if not user or not user.get("beasts"):
        return await message.reply("🐾 You need a beast first (/beastshop)")

    # animated hunt message
    msg = await message.reply("🔎 Searching dungeon.")

    for i in ["..", "...", "...."]:
        await asyncio.sleep(0.6)
        await msg.edit(f"🔎 Searching dungeon{i}")

    await asyncio.sleep(0.5)

    # ---------------- PORTAL EVENT ---------------- #

    if random.randint(1,100) <= 5:

        portal_gems = random.randint(50,120)

        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"gems.Diamond": portal_gems}},
            upsert=True
        )

        return await msg.edit(
            f"""
🌌 **PORTAL DUNGEON OPENED**

You entered a hidden dungeon!

💎 Diamond × {portal_gems}
"""
        )
      
       # ---------------- LEGENDARY DROP ---------------- #

if random.randint(1,100) <= 2:

    legendary_gems = random.randint(40,80)

    await user_collection.update_one(
        {"id": user_id},
        {
            "$inc": {
                "gems.Diamond": legendary_gems,
                "mythic_gems": 1,
                "hunt_points": 3
            }
        },
        upsert=True
    )

    return await msg.edit(
        f"""
✨ **LEGENDARY DROP FOUND**

💎 Diamond × {legendary_gems}
🔥 Mythic Gem × 1

You found a hidden treasure chest!
"""
    )

    # ---------------- NORMAL HUNT ---------------- #

    gem = random_gem()

    amount = random.randint(5,15)

    # 🔥 Beast Power System
    beast_bonus = get_beast_power(user)
    amount += beast_bonus

    await user_collection.update_one(
        {"id": user_id},
        {
            "$inc": {
                f"gems.{gem}": amount,
                "hunt_points": 1
            }
        },
        upsert=True
    )

    emoji = gem_prices.get(gem, {}).get("emoji", "💎")

    await msg.edit(
        f"""
🏹 **HUNT SUCCESS**

{emoji} **{gem} × {amount}**

🐾 Beast Power: +{beast_bonus}
"""
    )
  
  
  # =========================
# BOSS RAID SYSTEM
# =========================

RAID_BOSSES = [
    {"name": "Obsidian Dragon", "hp": 2500},
    {"name": "Shadow Titan", "hp": 3000},
    {"name": "Abyss Demon", "hp": 3500}
]

active_raid = None


@bot.on_message(filters.command(["startraid"]))
async def start_raid(client, message):

    global active_raid

    if active_raid:
        return await message.reply("⚠️ A raid is already active!")

    boss = random.choice(RAID_BOSSES)

    active_raid = {
        "name": boss["name"],
        "hp": boss["hp"],
        "players": {}
    }

    await message.reply(
        f"""
👹 **RAID BOSS SPAWNED**

Boss: **{boss['name']}**
HP: **{boss['hp']}**

⚔ Use /raidattack to fight!
"""
    )


@bot.on_message(filters.command(["raidattack"]))
async def raid_attack(client, message):

    global active_raid

    if not active_raid:
        return await message.reply("❌ No active raid!")

    user_id = message.from_user.id

    damage = random.randint(30,120)

    active_raid["hp"] -= damage

    active_raid["players"][user_id] = \
        active_raid["players"].get(user_id,0) + damage

    if active_raid["hp"] <= 0:

        text = f"🏆 **{active_raid['name']} defeated!**\n\n"

        for uid, dmg in active_raid["players"].items():

            reward = dmg // 15

            await user_collection.update_one(
                {"id": uid},
                {"$inc": {"gems.Diamond": reward}}
            )

            text += f"`{uid}` dealt **{dmg} damage**\n"

        await message.reply(text)

        active_raid = None
        return

    await message.reply(
        f"""
⚔ Damage: **{damage}**

👹 Boss HP left: **{active_raid['hp']}**
"""
    )

    # critical drop
    if random.randint(1, 100) <= 5:
        amount *= 3

        critical = True
    else:
        critical = False

    await user_collection.update_one(
        {"id": user_id},
        {
            "$inc": {
                f"gems.{gem}": amount,
                "hunt_count": 1
            }
        },
        upsert=True
    )

    emoji = gem_prices[gem]["emoji"]

    text = f"🎉 You found\n\n{emoji} **{gem} × {amount}**"

    if critical:
        text += "\n\n✨ **CRITICAL DROP!**"

    await message.reply(text)

    await send_log(f"{user_id} hunted {gem} x{amount}")


# ---------------- LEADERBOARD ---------------- #

@app.on_message(filters.command("hunttop"))
async def hunt_top(client, message: Message):

    users = user_collection.find().sort("hunt_count", -1).limit(10)

    text = "🏆 **TOP HUNTERS**\n\n"

    i = 1
    async for user in users:

        hunts = user.get("hunt_count", 0)

        text += f"{i}. `{user['id']}` — {hunts} hunts\n"

        i += 1

    await message.reply(text)
  
owner_id = 5158013355

@bot.on_message(filters.user(owner_id) & filters.command(["hreset"]))
async def reset_gems_command(_: bot, message: t.Message):
    # Check if the command is a reply to a user's message
    if message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
        # Reset gems for the specified user
        await user_collection.update_one({'id': user_id}, {'$unset': {'gems': 1}})
        await message.reply_text(f"loot reset for user {user_id}.")
    else:
        await message.reply_text("Please reply to the user's message to reset their loot.")

AUTHORIZED_USER_ID = 5158013355

@bot.on_message(filters.command(["itemreset"]))
async def item_reset_command(client, message):
    user_id = message.from_user.id
    if user_id != AUTHORIZED_USER_ID:
        await message.reply_text("You are not authorized to use this command.")
        return

    await user_collection.update_many({}, {'$set': {'gems': {}}})
    await message.reply_text("All users' items have been reset to zero.")
