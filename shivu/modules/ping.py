import time
from datetime import timedelta
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from shivu import application

# Store the bot start time
BOT_START_TIME = time.time()


# ---------------- PING COMMAND ---------------- #

async def ping(update: Update, context: CallbackContext) -> None:

    image_url = "https://files.catbox.moe/7jvh55.jpg"

    start_time = time.time()

    await update.message.reply_sticker(
        "CAACAgQAAxkBAAOxZydY5130mqDr6GKX6kucio9IHRQAAlgRAAKLAdBR7L2HepOERFIeBA"
    )

    msg = await update.message.reply_text("⏳ kawaii is calculating...")

    end_time = time.time()
    elapsed_time = round((end_time - start_time) * 1000, 3)

    await msg.delete()

    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=image_url,
        caption=(
            f"🌸 @{context.bot.username} ᴘσηɢ!\n\n"
            f"⏱️ ʟᴧᴛєηᴄʏ: {elapsed_time} ms\n\n"
            f"✨ ғᴧsᴛ ᴧs єᴠєʀ, ᴊᴜsᴛ ғσʀ ʏσᴜ, {update.effective_user.mention_html()} 💖"
        ),
        parse_mode="HTML",
    )


# ---------------- ALIVE COMMAND ---------------- #

async def alive(update: Update, context: CallbackContext) -> None:

    video_url = "https://files.catbox.moe/nywp1r.mp4"

    uptime_seconds = time.time() - BOT_START_TIME
    uptime = str(timedelta(seconds=int(uptime_seconds)))

    alive_message = (
        f"👋 ʜєʟʟσ, sєηᴘᴧɪ! I'ᴍ @{context.bot.username} 🌸\n\n"
        "❄️ sᴛᴧᴛᴜs: ғᴜʟʟʏ σᴘєʀᴧᴛɪσηᴧʟ\n"
        f"🌋 ᴜᴘᴛɪᴍє: {uptime}\n"
        f"🥂 ʙσᴛ ɴᴧᴍє: @{context.bot.username}\n"
        "📊 ᴠєʀsɪση: 1.0.0\n\n"
        f"ᴛʜᴧηᴋs ғσʀ ᴋєєᴘɪηɢ ᴍє ᴧʟɪᴠє, {update.effective_user.mention_html()} 😊💕"
    )

    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=video_url,
        caption=alive_message,
        parse_mode="HTML",
    )


# ---------------- HANDLERS ---------------- #

application.add_handler(CommandHandler("ping", ping))
application.add_handler(CommandHandler("alive", alive))
