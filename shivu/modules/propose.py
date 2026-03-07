from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from shivu import shivuu as bot
from shivu import user_collection, collection
import random
import asyncio
import time

# CONFIG
OWNER_ID = 5158013355
MUST_JOIN = "upper_moon_chat"

PROPOSE_COST = 200000
RETRY_COST = 50000
COOLDOWN = 600
SPAM = 5

WIN_RATE = 5
JACKPOT_CHANCE = 2
MYTHICAL_CHANCE = 1
DOUBLE_DROP = 5

STREAK_LIMIT = 5

# MEMORY
cooldowns = {}
last_used = {}
fail_streak = {}

# IMAGES
ACCEPT_IMG = [
"https://te.legra.ph/file/4fe133737bee4866a3549.png",
"https://te.legra.ph/file/28d46e4656ee2c3e7dd8f.png"
]

REJECT_IMG = [
"https://te.legra.ph/file/d6e784e5cda62ac27541f.png",
"https://te.legra.ph/file/e4e1ba60b4e79359bf9e7.png"
]

# RANDOM CHARACTER
async def get_character():

    pipeline = [
        {"$match": {"rarity": {"$in": ["🟡 Legendary","🟠 Rare"]}}},
        {"$sample": {"size": 1}}
    ]

    data = collection.aggregate(pipeline)
    return await data.to_list(1)


# MYTHICAL CHARACTER
async def get_mythical():

    pipeline = [
        {"$match": {"rarity": "🌌 Mythical"}},
        {"$sample": {"size": 1}}
    ]

    data = collection.aggregate(pipeline)
    return await data.to_list(1)


# PROPOSE COMMAND
@bot.on_message(filters.command("propose"))
async def propose(_, message):

    uid = message.from_user.id
    now = time.time()

    # JOIN CHECK
    try:
        await bot.get_chat_member(MUST_JOIN, uid)
    except UserNotParticipant:
        return await message.reply(
            "Join support group first",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("JOIN", url=f"https://t.me/{MUST_JOIN}")]]
            )
        )

    # SPAM CHECK
    if uid in last_used and now-last_used[uid] < SPAM:
        return await message.reply("🚨 Slow down.")

    # COOLDOWN
    if uid in cooldowns and now-cooldowns[uid] < COOLDOWN:
        remain = int(COOLDOWN-(now-cooldowns[uid]))
        return await message.reply(f"⏳ Wait {remain}s")

    data = await user_collection.find_one({"id":uid}) or {}
    bal = data.get("balance",0)

    if bal < PROPOSE_COST:
        return await message.reply("⚠️ Need 200000 tokens")

    # PAY
    await user_collection.update_one(
        {"id":uid},
        {"$inc":{"balance":-PROPOSE_COST}}
    )

    cooldowns[uid] = now
    last_used[uid] = now

    msg = await message.reply("💍 Preparing proposal...")
    await asyncio.sleep(1)

    await msg.edit("💞 Extending the ring...")
    await asyncio.sleep(1)

    await msg.edit("❤️ Asking the question...")
    await asyncio.sleep(2)

    luck = random.randint(1,100)
    jackpot = random.randint(1,100)

    streak = fail_streak.get(uid,0)

    # MYTHICAL DROP
    if random.randint(1,200) <= MYTHICAL_CHANCE:

        char = await get_mythical()

        if char:

            char = char[0]

            await user_collection.update_one(
                {"id":uid},
                {"$push":{"characters":char}}
            )

            await message.reply_photo(
                char["img_url"],
                caption=f"""
🌌 MYTHICAL LOVE

Name: {char['name']}
Anime: {char['anime']}
Rarity: {char['rarity']}
"""
            )

            return

    # NORMAL WIN
    if luck <= WIN_RATE or streak >= STREAK_LIMIT:

        char = await get_character()

        if char:

            char = char[0]

            await user_collection.update_one(
                {"id":uid},
                {
                    "$push":{"characters":char},
                    "$inc":{"proposal_win":1}
                }
            )

            fail_streak[uid] = 0

            await message.reply_photo(
                char["img_url"],
                caption=f"""
💍 PROPOSAL ACCEPTED

Name: {char['name']}
Anime: {char['anime']}
Rarity: {char['rarity']}
"""
            )

            # DOUBLE DROP
            if random.randint(1,100) <= DOUBLE_DROP:

                await user_collection.update_one(
                    {"id":uid},
                    {"$push":{"characters":char}}
                )

                await message.reply("💎 DOUBLE CHARACTER DROP!")

            # JACKPOT
            if jackpot <= JACKPOT_CHANCE:

                coins = random.randint(500000,1000000)

                await user_collection.update_one(
                    {"id":uid},
                    {"$inc":{"balance":coins}}
                )

                await message.reply(f"🎰 JACKPOT!\nYou won {coins} coins!")

    else:

        fail_streak[uid] = streak+1

        await user_collection.update_one(
            {"id":uid},
            {"$inc":{"proposal_lose":1}}
        )

        await message.reply_photo(
            random.choice(REJECT_IMG),
            caption="💔 Proposal rejected"
        )

    await message.reply(
        "Try again?",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Retry (50k)",callback_data="retry_propose")]]
        )
    )


# RETRY
@bot.on_callback_query(filters.regex("retry_propose"))
async def retry(_,query):

    uid = query.from_user.id

    data = await user_collection.find_one({"id":uid}) or {}
    bal = data.get("balance",0)

    if bal < RETRY_COST:
        return await query.answer("Not enough coins",show_alert=True)

    await user_collection.update_one(
        {"id":uid},
        {"$inc":{"balance":-RETRY_COST}}
    )

    await query.answer("Retrying...")

    await propose(_,query.message)


# STATS
@bot.on_message(filters.command("proposestats"))
async def stats(_,message):

    uid = message.from_user.id

    data = await user_collection.find_one({"id":uid}) or {}

    win = data.get("proposal_win",0)
    lose = data.get("proposal_lose",0)

    total = win+lose

    rate = 0
    if total>0:
        rate = round((win/total)*100)

    await message.reply(f"""
💍 Proposal Stats

Total: {total}
❤️ Wins: {win}
💔 Losses: {lose}
🔥 Win Rate: {rate}%
""")


# LEADERBOARD
@bot.on_message(filters.command("proposalboard"))
async def leaderboard(_,message):

    users = user_collection.find().sort("proposal_win",-1).limit(10)

    text = "🏆 Proposal Leaderboard\n\n"
    rank = 1

    async for u in users:

        text += f"{rank}. {u.get('proposal_win',0)} wins\n"
        rank += 1

    await message.reply(text)


# OWNER COOLDOWN RESET
@bot.on_message(filters.command("cd"))
async def reset_cd(_,message):

    if message.from_user.id != OWNER_ID:
        return

    if not message.reply_to_message:
        return await message.reply("Reply to user")

    uid = message.reply_to_message.from_user.id
    cooldowns.pop(uid,None)

    await message.reply("✅ Cooldown reset")
