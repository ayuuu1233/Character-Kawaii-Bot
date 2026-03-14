import os
import sys
import psutil
import gc
import subprocess
import random
import time
from telegram.ext import MessageHandler, filters
from telegram import Update
from datetime import datetime, timedelta
from telegram import ChatPermissions
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, db, user_collection

INFO_VIDEO = "https://files.catbox.moe/9zncor.mp4"

OWNER_ID = 5158013355

# ---------------- OWNER CHECK ----------------
async def is_owner(update: Update):
    return update.effective_user.id == OWNER_ID


# ---------------- AURA ----------------
last_arrival = 0
COOLDOWN = 20

ARRIVAL_EVENTS = [
    {
        "text": "👑 My Sensei has arrived... Everyone behave.",
        "video": "https://files.catbox.moe/s4nq7h.mp4"
    },
    {
        "text": "⚡ The Master has entered the chat.",
        "video": "https://files.catbox.moe/7yma10.mp4"
    },
    {
        "text": "🔥 All characters bow... Sensei is here!",
        "video": "https://files.catbox.moe/ihru5d.mp4"
    },
    {
        "text": "👁️ Sensei is watching...",
        "video": "https://files.catbox.moe/rtm26t.mp4"
    }
]

RARE_EVENTS = [
    {
        "text": "🌌 Reality bends as the Supreme Owner appears.",
        "video": "https://files.catbox.moe/qkeqgs.mp4"
    },
    {
        "text": "💀 The server trembles... Ayush has arrived.",
        "video": "https://files.catbox.moe/g1b6dp.mp4"
    }
]


async def owner_arrival(update: Update, context: CallbackContext):

    global last_arrival

    if update.effective_user.id != OWNER_ID:
        return

    if update.effective_chat.type == "private":
        return

    now = time.time()

    if now - last_arrival < COOLDOWN:
        return

    last_arrival = now

    event = random.choice(ARRIVAL_EVENTS)

    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=event["video"],
        caption=event["text"]
    )


# ---------------- STATUS ----------------
async def status(update: Update, context: CallbackContext):
    if not await is_owner(update):
        return

    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    await update.message.reply_text(
        f"📊 BOT STATUS\n\n"
        f"🧠 CPU : {cpu}%\n"
        f"💾 RAM : {ram}%"
    )


# ---------------- EVAL ----------------
async def eval_command(update: Update, context: CallbackContext):
    if not await is_owner(update):
        return

    try:
        code = " ".join(context.args)
        result = eval(code)
        await update.message.reply_text(f"✅ Result:\n{result}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error:\n{e}")


# ---------------- NUKE DATABASE ----------------
async def nuke_db(update: Update, context: CallbackContext):
    if not await is_owner(update):
        return

    if not context.args or context.args[0] != "confirm":
        await update.message.reply_text(
            "⚠️ This will delete ALL database.\n\n"
            "Use:\n/nuke confirm"
        )
        return

    collections = await db.list_collection_names()

    for name in collections:
        await db[name].drop()

    await update.message.reply_text("💥 Database Nuked Successfully!")


# ---------------- MAINTENANCE ----------------
MAINTENANCE = False

async def maintenance(update: Update, context: CallbackContext):
    global MAINTENANCE

    if not await is_owner(update):
        return

    MAINTENANCE = not MAINTENANCE

    await update.message.reply_text(
        f"⚠️ Maintenance Mode : {'ON' if MAINTENANCE else 'OFF'}"
    )


# ---------------- DB STATS ----------------
async def db_stats(update: Update, context: CallbackContext):
    if not await is_owner(update):
        return

    stats = await db.command("dbstats")

    size = stats["dataSize"] // 1024

    await update.message.reply_text(
        f"💾 Database Stats\n\n"
        f"Data Size : {size} KB"
    )


# ---------------- JUDGEMENT ----------------
JUDGEMENT_MESSAGES = [
    "⚖️ Sensei has judged {user}\nPunishment: 100 Tokens Burned!",
    "🔥 Divine punishment delivered to {user}\nResult: 200 Tokens Destroyed!",
    "💀 Curse placed on {user}\nResult: 50 Tokens Removed!",
    "⚡ Sensei's anger strikes {user}\nResult: Temporary Silence!",
]

RARE_JUDGEMENT = [
    "🌌 Ultimate Judgement on {user}\nResult: Banished from the realm!",
]

async def judgement(update: Update, context: CallbackContext):

    if not await is_owner(update):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a user with /judgement")
        return

    target = update.message.reply_to_message.from_user
    uid = target.id
    chat_id = update.effective_chat.id

    # rare punishment chance
    if random.randint(1,100) <= 5:

        text = random.choice(RARE_JUDGEMENT).format(user=target.mention_html())

        await context.bot.ban_chat_member(chat_id, uid)

        await context.bot.send_message(
            chat_id,
            text,
            parse_mode="HTML"
        )
        return

    punishment = random.randint(1,4)

    if punishment == 1:

        await user_collection.update_one(
            {"id": uid},
            {"$inc": {"tokens": -100}}
        )

    elif punishment == 2:

        await user_collection.update_one(
            {"id": uid},
            {"$inc": {"tokens": -200}}
        )

    elif punishment == 3:

        await user_collection.update_one(
            {"id": uid},
            {"$inc": {"tokens": -50}}
        )

    elif punishment == 4:

        until = datetime.utcnow() + timedelta(minutes=5)

        await context.bot.restrict_chat_member(
            chat_id,
            uid,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until
        )

    text = random.choice(JUDGEMENT_MESSAGES).format(user=target.mention_html())

    await context.bot.send_message(
        chat_id,
        text,
        parse_mode="HTML"
    )

# ---------------- USER INFO ----------------
async def get_user_info(update: Update, context: CallbackContext):

    if not await is_owner(update):
        return

    if not context.args:
        await update.message.reply_text("Usage:\n/uinfo USER_ID")
        return

    loading = await update.message.reply_text("🔍 Searching user...")

    uid = int(context.args[0])
    data = await user_collection.find_one({'id': uid})

    if not data:
        await loading.edit_text("❌ User not found.")
        return

    name = data.get("first_name", "Unknown")
    username = data.get("username")

    if username:
        username = f"@{username}"
    else:
        username = "None"

    tokens = data.get("tokens", 0)
    chars = len(data.get("characters", []))

    text = f"""
╔══『 👤 USER PROFILE 』══╗

🆔 ID : `{uid}`
👤 Name : {name}
🔗 Username : {username}

💰 Tokens : {tokens}
🎴 Characters : {chars}

━━━━━━━━━━━━━━
⚡ Queried by Sensei
"""

    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=INFO_VIDEO,
        caption=text,
        parse_mode="Markdown"
    )

    await loading.delete()


# ---------------- CLEAN LOGS ----------------
async def clean_logs(update: Update, context: CallbackContext):
    if not await is_owner(update):
        return

    os.system("rm -f *.log")
    await update.message.reply_text("🧹 Logs cleaned.")


# ---------------- MEMORY CLEAN ----------------
async def mem_dump(update: Update, context: CallbackContext):
    if not await is_owner(update):
        return

    gc.collect()
    await update.message.reply_text("🧠 Memory cleaned.")


# ---------------- REGISTER COMMANDS ----------------
commands = [
    
    ("status", status),
    ("eval", eval_command),
    ("nuke", nuke_db),
    ("maintenance", maintenance),
    ("dbstats", db_stats),
    ("judgement", judgement),
    ("uinfo", get_user_info),
    ("clean", clean_logs),
    ("memdump", mem_dump),
]

for cmd, func in commands:
    application.add_handler(CommandHandler(cmd, func, block=False))
    application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, owner_arrival),
    group=-1
    )
