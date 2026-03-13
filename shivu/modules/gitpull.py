import os
import sys
import json
import subprocess
import traceback
import time
from pyrogram import filters
from shivu import shivuu as app, SPECIALGRADE, db

SUDO_FILE = "sudo_users.json"
LOG_FILE = "botlog.txt"
START_TIME = time.time()

# -------------------------
# LOAD SUDO
# -------------------------
def load_sudo():
    if os.path.exists(SUDO_FILE):
        with open(SUDO_FILE) as f:
            return set(json.load(f))
    return set(SPECIALGRADE)

def save_sudo(data):
    with open(SUDO_FILE, "w") as f:
        json.dump(list(data), f)

SUDO = load_sudo()

# -------------------------
# CHECK SUDO
# -------------------------
def is_sudo(user_id):
    return str(user_id) in SUDO

# -------------------------
# ADD SUDO
# -------------------------
@app.on_message(filters.command("addog"))
async def add_sudo(client, message):

    if str(message.from_user.id) not in SPECIALGRADE:
        return await message.reply("❌ Not authorized")

    if not message.reply_to_message:
        return await message.reply("Reply to a user")

    user_id = str(message.reply_to_message.from_user.id)

    SUDO.add(user_id)
    save_sudo(SUDO)

    await message.reply("✅ User added to SUDO")

# -------------------------
# REMOVE SUDO
# -------------------------
@app.on_message(filters.command("rmog"))
async def remove_sudo(client, message):

    if str(message.from_user.id) not in SPECIALGRADE:
        return await message.reply("❌ Not authorized")

    if not message.reply_to_message:
        return await message.reply("Reply to user")

    user_id = str(message.reply_to_message.from_user.id)

    if user_id in SUDO:
        SUDO.remove(user_id)
        save_sudo(SUDO)

        await message.reply("✅ Removed from SUDO")

# -------------------------
# SUDO LIST
# -------------------------
@app.on_message(filters.command("sudolist"))
async def sudolist(client, message):

    if str(message.from_user.id) not in SPECIALGRADE:
        return await message.reply("❌ Not authorized")

    text = "👑 **SUDO USERS**\n\n"

    for x in SUDO:
        text += f"`{x}`\n"

    await message.reply(text)

# -------------------------
# GIT PULL
# -------------------------
@app.on_message(filters.command("gitpull"))
async def gitpull(client, message):

    if not is_sudo(message.from_user.id):
        return await message.reply("❌ Not authorized")

    msg = await message.reply("🔄 Updating bot...")

    process = subprocess.run(
        ["git", "pull", "origin", "main"],
        capture_output=True,
        text=True
    )

    output = process.stdout

    if "Already up to date" in output:
        return await msg.edit("✅ Already up to date")

    await msg.edit(f"✅ Update Pulled\n\n`{output[:3000]}`\n\nRestarting...")

    os.execv(sys.executable, ["python"] + sys.argv)

# -------------------------
# GIT LOG
# -------------------------
@app.on_message(filters.command("gitlog"))
async def gitlog(client, message):

    if not is_sudo(message.from_user.id):
        return await message.reply("❌ Not authorized")

    process = subprocess.run(
        ["git", "log", "--oneline", "-5"],
        capture_output=True,
        text=True
    )

    await message.reply(f"📜 Latest commits\n\n`{process.stdout}`")

# -------------------------
# GIT STATUS
# -------------------------
@app.on_message(filters.command("gitstatus"))
async def gitstatus(client, message):

    if not is_sudo(message.from_user.id):
        return await message.reply("❌ Not authorized")

    process = subprocess.run(
        ["git", "status"],
        capture_output=True,
        text=True
    )

    await message.reply(f"`{process.stdout[:3500]}`")

# -------------------------
# RESTART
# -------------------------
@app.on_message(filters.command("restart"))
async def restart(client, message):

    if not is_sudo(message.from_user.id):
        return await message.reply("❌ Not authorized")

    await message.reply("🔄 Restarting bot...")

    os.execv(sys.executable, ["python"] + sys.argv)

# -------------------------
# BOT STATUS
# -------------------------
@app.on_message(filters.command("bot"))
async def bot_status(client, message):

    uptime = int(time.time() - START_TIME)

    hours = uptime // 3600
    minutes = (uptime % 3600) // 60

    text = f"""
🤖 BOT STATUS

Status : Running
Uptime : {hours}h {minutes}m
Python : {sys.version.split()[0]}
"""

    await message.reply(text)

# -------------------------
# SHELL COMMAND
# -------------------------
@app.on_message(filters.command("shell"))
async def shell(client, message):

    if not is_sudo(message.from_user.id):
        return

    cmd = message.text.split(None,1)[1]

    process = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    output = process.stdout + process.stderr

    if not output:
        output = "Done"

    await message.reply(f"`{output[:3500]}`")

# -------------------------
# PYTHON EVAL
# -------------------------
@app.on_message(filters.command("eval"))
async def eval_python(client, message):

    if not is_sudo(message.from_user.id):
        return

    code = message.text.split(None,1)[1]

    try:
        result = eval(code)
        await message.reply(f"`{result}`")

    except Exception as e:
        await message.reply(f"`{e}`")

# -------------------------
# LOGS
# -------------------------
@app.on_message(filters.command("logs"))
async def logs(client, message):

    if not is_sudo(message.from_user.id):
        return

    if os.path.exists(LOG_FILE):
        await message.reply_document(LOG_FILE)
    else:
        await message.reply("No logs found")

# -------------------------
# BACKUP DATABASE
# -------------------------
@app.on_message(filters.command("backupdb"))
async def backup_db(client, message):

    if not is_sudo(message.from_user.id):
        return

    data = []

    async for doc in db.collection.find():
        data.append(doc)

    with open("db_backup.json","w") as f:
        json.dump(data,f,default=str)

    await message.reply_document("db_backup.json")

# -------------------------
# CLEAR TEMP FILES
# -------------------------
@app.on_message(filters.command("cleartemp"))
async def clear_temp(client, message):

    if not is_sudo(message.from_user.id):
        return

    removed = 0

    for file in os.listdir():

        if file.endswith(".tmp") or file.endswith(".cache"):

            os.remove(file)
            removed += 1

    await message.reply(f"🧹 Cleared {removed} temp files")

# -------------------------
# GIT ADD
# -------------------------
@app.on_message(filters.command("gitadd"))
async def gitadd(client, message):

    if not is_sudo(message.from_user.id):
        return await message.reply("❌ Not authorized")

    process = subprocess.run(
        ["git", "add", "."],
        capture_output=True,
        text=True
    )

    await message.reply("✅ Files added to staging")

# -------------------------
# GIT COMMIT
# -------------------------
@app.on_message(filters.command("gitcommit"))
async def gitcommit(client, message):

    if not is_sudo(message.from_user.id):
        return await message.reply("❌ Not authorized")

    if len(message.command) < 2:
        return await message.reply("Usage:\n/gitcommit your message")

    msg = " ".join(message.command[1:])

    process = subprocess.run(
        ["git", "commit", "-m", msg],
        capture_output=True,
        text=True
    )

    output = process.stdout + process.stderr

    await message.reply(f"`{output[:3500]}`")

# -------------------------
# GIT PUSH
# -------------------------
@app.on_message(filters.command("gitpush"))
async def gitpush(client, message):

    if not is_sudo(message.from_user.id):
        return await message.reply("❌ Not authorized")

    msg = await message.reply("🚀 Pushing to GitHub...")

    process = subprocess.run(
        ["git", "push", "origin", "main"],
        capture_output=True,
        text=True
    )

    output = process.stdout + process.stderr

    await msg.edit(f"✅ Push complete\n\n`{output[:3500]}`")
