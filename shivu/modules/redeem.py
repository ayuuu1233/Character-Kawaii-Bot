from pyrogram import Client, filters
import random
import string
import time
from datetime import datetime

from shivu import user_collection, collection
from shivu import shivuu as app


generated_codes = {}
generated_waifus = {}

# sudo users
sudo_user_ids = {5158013355}

# cooldown
redeem_cooldown = {}

REDEEM_DELAY = 5


def generate_random_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


def format_amount(amount):
    return f"{amount:,.0f}" if float(amount).is_integer() else f"{amount:,.2f}"


# ---------------- GENERATE TOKEN CODE ---------------- #

@app.on_message(filters.command("gen"))
async def generate_code(client, message):

    if message.from_user.id not in sudo_user_ids:
        return await message.reply_text(
            "🚫 Only **sudo users** can generate reward codes."
        )

    try:
        amount = float(message.command[1])
        quantity = int(message.command[2])
    except:
        return await message.reply_text(
            "Usage:\n`/gen amount quantity`\n\nExample:\n`/gen 100000 5`"
        )

    code = generate_random_code()

    generated_codes[code] = {
        "amount": amount,
        "quantity": quantity,
        "total_claims": 0,
        "claimed_by": {},
        "expiry": time.time() + 86400
    }

    await message.reply_text(
        f"""
✨ **Reward Code Generated**

🔑 Code: `{code}`
💰 Amount: Ŧ `{format_amount(amount)}`
📦 Quantity: `{quantity}`
⏳ Expires: 24 hours

Redeem using:
/redeem {code}
"""
    )


# ---------------- REDEEM TOKEN CODE ---------------- #

@app.on_message(filters.command("redeem"))
async def redeem_code(client, message):

    user_id = message.from_user.id

    if user_id in redeem_cooldown:
        if time.time() - redeem_cooldown[user_id] < REDEEM_DELAY:
            return await message.reply_text(
                "⏳ Slow down! Try again in a few seconds."
            )

    redeem_cooldown[user_id] = time.time()

    if len(message.command) < 2:
        return await message.reply_text("Usage:\n`/redeem CODE`")

    code = message.command[1]

    if code not in generated_codes:
        return await message.reply_text("❌ Invalid or expired code.")

    code_data = generated_codes[code]

    if time.time() > code_data["expiry"]:
        del generated_codes[code]
        return await message.reply_text("⌛ This code has expired.")

    if code_data["total_claims"] >= code_data["quantity"]:
        return await message.reply_text("⚠️ This code is fully redeemed.")

    user_claims = code_data["claimed_by"].get(user_id, 0)

    if user_claims >= 2:
        return await message.reply_text(
            "🚫 You already redeemed this code **2 times**."
        )

    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"tokens": code_data["amount"]}},
        upsert=True
    )

    code_data["claimed_by"][user_id] = user_claims + 1
    code_data["total_claims"] += 1

    await message.reply_text(
        f"""
🎉 **Redeem Successful**

💰 Received: Ŧ `{format_amount(code_data['amount'])}`

Use `/tokens` to check your balance.
"""
    )


# ---------------- GENERATE WAIFU CODE ---------------- #

@app.on_message(filters.command("wgen"))
async def generate_waifu(client, message):

    if message.from_user.id not in sudo_user_ids:
        return await message.reply_text(
            "🚫 Only sudo users can generate waifu codes."
        )

    try:
        char_id = message.command[1]
        quantity = int(message.command[2])
    except:
        return await message.reply_text(
            "Usage:\n`/wgen character_id quantity`\nExample:\n`/wgen 56 1`"
        )

    waifu = await collection.find_one({"id": char_id})

    if not waifu:
        return await message.reply_text("❌ Waifu not found.")

    code = generate_random_code()

    generated_waifus[code] = {
        "waifu": waifu,
        "quantity": quantity,
        "claimed_by": {}
    }

    await message.reply_photo(
        waifu["img_url"],
        caption=f"""
🌸 **Waifu Drop**

🔑 Code: `{code}`

👤 Name: {waifu['name']}
⭐ Rarity: {waifu['rarity']}
📦 Quantity: {quantity}

Redeem using:
/wredeem {code}
"""
    )


# ---------------- REDEEM WAIFU ---------------- #

@app.on_message(filters.command("wredeem"))
async def redeem_waifu(client, message):

    user_id = message.from_user.id

    if len(message.command) < 2:
        return await message.reply_text("Usage:\n`/wredeem CODE`")

    code = message.command[1]

    if code not in generated_waifus:
        return await message.reply_text("❌ Invalid waifu code.")

    data = generated_waifus[code]

    if data["quantity"] <= 0:
        return await message.reply_text("⚠️ All waifus claimed.")

    user_claims = data["claimed_by"].get(user_id, 0)

    if user_claims >= 2:
        return await message.reply_text(
            "🚫 You already claimed this waifu **2 times**."
        )

    waifu = data["waifu"]

    await user_collection.update_one(
        {"id": user_id},
        {"$push": {"characters": waifu}},
        upsert=True
    )

    data["quantity"] -= 1
    data["claimed_by"][user_id] = user_claims + 1

    if data["quantity"] <= 0:
        del generated_waifus[code]

    await message.reply_photo(
        waifu["img_url"],
        caption=f"""
✨ **New Companion Acquired**

👤 Name: {waifu['name']}
⭐ Rarity: {waifu['rarity']}
🎌 Anime: {waifu['anime']}

Take good care of her!
"""
    )
