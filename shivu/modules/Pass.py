from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from datetime import datetime, timedelta
import random

from shivu import user_collection, collection, application

AUTHORIZED_USER_ID = 5158013355

PASS_PRICE = 30000
PASS_DURATION = 7
PASS_MULTIPLIER = 1.5


# -----------------------------
# RANDOM CHARACTER
# -----------------------------

async def get_random_character():

    rarities = [
        "🔮 limited edition",
        "🟡 Legendary",
        "🌌 Celestial"
    ]

    rarity = random.choice(rarities)

    pipeline = [
        {"$match": {"rarity": rarity}},
        {"$sample": {"size": 1}}
    ]

    cursor = collection.aggregate(pipeline)
    characters = await cursor.to_list(length=1)

    return characters


# -----------------------------
# USER DATA
# -----------------------------

async def get_user_data(user_id):

    user = await user_collection.find_one({"id": user_id})

    if not user:

        user = {
            "id": user_id,
            "tokens": 0,
            "pass": False,
            "streak": 0,
            "characters": [],
            "pass_details": {
                "expiry": None,
                "last_daily": None,
                "last_weekly": None,
                "total_claims": 0
            }
        }

        await user_collection.insert_one(user)

    return user


# -----------------------------
# PASS COMMAND
# -----------------------------

async def pass_cmd(update: Update, context: CallbackContext):

    user_id = update.effective_user.id
    user = await get_user_data(user_id)

    if not user["pass"]:

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Buy Pass (30k)", callback_data=f"buy:{user_id}")]
        ])

        await update.message.reply_text(
            "🚫 You don't have a pass.\nBuy one to unlock rewards!",
            reply_markup=keyboard
        )

        return

    expiry = user["pass_details"]["expiry"]

    if expiry and datetime.now() > expiry:

        await user_collection.update_one(
            {"id": user_id},
            {"$set": {"pass": False}}
        )

        await update.message.reply_text("❌ Your pass expired.")
        return

    total = user["pass_details"]["total_claims"]

    await update.message.reply_text(
        f"""
🎟 PASS INFO

Owner: {update.effective_user.first_name}

Total Claims: {total}
Expiry: {expiry.strftime("%Y-%m-%d")}
        """
    )


# -----------------------------
# BUY PASS
# -----------------------------

async def button_callback(update: Update, context: CallbackContext):

    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split(":")
    user_id = int(user_id)

    if query.from_user.id != user_id:
        return

    user = await get_user_data(user_id)

    if action == "buy":

        if user["tokens"] < PASS_PRICE:

            await query.message.edit_text("❌ Not enough tokens")
            return

        expiry = datetime.now() + timedelta(days=PASS_DURATION)

        await user_collection.update_one(
            {"id": user_id},
            {
                "$inc": {"tokens": -PASS_PRICE},
                "$set": {
                    "pass": True,
                    "pass_details.expiry": expiry
                }
            }
        )

        await query.message.edit_text("🎉 Pass purchased!")


# -----------------------------
# DAILY CLAIM
# -----------------------------

async def claim_daily(update: Update, context: CallbackContext):

    user_id = update.effective_user.id
    user = await get_user_data(user_id)

    if not user["pass"]:

        await update.message.reply_text("❌ You need a pass")
        return

    last = user["pass_details"]["last_daily"]

    if last and (datetime.now() - last) < timedelta(hours=24):

        await update.message.reply_text("⏳ Daily already claimed")
        return

    reward = random.randint(500, 2000)

    reward = int(reward * PASS_MULTIPLIER)

    characters = await get_random_character()

    if not characters:
        await update.message.reply_text("Character error")
        return

    char = characters[0]

    jackpot = ""

    if random.randint(1, 100) <= 5:

        bonus = 10000

        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"tokens": bonus}}
        )

        jackpot = f"\n🎰 JACKPOT BONUS: {bonus}"

    await user_collection.update_one(
        {"id": user_id},
        {
            "$inc": {"tokens": reward},
            "$set": {"pass_details.last_daily": datetime.now()},
            "$addToSet": {"characters": char},
            "$inc": {"pass_details.total_claims": 1}
        }
    )

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=char["img_url"],
        caption=f"""
🎁 DAILY REWARD

Character: {char['name']}
Anime: {char['anime']}
Rarity: {char['rarity']}

💰 Tokens: {reward}
{jackpot}
"""
    )


# -----------------------------
# WEEKLY CLAIM
# -----------------------------

async def claim_weekly(update: Update, context: CallbackContext):

    user_id = update.effective_user.id
    user = await get_user_data(user_id)

    last = user["pass_details"]["last_weekly"]

    if last and (datetime.now() - last) < timedelta(days=7):

        await update.message.reply_text("❌ Weekly already claimed")
        return

    reward = 5000

    await user_collection.update_one(
        {"id": user_id},
        {
            "$inc": {"tokens": reward},
            "$set": {"pass_details.last_weekly": datetime.now()}
        }
    )

    await update.message.reply_text(
        f"🏆 Weekly reward claimed!\n💰 {reward} tokens"
    )


# -----------------------------
# PASS STATS
# -----------------------------

async def pass_stats(update: Update, context: CallbackContext):

    user_id = update.effective_user.id
    user = await get_user_data(user_id)

    claims = user["pass_details"]["total_claims"]
    chars = len(user.get("characters", []))
    tokens = user["tokens"]

    await update.message.reply_text(
        f"""
📊 PASS STATS

Total Claims: {claims}
Characters: {chars}
Tokens: {tokens}
"""
    )


# -----------------------------
# OWNER RESET
# -----------------------------

async def reset_passes(update: Update, context: CallbackContext):

    if update.effective_user.id != AUTHORIZED_USER_ID:
        return

    await user_collection.update_many(
        {},
        {"$set": {"pass": False}}
    )

    await update.message.reply_text("All passes reset")


# -----------------------------
# HANDLERS
# -----------------------------

application.add_handler(CommandHandler("pass", pass_cmd))
application.add_handler(CommandHandler("claim", claim_daily))
application.add_handler(CommandHandler("weekly", claim_weekly))
application.add_handler(CommandHandler("passstats", pass_stats))
application.add_handler(CommandHandler("rpass", reset_passes))

application.add_handler(
    CallbackQueryHandler(button_callback, pattern="buy:")
)
