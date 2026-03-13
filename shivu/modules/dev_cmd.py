import os
import sys
import psutil
import gc
import subprocess
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application, db, user_collection

INFO_VIDEO = "https://files.catbox.moe/9zncor.mp4"

# --- CONFIG: Apni Telegram User ID yahan daalein ---
OWNER_ID = 5158013355  # <--- ID YAHAN BADAL LEIN

# Security Helper
async def is_owner(update: Update):
    return update.effective_user.id == OWNER_ID

# --- 1. Restart ---
async def restart(update: Update, context: CallbackContext):    
    if not await is_owner(update): return    
    await update.message.reply_text("🔄 Restarting bot...")    
    os.execl(sys.executable, sys.executable, "-m", "shivu")
    
# --- 2. Status ---
async def status(update: Update, context: CallbackContext):
    if not await is_owner(update): return
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    await update.message.reply_text(f"📊 CPU: {cpu}% | RAM: {ram}%")

# --- 3. Evaluate Code ---
async def eval_command(update: Update, context: CallbackContext):
    if not await is_owner(update): return
    try:
        cmd = " ".join(context.args)
        result = eval(cmd)
        await update.message.reply_text(f"✅ Result: {result}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# --- 4. Database Nuke (Dangerous!) ---
async def nuke_db(update: Update, context: CallbackContext):
    if not await is_owner(update): return
    for collection in await db.list_collection_names():
        await db[collection].drop()
    await update.message.reply_text("💥 Database Nuked!")

# --- 5. Maintenance Mode ---
MAINTENANCE = False
async def maintenance(update: Update, context: CallbackContext):
    global MAINTENANCE
    if not await is_owner(update): return
    MAINTENANCE = not MAINTENANCE
    await update.message.reply_text(f"⚠️ Maintenance: {'ON' if MAINTENANCE else 'OFF'}")

# --- 6. DB Stats ---
async def db_stats(update: Update, context: CallbackContext):
    if not await is_owner(update): return
    stats = await db.command("dbstats")
    await update.message.reply_text(f"💾 Data Size: {stats['dataSize'] // 1024} KB")

# --- 7. Git Pull ---
async def git_pull(update: Update, context: CallbackContext):
    if not await is_owner(update): return
    output = subprocess.check_output(["git", "pull"]).decode("utf-8")
    await update.message.reply_text(f"🚀 Pull Result:\n{output}")

# --- 8. User Info ---
async def get_user_info(update: Update, context: CallbackContext):

    if not await is_owner(update):
        return

    if not context.args:
        await update.message.reply_text("❌ Usage: /uinfo USER_ID")
        return

    loading = await update.message.reply_text("⚡ sᴄᴀɴɴɪɴɢ ᴛʜᴇ ᴍᴜʟᴛɪᴠᴇʀsᴇ ғᴏʀ ᴛʜɪs ᴜsᴇʀ...")

    uid = int(context.args[0])
    data = await user_collection.find_one({'id': uid})

    if not data:
        await loading.edit_text("❌ User not found in database.")
        return

    name = data.get("first_name", "Unknown")
    username = data.get("username", "None")
    tokens = data.get("tokens", 0)
    chars = len(data.get("characters", []))

    text = f"""
╔══『 👤 USER PROFILE 』══╗

🆔 ID : `{uid}`
👤 Name : {name}
🔗 Username : @{username}

💰 Tokens : {tokens}
🎴 Characters : {chars}

━━━━━━━━━━━━━━
⚡ Queried by Sensei
『 Character Kawaii Bot 』
"""

    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=INFO_VIDEO,
        caption=text,
        parse_mode="Markdown"
    )

    await loading.delete()
# --- 9. Clean Logs ---
async def clean_logs(update: Update, context: CallbackContext):
    if not await is_owner(update): return
    os.system("rm *.log")
    await update.message.reply_text("🧹 Logs cleared!")

# --- 10. Memory Dump ---
async def mem_dump(update: Update, context: CallbackContext):
    if not await is_owner(update): return
    gc.collect()
    await update.message.reply_text("🧠 Memory cleaned!")

# --- Register Handlers ---
commands = [
    ("restart", restart), ("status", status), ("eval", eval_command),
    ("nuke", nuke_db), ("maintenance", maintenance), ("dbstats", db_stats),
    ("gitpull", git_pull), ("uinfo", get_user_info), ("clean", clean_logs),
    ("memdump", mem_dump)
]

for cmd, func in commands:
    application.add_handler(CommandHandler(cmd, func, block=False))




