import asyncio
import time
import random
from pyrogram import filters, Client, types as t
from shivu import shivuu as bot
from shivu import collection, user_collection

cooldowns = {}

BONUS_REWARDS = {
    6: 100,
    5: 50,
    4: 20
}

SECRET_DROP_CHANCE = 3  # %

async def fetch_unique_characters(receiver_id, target_rarities=['🟡 Legendary','💮 Exclusive']):
    
    user_data = await user_collection.find_one({'id': receiver_id}) or {"characters": []}
    owned_ids = [c["id"] for c in user_data.get("characters", [])]

    pipeline = [
        {
            "$match": {
                "rarity": {"$in": target_rarities},
                "id": {"$nin": owned_ids}
            }
        },
        {"$sample": {"size": 1}}
    ]

    chars = await collection.aggregate(pipeline).to_list(length=1)
    return chars


async def secret_character():

    pipeline = [
        {"$match": {"rarity": "🔮 Mythic"}},
        {"$sample": {"size": 1}}
    ]

    chars = await collection.aggregate(pipeline).to_list(length=1)
    return chars


async def handle_rewards(user_id, value):

    coins = BONUS_REWARDS.get(value, 0)

    if coins > 0:
        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"coins": coins}},
            upsert=True
        )

    return coins


@bot.on_message(filters.command(["roll","dice"]))
async def roll_command(_, message: t.Message):

    user_id = message.from_user.id
    mention = message.from_user.mention

    # Cooldown
    if user_id in cooldowns:
        remaining = 60 - (time.time() - cooldowns[user_id])

        if remaining > 0:
            return await message.reply_text(
                f"⏳ {mention} wait **{int(remaining)}s** before rolling again!"
            )

    cooldowns[user_id] = time.time()

    suspense = await message.reply_text("🎲 Rolling the **Anime Dice**...")

    await asyncio.sleep(2)

    dice_msg = await bot.send_dice(message.chat.id,"🎲")
    value = dice_msg.dice.value

    await suspense.edit_text(f"🎲 **{mention} rolled {value}!**")

    coins = await handle_rewards(user_id,value)

    # SECRET DROP
    if random.randint(1,100) <= SECRET_DROP_CHANCE:

        char = await secret_character()

        if char:

            await message.reply_photo(
                photo=char[0]["img_url"],
                caption=f"""
🌌 **SECRET MYTHIC DROP**

🍃 Name : {char[0]['name']}
⚜️ Rarity : {char[0]['rarity']}
⛩ Anime : {char[0]['anime']}

🔥 **INSANE LUCK {mention}!**
"""
            )

            await user_collection.update_one(
                {"id": user_id},
                {"$push": {"characters": char[0]}},
                upsert=True
            )

            return

    # JACKPOT
    if value >= 5:

        chars = await fetch_unique_characters(user_id)

        if chars:

            c = chars[0]

            await message.reply_photo(
                photo=c["img_url"],
                caption=f"""
🎉 **JACKPOT DROP**

🍃 Name : {c['name']}
⚜️ Rarity : {c['rarity']}
⛩ Anime : {c['anime']}

💰 Bonus Coins : **{coins}**

✨ Congrats {mention}
"""
            )

            await user_collection.update_one(
                {"id": user_id},
                {"$push": {"characters": c}},
                upsert=True
            )

    elif value >= 3:

        await message.reply_animation(
            animation="https://files.catbox.moe/p62bql.mp4",
            caption=f"✨ Good roll {mention}! Keep trying for jackpot!\n💰 Coins : {coins}"
        )

    else:

        await message.reply_animation(
            animation="https://files.catbox.moe/hn08wr.mp4",
            caption=f"💔 Bad luck {mention}... rolled **{value}**"
        )

    # EXTRA ROLL BONUS
    if value == 6:

        await message.reply_text(
            "🔥 **PERFECT ROLL!**\nYou unlocked a **FREE EXTRA ROLL!**"
        )
