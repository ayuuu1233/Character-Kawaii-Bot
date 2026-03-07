from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shivu import shivuu as bot
from shivu import user_collection, collection
from datetime import datetime, timedelta
import asyncio
import random
from pyrogram.enums import ChatMemberStatus

OWNER_ID = 5158013355
DEVS = (5158013355,)

SUPPORT_CHAT_ID = -1001945969614
CHANNEL_ID = -1002596866659
COMMUNITY_GROUP = -1002291490259

keyboard_all = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎭 Official Group", url="https://t.me/upper_moon_chat")],
    [InlineKeyboardButton("📢 Official Channel", url="https://t.me/kawaiii_99")],
    [InlineKeyboardButton("🌟 Community Groups", url="https://t.me/KK_CUTIES")]
])


async def check_membership(user_id):

    valid = [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER
    ]

    try:
        g = await bot.get_chat_member(SUPPORT_CHAT_ID, user_id)
        c = await bot.get_chat_member(CHANNEL_ID, user_id)
        com = await bot.get_chat_member(COMMUNITY_GROUP_ID, user_id)

        return (
            g.status in valid,
            c.status in valid,
            com.status in valid
        )

    except:
        return False, False, False


async def get_unique_character(user_id):

    user = await user_collection.find_one({'id': user_id})

    owned = []
    if user:
        owned = [c['id'] for c in user.get('characters', [])]

    pipeline = [
        {'$match': {'id': {'$nin': owned}}},
        {'$sample': {'size': 1}}
    ]

    cursor = collection.aggregate(pipeline)
    chars = await cursor.to_list(1)

    if chars:
        return chars[0]

    cursor = collection.aggregate([{'$sample': {'size': 1}}])
    chars = await cursor.to_list(1)

    return chars[0] if chars else None


@bot.on_message(filters.command("wclaim"))
async def claim(_, message):

    user_id = message.from_user.id
    mention = message.from_user.mention

    anim = await message.reply_text(
        "✨ **Processing Claim...**\n"
        "▰▱▱▱▱▱"
    )

    await asyncio.sleep(1)

    await anim.edit_text(
        "🔎 **Searching Characters...**\n"
        "▰▰▰▱▱▱"
    )

    await asyncio.sleep(1)

    if user_id not in DEVS and user_id != OWNER_ID:

        g, c, com = await check_membership(user_id)

        if not g or not c or not com:

            await anim.delete()

            return await message.reply_text(
                "⚠️ **Join all official platforms first!**",
                reply_markup=keyboard_all
            )

    user = await user_collection.find_one({'id': user_id})

    if not user:

        user = {
            'id': user_id,
            'characters': [],
            'last_claim_time': None,
            'claim_streak': 0
        }

        await user_collection.insert_one(user)

    now = datetime.utcnow()
    last = user.get("last_claim_time")

    if last and last.date() == now.date():

        cooldown = last + timedelta(hours=24)
        remaining = cooldown - now

        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60

        await anim.delete()

        return await message.reply_text(
            f"⏳ **Already Claimed Today!**\n\n"
            f"Next claim in **{hours}h {minutes}m**"
        )

    streak = user.get("claim_streak", 0)

    if last and (now.date() - last.date()).days == 1:
        streak += 1
    else:
        streak = 1

    await user_collection.update_one(
        {'id': user_id},
        {'$set': {
            'last_claim_time': now,
            'claim_streak': streak
        }}
    )

    jackpot = random.randint(1,100) == 1
    shiny = random.randint(1,50) == 1

    claim_count = 3 if jackpot else 1

    characters = []

    for _ in range(claim_count):

        char = await get_unique_character(user_id)

        if char:
            characters.append(char)

            await user_collection.update_one(
                {'id': user_id},
                {'$push': {'characters': char}}
            )

    await anim.edit_text("🎁 **Reward Found!**")
    await asyncio.sleep(1)
    await anim.delete()

    for char in characters:

        caption = (
            f"🎉 **{mention} claimed a character!**\n\n"
            f"🎭 Name: `{char['name']}`\n"
            f"⚜️ Rarity: `{char['rarity']}`\n"
            f"⛩ Anime: `{char['anime']}`\n\n"
            f"🔥 Streak: `{streak}` days"
        )

        if shiny:
            caption += "\n\n✨ **SHINY VERSION!**"

        if jackpot:
            caption += "\n\n💎 **JACKPOT CLAIM!**"

        await message.reply_photo(
            photo=char['img_url'],
            caption=caption
)
