import random
import time
import asyncio
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from shivu import application, user_collection

cooldowns = {}
COOLDOWN = 10
CHALLENGES = {}

TEAMS = ["Team Z","Team V","Team X","Team Y","Team W"]

PLAYERS = [
"Isagi Yoichi",
"Rin Itoshi",
"Nagi Seishiro",
"Bachira Meguru",
"Barou Shoei"
]

BOSSES = [
"👑 Rin Itoshi",
"🔥 Kaiser",
"⚡ Loki",
"💀 Ego Monster"
]

GIFS = {
"win":"https://files.catbox.moe/9fk6tq.gif",
"lose":"https://files.catbox.moe/h8zv61.gif",
"draw":"https://files.catbox.moe/7jxi98.gif"
}


def get_rank(xp):

    if xp < 50:
        return "🥉 Rookie Striker"
    elif xp < 150:
        return "🥈 Elite Striker"
    elif xp < 300:
        return "🥇 Ego Monster"
    else:
        return "👑 Blue Lock King"


async def get_user(user_id):

    user = await user_collection.find_one({"id": user_id})

    if not user:
        await user_collection.insert_one({
            "id": user_id,
            "xp": 0,
            "goals": 0,
            "players": [],
            "ego": 0
        })

        user = await user_collection.find_one({"id": user_id})

    return user


async def check_cooldown(user_id, message):

    last = cooldowns.get(user_id)

    if last and time.time() - last < COOLDOWN:

        wait = int(COOLDOWN - (time.time() - last))
        await message.reply_text(f"⏱ Wait {wait}s before playing again")

        return False

    return True


# ⚽ SOLO MATCH
async def football(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message
    user_id = msg.from_user.id

    if not await check_cooldown(user_id, msg):
        return

    user = await get_user(user_id)

    team = random.choice(TEAMS)
    enemy = random.choice([x for x in TEAMS if x != team])

    await msg.reply_text("⚽ Match Starting...")
    await asyncio.sleep(1)

    await msg.reply_text(f"🏟 {team} vs {enemy}")
    await asyncio.sleep(2)

    result = random.choice(["win","lose","draw"])

    if result == "win":

        xp = random.randint(5,10)
        goals = 1
        text = f"⚽ GOAL!\n{team} defeated {enemy}\n\n+{xp} XP"

    elif result == "lose":

        xp = 1
        goals = 0
        text = f"🛑 Blocked!\n{enemy} wins\n\n+{xp} XP"

    else:

        xp = 3
        goals = 0
        text = f"🤝 Draw Match\n\n+{xp} XP"

    await msg.reply_animation(
        animation=GIFS[result],
        caption=text
    )

    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"xp": xp, "goals": goals}}
    )

    cooldowns[user_id] = time.time()


# ⚔ CHALLENGE
async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("Usage: /challenge @username")
        return

    challenger = update.effective_user
    target = context.args[0].replace("@","")

    CHALLENGES[target] = challenger.id

    await update.message.reply_text(
        f"⚔ {challenger.first_name} challenged @{target}!\nUse /accept"
    )


async def accept(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if user.username not in CHALLENGES:
        return

    challenger = CHALLENGES[user.username]

    del CHALLENGES[user.username]

    winner = random.choice([challenger, user.id])

    xp = 15

    await user_collection.update_one(
        {"id": winner},
        {"$inc": {"xp": xp, "goals": 1}}
    )

    await update.message.reply_text("⚽ PvP match finished!")


# 🏆 RANK
async def footballrank(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    user = await get_user(user_id)

    rank = get_rank(user["xp"])

    await update.message.reply_text(
        f"⚽ Blue Lock Rank\n\nXP: {user['xp']}\nGoals: {user['goals']}\nRank: {rank}"
    )


# 📊 LEADERBOARD
async def footballlb(update: Update, context: ContextTypes.DEFAULT_TYPE):

    users = user_collection.find().sort("goals",-1).limit(10)

    text = "🏆 Blue Lock Leaderboard\n\n"

    pos = 1

    async for u in users:

        text += f"{pos}. {u['id']} — {u.get('goals',0)} goals\n"
        pos += 1

    await update.message.reply_text(text)


# 🎰 GACHA
async def gacha(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    player = random.choice(PLAYERS)

    await user_collection.update_one(
        {"id": user_id},
        {"$addToSet": {"players": player}},
        upsert=True
    )

    await update.message.reply_text(f"🎰 You scouted player:\n⚽ {player}")


# 👑 BOSS
async def boss(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    user = await get_user(user_id)

    boss = random.choice(BOSSES)

    await update.message.reply_text(f"⚔ Boss appeared!\n{boss}")

    if user["xp"] > 50:

        xp = 20

        await user_collection.update_one(
            {"id": user_id},
            {"$inc": {"xp": xp, "goals": 2}}
        )

        await update.message.reply_text(f"🔥 Boss defeated!\n+{xp} XP")

    else:

        await update.message.reply_text("💀 Too weak! Gain more XP first.")


# 🎁 DAILY
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    xp = 10

    await user_collection.update_one(
        {"id": user_id},
        {"$inc": {"xp": xp}},
        upsert=True
    )

    await update.message.reply_text(f"🎁 Daily reward\n+{xp} XP")


# 📜 PROFILE
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    user = await get_user(user_id)

    players = ", ".join(user["players"]) if user["players"] else "None"

    await update.message.reply_text(
        f"⚽ Blue Lock Profile\n\nXP: {user['xp']}\nGoals: {user['goals']}\nEgo: {user['ego']}\n\nPlayers:\n{players}"
    )


application.add_handler(CommandHandler("football", football))
application.add_handler(CommandHandler("challenge", challenge))
application.add_handler(CommandHandler("accept", accept))
application.add_handler(CommandHandler("footballrank", footballrank))
application.add_handler(CommandHandler("footballlb", footballlb))
application.add_handler(CommandHandler("gacha", gacha))
application.add_handler(CommandHandler("boss", boss))
application.add_handler(CommandHandler("daily", daily))
application.add_handler(CommandHandler("profile", profile))
