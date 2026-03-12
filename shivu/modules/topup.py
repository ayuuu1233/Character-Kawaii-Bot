from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from shivu import shivuu as app
import random
import json
import os

# -------------------- CONSTANTS -------------------- #
FREE_TOPUP_REWARD = 500
WEEKLY_TOPUP_COST = 1200
WEEKLY_REWARDS = {
    'daily': {'wealth': 500, 'tokens': 0, 'character_rarity': '🟠 Rare'},
    'weekly_end': {'wealth': 1000, 'tokens': 2000, 'character_rarity': '🟡 Legendary'}
}
MONTHLY_TOPUP_COST = 3000
MONTHLY_REWARDS = {
    'weekly': {'wealth': 1000, 'tokens': 1000, 'character_rarity': '🟡 Legendary'},
    'month_end': {'wealth': 2000, 'tokens': 3000, 'character_rarity': '🔮 Limited Edition'}
}

USERS_FILE = "users.json"

# -------------------- USERS DATA -------------------- #
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
else:
    users = {}

def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, default=str)

def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in users:
        users[user_id] = {
            'balance': 0,
            'wealth': 0,
            'free_topup_claimed': False,
            'weekly_topup': {'active': False, 'start_date': None, 'last_claim_date': None, 'bonus_claimed': False},
            'monthly_topup': {'active': False, 'start_date': None, 'last_claim_date': None, 'bonus_claimed': False}
        }
    return users[user_id]

# -------------------- CHARACTERS -------------------- #
def get_random_character(rarity):
    characters = {
        '🟠 Rare': {'name': 'Rare Hero', 'img_url': 'https://example.com/rare.jpg'},
        '🟡 Legendary': {'name': 'Legendary Hero', 'img_url': 'https://example.com/legendary.jpg'},
        '🔮 Limited Edition': {'name': 'Limited Hero', 'img_url': 'https://example.com/limited.jpg'}
    }
    return characters[rarity]

# -------------------- COMMAND: /topup -------------------- #
@app.on_message(filters.command("topup"))
async def topup_cmd(client, message):
    user_id = message.from_user.id
    get_user_data(user_id)

    keyboard = [
        [InlineKeyboardButton("Free Top-Up 🎁", callback_data=f"free_topup:{user_id}")],
        [InlineKeyboardButton("Weekly Top-Up 🗓️", callback_data=f"weekly_topup:{user_id}")],
        [InlineKeyboardButton("Monthly Top-Up 🗓️", callback_data=f"monthly_topup:{user_id}")],
        [InlineKeyboardButton("Claim Weekly Daily Reward 🏆", callback_data=f"claim_weekly:{user_id}")],
        [InlineKeyboardButton("Claim Monthly Weekly Reward 🏅", callback_data=f"claim_monthly:{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply(
        "<b>❰ 𝗧 𝗢 𝗣 𝗨 𝗣 𝗠 𝗘 𝗡 𝗨 ❱</b>\n\n"
        "1️⃣ Free Top-Up: 500 tokens.\n"
        "2️⃣ Weekly Top-Up: 1200 tokens. Rewards daily + end of week bonus.\n"
        "3️⃣ Monthly Top-Up: 3000 tokens. Rewards weekly + month-end bonus.\n\n"
        "Choose your option below!",
        parse_mode="html",
        reply_markup=reply_markup
    )

# -------------------- CALLBACK HANDLER -------------------- #
@app.on_callback_query(filters.regex(".*"))
async def button_callback(client, query):
    user_id = query.from_user.id
    action, target_user_id = query.data.split(":")
    target_user_id = int(target_user_id)

    if user_id != target_user_id:
        await query.answer("This button is not for you!", show_alert=True)
        return

    user = get_user_data(user_id)
    now = datetime.now()

    # ---------- FREE TOP-UP ---------- #
    if action == "free_topup":
        if user['free_topup_claimed']:
            await query.answer("You already claimed the Free Top-Up!", show_alert=True)
            return
        user['balance'] += FREE_TOPUP_REWARD
        user['free_topup_claimed'] = True
        save_users()
        await query.message.edit_text(f"🎉 Free Top-Up claimed! +{FREE_TOPUP_REWARD} tokens.")

    # ---------- WEEKLY TOP-UP ---------- #
    elif action == "weekly_topup":
        if user['balance'] < WEEKLY_TOPUP_COST:
            await query.answer("Not enough tokens!", show_alert=True)
            return
        if user['weekly_topup']['active']:
            await query.answer("Weekly Top-Up already active!", show_alert=True)
            return
        user['balance'] -= WEEKLY_TOPUP_COST
        user['weekly_topup']['active'] = True
        user['weekly_topup']['start_date'] = now.isoformat()
        user['weekly_topup']['last_claim_date'] = None
        user['weekly_topup']['bonus_claimed'] = False
        save_users()
        await query.message.edit_text("🗓️ Weekly Top-Up activated! Claim daily rewards.")

    # ---------- MONTHLY TOP-UP ---------- #
    elif action == "monthly_topup":
        if user['balance'] < MONTHLY_TOPUP_COST:
            await query.answer("Not enough tokens!", show_alert=True)
            return
        if user['monthly_topup']['active']:
            await query.answer("Monthly Top-Up already active!", show_alert=True)
            return
        user['balance'] -= MONTHLY_TOPUP_COST
        user['monthly_topup']['active'] = True
        user['monthly_topup']['start_date'] = now.isoformat()
        user['monthly_topup']['last_claim_date'] = None
        user['monthly_topup']['bonus_claimed'] = False
        save_users()
        await query.message.edit_text("🗓️ Monthly Top-Up activated! Claim weekly rewards.")

    # ---------- CLAIM WEEKLY DAILY ---------- #
    elif action == "claim_weekly":
        if not user['weekly_topup']['active']:
            await query.answer("No active Weekly Top-Up!", show_alert=True)
            return

        # Daily claim check
        last_claim = user['weekly_topup']['last_claim_date']
        if last_claim and (now - datetime.fromisoformat(last_claim)).days < 1:
            await query.answer("⏳ Already claimed today!", show_alert=True)
            return

        user['balance'] += WEEKLY_REWARDS['daily']['wealth']
        user['weekly_topup']['last_claim_date'] = now.isoformat()
        char = get_random_character(WEEKLY_REWARDS['daily']['character_rarity'])

        # ---------- Auto weekly_end bonus ----------
        start_date = datetime.fromisoformat(user['weekly_topup']['start_date'])
        if (now - start_date).days >= 7 and not user['weekly_topup'].get('bonus_claimed', False):
            user['balance'] += WEEKLY_REWARDS['weekly_end']['wealth']
            user['weekly_topup']['bonus_claimed'] = True
            bonus_char = get_random_character(WEEKLY_REWARDS['weekly_end']['character_rarity'])
            await query.message.reply_photo(
                bonus_char['img_url'],
                caption=f"🎉 Weekly Top-Up Bonus!\n+{WEEKLY_REWARDS['weekly_end']['wealth']} tokens\nYou got: {bonus_char['name']} ({WEEKLY_REWARDS['weekly_end']['character_rarity']})"
            )

        save_users()
        await query.message.reply_photo(
            char['img_url'],
            caption=f"🎁 Daily Weekly Top-Up claimed!\n+{WEEKLY_REWARDS['daily']['wealth']} tokens\nYou got: {char['name']} ({WEEKLY_REWARDS['daily']['character_rarity']})"
        )

    # ---------- CLAIM MONTHLY WEEKLY ---------- #
    elif action == "claim_monthly":
        if not user['monthly_topup']['active']:
            await query.answer("No active Monthly Top-Up!", show_alert=True)
            return

        # Weekly claim check
        last_claim = user['monthly_topup']['last_claim_date']
        if last_claim and (now - datetime.fromisoformat(last_claim)).days < 7:
            await query.answer("⏳ Already claimed this week!", show_alert=True)
            return

        user['balance'] += MONTHLY_REWARDS['weekly']['wealth']
        user['monthly_topup']['last_claim_date'] = now.isoformat()
        char = get_random_character(MONTHLY_REWARDS['weekly']['character_rarity'])

        # ---------- Auto month_end bonus ----------
        start_date = datetime.fromisoformat(user['monthly_topup']['start_date'])
        if (now - start_date).days >= 30 and not user['monthly_topup'].get('bonus_claimed', False):
            user['balance'] += MONTHLY_REWARDS['month_end']['wealth']
            user['monthly_topup']['bonus_claimed'] = True
            bonus_char = get_random_character(MONTHLY_REWARDS['month_end']['character_rarity'])
            await query.message.reply_photo(
                bonus_char['img_url'],
                caption=f"🎉 Monthly Top-Up Bonus!\n+{MONTHLY_REWARDS['month_end']['wealth']} tokens\nYou got: {bonus_char['name']} ({MONTHLY_REWARDS['month_end']['character_rarity']})"
            )

        save_users()
        await query.message.reply_photo(
            char['img_url'],
            caption=f"🎁 Monthly Weekly Reward claimed!\n+{MONTHLY_REWARDS['weekly']['wealth']} tokens\nYou got: {char['name']} ({MONTHLY_REWARDS['weekly']['character_rarity']})"
  )
