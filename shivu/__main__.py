import importlib
import time
import random
import re
import asyncio
from html import escape
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CommandHandler, CallbackContext, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)
from shivu import (
    collection, top_global_groups_collection,
    group_user_totals_collection, user_collection,
    user_totals_collection, shivuu
)
from shivu import application, SUPPORT_CHAT, UPDATE_CHAT, OWNER_ID, sudo_users, db, LOGGER
from shivu.modules import ALL_MODULES

# ── Load all modules ──────────────────────────────────────────────────────────
for module_name in ALL_MODULES:
    importlib.import_module("shivu.modules." + module_name)

# ── State dicts ───────────────────────────────────────────────────────────────
locks                = {}
last_characters      = {}
sent_characters      = {}
first_correct_guesses= {}
message_counts       = {}
character_message_links = {}
last_user            = {}
warned_users         = {}
user_message_counts  = {}

# ── Rarity config ─────────────────────────────────────────────────────────────
rarity_map = {
    1:  "⚪️ 𝘾𝙊𝙈𝙈𝙊𝙉",
    2:  "🔵 𝙈𝙀𝘿𝙄𝙐𝙈",
    3:  "👶 𝘾𝙃𝙄𝘽𝙄",
    4:  "🟠 𝙍𝘼𝙍𝙀",
    5:  "🟡 𝙇𝙀𝙂𝙀𝙉𝘿𝘼𝙍𝙔",
    6:  "💮 𝙀𝙓𝘾𝙇𝙐𝙎𝙄𝙑𝙀",
    7:  "🫧 𝙋𝙍𝙀𝙈𝙄𝙐𝙈",
    8:  "🔮 𝙇𝙄𝙈𝙄𝙏𝙀𝘿 𝙀𝘿𝙄𝙏𝙄𝙊𝙉",
    9:  "🌸 𝙀𝙓𝙊𝙏𝙄𝘾",
    10: "🎐 𝘼𝙎𝙏𝙍𝘼𝙇",
    11: "💞 𝙑𝘼𝙇𝙀𝙉𝙏𝙄𝙉𝙀",
}

rarity_active = {v: True for v in rarity_map.values()}

RARITY_WEIGHTS = {
    "⚪️ 𝘾𝙊𝙈𝙈𝙊𝙉":          13,
    "🔵 𝙈𝙀𝘿𝙄𝙐𝙈":           10,
    "👶 𝘾𝙃𝙄𝘽𝙄":            7,
    "🟠 𝙍𝘼𝙍𝙀":             2.5,
    "🟡 𝙇𝙀𝙂𝙀𝙉𝘿𝘼𝙍𝙔":        4,
    "💮 𝙀𝙓𝘾𝙇𝙐𝙎𝙄𝙑𝙀":        0.5,
    "🫧 𝙋𝙍𝙀𝙈𝙄𝙐𝙈":          0.5,
    "🔮 𝙇𝙄𝙈𝙄𝙏𝙀𝘿 𝙀𝘿𝙄𝙏𝙄𝙊𝙉":  0.1,
    "🌸 𝙀𝙓𝙊𝙏𝙄𝘾":           0.5,
    "🎐 𝘼𝙎𝙏𝙍𝘼𝙇":           0.1,
    "💞 𝙑𝘼𝙇𝙀𝙉𝙏𝙄𝙉𝙀":        0.1,
}

AUTHORIZED_USER_ID   = 5158013355
AUTHORIZED_USER_NAME = "my Sensei @Ayushboy1"

# ── Helpers ───────────────────────────────────────────────────────────────────
def escape_markdown(text):
    return re.sub(r'([\*_`\\~>#\+\-=|{}.!])', r'\\\1', text)


# ── message_counter ───────────────────────────────────────────────────────────
async def message_counter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.effective_user:
        return

    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"

    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()

    async with locks[chat_id]:
        chat_settings = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_settings.get('message_frequency', 100) if chat_settings else 100

        # Per-user count
        user_message_counts.setdefault(chat_id, {})
        user_message_counts[chat_id][user_id] = user_message_counts[chat_id].get(user_id, 0) + 1

        # Spam check
        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                warning = (
                    f"⚠️ **Spamming Detected!**\n"
                    f"🛑 **@{username}**, slow down!\n"
                    f"⏳ You are muted for **10 minutes**."
                )
                await update.message.reply_text(warning, parse_mode="Markdown")
                warned_users[user_id] = time.time()
                return
        else:
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        # Global chat count
        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        # Milestone notification
        user_msgs = user_message_counts[chat_id][user_id]
        if user_msgs % 25 == 0:
            await update.message.reply_text(
                f"🎉 Congrats, @{username}! You've sent **{user_msgs}** messages here!",
                parse_mode="Markdown"
            )

        # Spawn character every N messages
        if message_counts[chat_id] % message_frequency == 0:
            await send_image(update, context)
            message_counts[chat_id] = 0


# ── send_image ────────────────────────────────────────────────────────────────
async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    all_characters = await collection.find({}).to_list(length=None)
    if not all_characters:
        return

    sent_characters.setdefault(chat_id, [])

    # Reset if all characters sent
    if len(sent_characters[chat_id]) >= len(all_characters):
        sent_characters[chat_id] = []

    # Filter: not yet sent, has rarity, rarity is active
    available = [
        c for c in all_characters
        if 'id' in c
        and c['id'] not in sent_characters[chat_id]
        and c.get('rarity') in rarity_active
        and rarity_active.get(c.get('rarity'), False)
    ]

    if not available:
        available = all_characters  # fallback

    # Weighted selection
    weights = [RARITY_WEIGHTS.get(c.get('rarity'), 1) for c in available]
    selected = random.choices(available, weights=weights, k=1)[0]

    sent_characters[chat_id].append(selected['id'])
    last_characters[chat_id] = selected

    # Clear previous guess state
    first_correct_guesses.pop(chat_id, None)

    caption = (
        f"<b>{selected['rarity'][0]} ᴋᴀᴡᴀɪ! ᴀ {selected['rarity'][2:]} ᴄʜᴀʀᴀᴄᴛᴇʀ ʜᴀs ᴀᴘᴘᴇᴀʀᴇᴅ!</b>\n\n"
        f"<b>ᴀᴅᴅ ʜᴇʀ ᴛᴏ ʏᴏᴜʀ ʜᴀʀᴇᴍ ʙʏ sᴇɴᴅɪɴɢ</b>\n<b>/kawaii ɴᴀᴍᴇ</b>"
    )

    file_url = selected.get('img_url', '')
    is_video = file_url.lower().endswith((".mp4", ".mov", ".mkv"))

    if is_video:
        message = await context.bot.send_video(
            chat_id=chat_id, video=file_url,
            caption=caption, parse_mode='HTML'
        )
    else:
        message = await context.bot.send_photo(
            chat_id=chat_id, photo=file_url,
            caption=caption, parse_mode='HTML'
        )

    # Store message link
    chat = update.effective_chat
    if chat.username:
        character_message_links[chat_id] = f"https://t.me/{chat.username}/{message.message_id}"
    else:
        clean_id = str(chat_id).replace("-100", "")
        character_message_links[chat_id] = f"https://t.me/c/{clean_id}/{message.message_id}"


# ── Info callback (flew-away button) ─────────────────────────────────────────
async def placeholder_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    character_id = query.data.split("_", 1)[1]
    character = await collection.find_one({"id": character_id})

    if character:
        await query.message.reply_photo(
            photo=character['img_url'],
            caption=(
                f"<b>📜 Character Details:</b>\n"
                f"🌸 <b>Name:</b> {character['name']}\n"
                f"❇️ <b>Anime:</b> {character['anime']}\n"
                f"💎 <b>Rarity:</b> {character['rarity']}"
            ),
            parse_mode="HTML"
        )
    else:
        await query.message.reply_text("<b>❌ Character not found!</b>", parse_mode="HTML")


# ── /kawaii (guess) ───────────────────────────────────────────────────────────
async def guess(update: Update, context: CallbackContext) -> None:
    if not update.effective_user or not update.message:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # No character spawned yet
    if chat_id not in last_characters:
        return

    character = last_characters[chat_id]

    # Already guessed correctly by someone
    if chat_id in first_correct_guesses:
        winner = first_correct_guesses[chat_id].get('user')
        if winner:
            user_link = f'<a href="tg://user?id={winner.id}">{escape(winner.first_name)}</a>'
        else:
            user_link = "Someone"
        await update.message.reply_text(
            f'🌟 <b>{escape(character["name"])}</b> has already been kawaiied by {user_link}!\n'
            f'🍵 Wait for the next character to spawn...',
            parse_mode='HTML'
        )
        return

    # Get user guess
    guess_text = ' '.join(context.args).strip().lower() if context.args else ''

    if not guess_text:
        return

    if "()" in guess_text or "&" in guess_text:
        await update.message.reply_text(
            "🔒 Invalid input! Please avoid '&' and special characters."
        )
        return

    character_name = character['name'].lower()
    name_parts = character_name.split()

    correct = (
        sorted(name_parts) == sorted(guess_text.split())
        or any(part == guess_text for part in name_parts)
    )

    if correct:
        # Record winner
        first_correct_guesses[chat_id] = {
            'user': update.effective_user,
            'character': character,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        time_taken_secs = 0  # approximate since we don't store spawn time precisely
        minutes, seconds = divmod(time_taken_secs, 60)

        # Update user in DB
        user_doc = await user_collection.find_one({'id': user_id})
        update_fields = {}

        if user_doc:
            if update.effective_user.username != user_doc.get('username'):
                update_fields['username'] = update.effective_user.username
            if update.effective_user.first_name != user_doc.get('first_name'):
                update_fields['first_name'] = update.effective_user.first_name
            if update_fields:
                await user_collection.update_one({'id': user_id}, {'$set': update_fields})
            await user_collection.update_one(
                {'id': user_id},
                {'$push': {'characters': character}}
            )
        else:
            await user_collection.insert_one({
                'id': user_id,
                'username': getattr(update.effective_user, 'username', None),
                'first_name': update.effective_user.first_name,
                'characters': [character],
            })

        # Update group leaderboard
        group_entry = await group_user_totals_collection.find_one(
            {'user_id': user_id, 'group_id': chat_id}
        )
        if group_entry:
            await group_user_totals_collection.update_one(
                {'user_id': user_id, 'group_id': chat_id},
                {'$inc': {'count': 1}}
            )
        else:
            await group_user_totals_collection.insert_one({
                'user_id': user_id,
                'group_id': chat_id,
                'username': getattr(update.effective_user, 'username', None),
                'first_name': update.effective_user.first_name,
                'count': 1,
            })

        keyboard = [[InlineKeyboardButton(
            f"🏮 {escape(update.effective_user.first_name)}'s Harem 🏮",
            switch_inline_query_current_chat=f"collection.{user_id}"
        )]]

        await update.message.reply_text(
            f'✅ <b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> '
            f'You got a new character!\n\n'
            f'🌸 𝗡𝗔𝗠𝗘: <b>{character["name"]}</b>\n'
            f'❇️ 𝗔𝗡𝗜𝗠𝗘: <b>{character["anime"]}</b>\n'
            f'{character["rarity"][0]} 𝗥𝗔𝗥𝗜𝗧𝗬: <b>{character["rarity"]}</b>',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Remove character so it can't be guessed again
        del last_characters[chat_id]

    else:
        # Wrong guess
        message_link = character_message_links.get(chat_id, "#")
        keyboard = [[InlineKeyboardButton("★ See Character ★", url=message_link)]]
        await update.message.reply_text(
            f"❌ Wrong guess: <b>{escape(guess_text)}</b>!\nPlease try again.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ── /set_on & /set_off ────────────────────────────────────────────────────────
async def set_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return await update.message.reply_text(f"Only {AUTHORIZED_USER_NAME} can use this.")
    try:
        rarity = rarity_map[int(context.args[0])]
        if rarity_active.get(rarity):
            await update.message.reply_text(f'Rarity {rarity} is already ON.')
        else:
            rarity_active[rarity] = True
            await update.message.reply_text(f'✅ Rarity {rarity} is now ON.')
    except (IndexError, ValueError, KeyError):
        await update.message.reply_text('Please provide a valid rarity number (1–11).')


async def set_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != AUTHORIZED_USER_ID:
        return await update.message.reply_text(f"Only {AUTHORIZED_USER_NAME} can use this.")
    try:
        rarity = rarity_map[int(context.args[0])]
        if not rarity_active.get(rarity):
            await update.message.reply_text(f'Rarity {rarity} is already OFF.')
        else:
            rarity_active[rarity] = False
            await update.message.reply_text(f'✅ Rarity {rarity} is now OFF.')
    except (IndexError, ValueError, KeyError):
        await update.message.reply_text('Please provide a valid rarity number (1–11).')


# ── Register handlers ─────────────────────────────────────────────────────────
application.add_handler(CommandHandler("kawaii", guess, block=False))
application.add_handler(CommandHandler("set_on",  set_on,  block=False))
application.add_handler(CommandHandler("set_off", set_off, block=False))
application.add_handler(CallbackQueryHandler(placeholder_callback, pattern=r"^info_"))
application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_counter, block=False))


# ── Bot entry point ───────────────────────────────────────────────────────────
async def start_bot():
    await shivuu.start()
    LOGGER.info("Pyrogram Client Started!")

    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        LOGGER.info("Bot is now Online on Telegram!")
        await asyncio.Event().wait()  # keep alive forever


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(start_bot())
    except (KeyboardInterrupt, SystemExit):
        LOGGER.info("Bot Stopped!")
    except Exception as e:
        LOGGER.error(f"Error: {e}")                                
