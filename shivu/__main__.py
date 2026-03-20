import datetime
import importlib
import time
import random
import re
import asyncio
import math
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, MessageHandler, filters, ContextTypes, Application, CallbackQueryHandler, CallbackContext
from shivu import collection, top_global_groups_collection, group_user_totals_collection, user_collection, user_totals_collection, shivuu
from shivu import application, SUPPORT_CHAT, UPDATE_CHAT, OWNER_ID, sudo_users, db, LOGGER
from shivu import set_on_data, set_off_data
from shivu.modules import ALL_MODULES
from shivu.modules import upload
from datetime import datetime

locks = {}
message_counters = {}
spam_counters = {}
last_characters = {}
sent_characters = {}
first_correct_guesses = {}
message_counts = {}
character_message_links = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("shivu.modules." + module_name)

last_user = {}
warned_users = {}

def escape_markdown(text):
    escape_chars = r'\*_`\\~>#+-=|{}.!'
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)

archived_characters = {}

# Initialize dictionaries for locks, last user, message counts, and warned users
locks = {}
last_user = {}
message_counts = {}
warned_users = {}
user_message_counts = {}

async def message_counter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # SAFETY CHECK 1: Agar chat ya user missing hai toh return kar jao
    if not update.effective_chat or not update.effective_user:
        return

    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    # Baaki logic (Locks, Chat Settings, etc.) yahan se shuru hoga...
    if chat_id not in locks:
        locks[chat_id] = asyncio.Lock()
    lock = locks[chat_id]

    async with lock:
        # ... (baaki sara code same rahega)

        # Fetch or set default message frequency for the chat
        chat_settings = await user_totals_collection.find_one({'chat_id': chat_id})
        message_frequency = chat_settings.get('message_frequency', 100) if chat_settings else 100

        # Track the user's individual message count
        user_message_counts[chat_id] = user_message_counts.get(chat_id, {})
        user_message_counts[chat_id][user_id] = user_message_counts[chat_id].get(user_id, 0) + 1

        # Check if the user is spamming
        if chat_id in last_user and last_user[chat_id]['user_id'] == user_id:
            last_user[chat_id]['count'] += 1
            if last_user[chat_id]['count'] >= 10:
                # Warn user if within cooldown time
                if user_id in warned_users and time.time() - warned_users[user_id] < 600:
                    return
                else:
                    # Enhanced warning message
                    warning_message = (
                        f"⚠️ **Spamming Detected!**\n"
                        f"🛑 **@{username}**, slow down! Excessive messages are not allowed.\n"
                        f"⏳ You are muted for **10 minutes**."
                    )
                    await update.message.reply_text(warning_message, parse_mode="Markdown")
                    warned_users[user_id] = time.time()
                    return
        else:
            # Reset message count if the user has changed
            last_user[chat_id] = {'user_id': user_id, 'count': 1}

        # Increment global chat message count
        message_counts[chat_id] = message_counts.get(chat_id, 0) + 1

        # Additional features:
        # 1. Notify the user of their message milestones
        user_messages = user_message_counts[chat_id][user_id]
        if user_messages % 25 == 0:
            milestone_message = (
                f"🎉 Congrats, @{username}! You've sent **{user_messages}** messages in this chat!\n"
                f"Keep engaging responsibly!"
            )
            await update.message.reply_text(milestone_message, parse_mode="Markdown")

        # 2. Send a celebratory image or message for every `message_frequency` messages
        if message_counts[chat_id] % message_frequency == 0:
            await send_image(update, context)
            message_counts[chat_id] = 0
    
rarity_active = {
    "⚪️ 𝘾𝙊𝙈𝙈𝙊𝙉": True,
    "🔵 𝙈𝙀𝘿𝙄𝙐𝙈": True,
    "👶 𝘾𝙃𝙄𝘽𝙄": True,
    "🟠 𝙍𝘼𝙍𝙀": True,
    "🟡 𝙇𝙀𝙂𝙀𝙉𝘿𝘼𝙍𝙔": True,
    "💮 𝙀𝙓𝘾𝙇𝙐𝙎𝙄𝙑𝙀": True,
    "🫧 𝙋𝙍𝙀𝙈𝙄𝙐𝙈": True,
    "🔮 𝙇𝙄𝙈𝙄𝙏𝙀𝘿 𝙀𝘿𝙄𝙏𝙄𝙊𝙉": True,
    "🌸 𝙀𝙓𝙊𝙏𝙄𝘾": True,
    "🎐 𝘼𝙎𝙏𝙍𝘼𝙇": True,
    "💞 𝙑𝘼𝙇𝙀𝙉𝙏𝙄𝙉𝙀": True
}

# Map numbers to rarity strings
rarity_map = {
   1: "⚪️ 𝘾𝙊𝙈𝙈𝙊𝙉",
   2: "🔵 𝙈𝙀𝘿𝙄𝙐𝙈",
   3: "👶 𝘾𝙃𝙄𝘽𝙄",
   4: "🟠 𝙍𝘼𝙍𝙀",
   5: "🟡 𝙇𝙀𝙂𝙀𝙉𝘿𝘼𝙍𝙔",
   6: "💮 𝙀𝙓𝘾𝙇𝙐𝙎𝙄𝙑𝙀",
   7: "🫧 𝙋𝙍𝙀𝙈𝙄𝙐𝙈",
   8: "🔮 𝙇𝙄𝙈𝙄𝙏𝙀𝘿 𝙀𝘿𝙄𝙏𝙄𝙊𝙉",
   9: "🌸 𝙀𝙓𝙊𝙏𝙄𝘾",
   10: "🎐 𝘼𝙎𝙏𝙍𝘼𝙇",
   11: "💞 𝙑𝘼𝙇𝙀𝙉𝙏𝙄𝙉𝙀"
 }

RARITY_WEIGHTS = {
    "⚪️ 𝘾𝙊𝙈𝙈𝙊𝙉": 13,
    "🔵 𝙈𝙀𝘿𝙄𝙐𝙈": 10,
    "👶 𝘾𝙃𝙄𝘽𝙄": 7,
    "🟠 𝙍𝘼𝙍𝙀": 2.5,
    "🟡 𝙇𝙀𝙂𝙀𝙉𝘿𝘼𝙍𝙔": 4,
    "💮 𝙀𝙓𝘾𝙇𝙐𝙎𝙄𝙑𝙀": 0.5,
    "🫧 𝙋𝙍𝙀𝙈𝙄𝙐𝙈": 0.5,
    "🔮 𝙇𝙄𝙈𝙄𝙏𝙀𝘿 𝙀𝘿𝙄𝙏𝙄𝙊𝙉": 0.1,
    "🌸 𝙀𝙓𝙊𝙏𝙄𝘾": 0.5,
    "🎐 𝘼𝙎𝙏𝙍𝘼𝙇": 0.1,
    "💞 𝙑𝘼𝙇𝙀𝙉𝙏𝙄𝙉𝙀": 0.1,
}
async def send_image(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    # Fetch all characters from the database
    all_characters = list(await collection.find({}).to_list(length=None))

    # Initialize sent_characters if not already done
    if chat_id not in sent_characters:
        sent_characters[chat_id] = []

    # Reset sent_characters if all characters have been sent
    if len(sent_characters[chat_id]) == len(all_characters):
        sent_characters[chat_id] = []

    # Prepare available characters
    available_characters = [
        c for c in all_characters 
        if 'id' in c 
        and c['id'] not in sent_characters[chat_id]
        and c.get('rarity') is not None 
        and c.get('rarity') != '💞 Valentine Special'
    ]

    # Weighted random selection based on rarity
    cumulative_weights = []
    cumulative_weight = 0
    for character in available_characters:
        cumulative_weight += RARITY_WEIGHTS.get(character.get('rarity'), 1)
        cumulative_weights.append(cumulative_weight)

    rand = random.uniform(0, cumulative_weight)
    selected_character = None
    for i, character in enumerate(available_characters):
        if rand <= cumulative_weights[i]:
            selected_character = character
            break

    if not selected_character:
        # Fallback: choose randomly if no character was selected
        selected_character = random.choice(all_characters)

    # Update sent_characters and last_characters
    sent_characters[chat_id].append(selected_character['id'])
    last_characters[chat_id] = selected_character

    # Reset first_correct_guesses for this chat
    if chat_id in first_correct_guesses:
        del first_correct_guesses[chat_id]

    # Rarity Emoji Mapping
    rarity_to_emoji = {
        "⚪️ 𝘾𝙊𝙈𝙈𝙊𝙉": "⚪️",
        "🔵 𝙈𝙀𝘿𝙄𝙐𝙈": "🔵",
        "👶 𝘾𝙃𝙄𝘽𝙄": "👶",
        "🟠 𝙍𝘼𝙍𝙀": "🟠",
        "🟡 𝙇𝙀𝙂𝙀𝙉𝘿𝘼𝙍𝙔": "🟡",
        "💮 𝙀𝙓𝘾𝙇𝙐𝙎𝙄𝙑𝙀": "💮",
        "🫧 𝙋𝙍𝙀𝙈𝙄𝙐𝙈": "🫧",
        "🔮 𝙇𝙄𝙈𝙄𝙏𝙀𝘿 𝙀𝘿𝙄𝙏𝙄𝙊𝙉": "🔮",
        "🌸 𝙀𝙓𝙊𝙏𝙄𝘾": "🌸",
        "🎐 𝘼𝙎𝙏𝙍𝘼𝙇": "🎐",
        "💞 𝙑𝘼𝙇𝙀𝙉𝙏𝙄𝙉𝙀": "💞",
    }

    rarity_emoji = rarity_to_emoji.get(selected_character.get('rarity'), "❓")

    # Send the character's image and message
     # Check karein ki URL video hai ya photo
    file_url = selected_character['img_url']
    
    if file_url.endswith((".mp4", ".mov", ".mkv")):
        # Agar video hai toh send_video use karein
        message = await context.bot.send_video(
            chat_id=chat_id,
            video=file_url,
            caption=f"""<b>{selected_character['rarity'][0]} ᴋᴀᴡᴀɪ! ᴀ {selected_character['rarity'][2:]} ᴄʜᴀʀᴀᴄᴛᴇʀ ʜᴀs ᴀᴘᴘᴇᴀʀᴇᴅ!</b>\n
<b>ᴀᴅᴅ ʜᴇʀ ᴛᴏ ʏᴏᴜʀ ʜᴀʀᴇᴍ ʙʏ sᴇɴᴅɪɴɢ</b>\n<b>/kawaii ɴᴀᴍᴇ</b>""",
            parse_mode='HTML'
        )
    else:
        # Agar image hai toh purana wala send_photo
        message = await context.bot.send_photo(
            chat_id=chat_id,
            photo=file_url,
            caption=f"""<b>{selected_character['rarity'][0]} ᴋᴀᴡᴀɪ! ᴀ {selected_character['rarity'][2:]} ᴄʜᴀʀᴀᴄᴛᴇʀ ʜᴀs ᴀᴘᴘᴇᴀʀᴇᴅ!</b>\n
<b>ᴀᴅᴅ ʜᴇʀ ᴛᴏ ʏᴏᴜʀ ʜᴀʀᴇᴍ ʙʏ sᴇɴᴅɪɴɢ</b>\n<b>/kawaii ɴᴀᴍᴇ</b>""",
            parse_mode='HTML'
        )


    # Save the message link for retry/reference
    if update.effective_chat.type == "private":
        message_link = f"https://t.me/c/{chat_id}/{message.message_id}"
    else:
        message_link = f"https://t.me/{update.effective_chat.username}/{message.message_id}"
    character_message_links[chat_id] = message_link

# Schedule the "flew away" logic after 2 minutes
async def character_flew_away(context: CallbackContext):
    # Retrieve data from the job context
    job_data = context.job.context
    chat_id = job_data['chat_id']
    selected_character = job_data['selected_character']
    last_characters = job_data['last_characters']

    # Check if the character is still active
    if chat_id in last_characters and last_characters[chat_id] == selected_character:
        del last_characters[chat_id]  # Remove character from the list

        # Notify the user that the character flew away
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=selected_character['img_url'],
            caption=(
                f"<b>⏳ Time's up!</b>\n\n"
                f"The character <b>{selected_character['name']}</b> has flown away. 😭\n\n"
                f"Here are the details:"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📜 Info", callback_data=f"info_{selected_character['id']}")]
            ])
        )

# Schedule the job
def schedule_character_flew_away(context: CallbackContext, chat_id, selected_character, last_characters):
    context.job_queue.run_once(
        character_flew_away, 
        120,  # 2 minutes
        context={
            'chat_id': chat_id,
            'selected_character': selected_character,
            'last_characters': last_characters
        }
    )

# Callback function to handle the "Info" button
async def placeholder_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    # Extract the character ID from the callback data
    character_id = query.data.split("_")[1]

    # Retrieve the character details from the database
    character = await collection.find_one({"id": character_id})

    # Check if the character exists
    if character:
        # Reply with the character's details and image
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
        # Inform the user if the character is not found
        await query.message.reply_text(
            "<b>❌ Character not found!</b>",
            parse_mode="HTML"
        )    


async def guess(update: Update, context: CallbackContext) -> None:
    # SAFETY CHECK 2: User ya Message missing hone par crash na ho
    if not update.effective_user or not update.message:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    


    if chat_id not in last_characters:
        return

    # Check if the character has already been guessed
    if chat_id in first_correct_guesses:
        correct_guess_user = first_correct_guesses[chat_id]['user']
        seized_character = first_correct_guesses[chat_id]['character']
        time_guessed = first_correct_guesses[chat_id]['time']
        user_link = f'<a href="tg://user?id={correct_guess_user.id}">{correct_guess_user.first_name}</a>'
        await update.message.reply_text(
            f'🌟 This character <b>{kawaiied_character}</b> has already been kawaiied by {user_link}!\n'
            f'⏱️ Guessed at: <b>{time_guessed}</b>\n'
            f'🍵 Wait for the next character to spawn... 🌌',
            parse_mode='HTML'
        )
        return

    # Retrieve the user's guess
    guess = ' '.join(context.args).lower() if context.args else ''

    if "()" in guess or "&" in guess.lower():
        await update.message.reply_text(
            "🔒 Sorry, invalid input! Please avoid '&' and special characters.",
            parse_mode='Markdown'
        )
        return

    character = last_characters[chat_id]
    character_name = character['name'].lower()
    name_parts = character_name.split()

    if sorted(name_parts) == sorted(guess.split()) or any(part == guess for part in name_parts):
        time_sent = None
        if isinstance(sent_characters.get(chat_id), dict):
            time_sent = sent_characters[chat_id].get(character['id'], time.time())
        elif isinstance(sent_characters.get(chat_id), list):
            for entry in sent_characters[chat_id]:
                if isinstance(entry, dict) and entry.get('id') == character['id']:
                    time_sent = entry.get('time', time.time())
                    break

        if time_sent is None:
            time_sent = time.time()

        time_taken = time.time() - time_sent
        minutes, seconds = divmod(int(time_taken), 60)

        guessed_time_str = datetime.fromtimestamp(time_sent).strftime("%Y-%m-%d %H:%M:%S")

        if chat_id not in first_correct_guesses:
            first_correct_guesses[chat_id] = {'user': None, 'character': None, 'time': None}


        if user_id not in [user.id for user in first_correct_guesses[chat_id]]:
            first_correct_guesses[chat_id].append(update.effective_user)

            # Update user database
            user = await user_collection.find_one({'id': user_id})
            update_fields = {}

            if user:
                if hasattr(update.effective_user, 'username') and update.effective_user.username != user.get('username'):
                    update_fields['username'] = update.effective_user.username
                if update.effective_user.first_name != user.get('first_name'):
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

            group_user_total = await group_user_totals_collection.find_one({'user_id': user_id, 'group_id': chat_id})
            if group_user_total:
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
            f'✅ <b><a href="tg://user?id={user_id}">{escape(update.effective_user.first_name)}</a></b> You got a new character!\n\n'
            f'🌸 𝗡𝗔𝗠𝗘: <b>{last_characters[chat_id]["name"]}</b>\n'
            f'❇️ 𝗔𝗡𝗜𝗠𝗘: <b>{last_characters[chat_id]["anime"]}</b>\n'
            f'{last_characters[chat_id]["rarity"][0]} 𝗥𝗔𝗥𝗜𝗧𝗬: <b>{last_characters[chat_id]["rarity"]}</b>\n'
            f'⏱️ Time taken: <b>{minutes}m {seconds}s</b>',
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
                       )
    else:
        # Extract user input and remove the bot mention and command prefix
        user_input = update.message.text.strip()  # Full input with command
        command_parts = user_input.split(" ")  # Split based on spaces

        # Ignore the command and bot mention, take the guess part only
        if len(command_parts) > 1:
            user_guess = command_parts[-1].strip()  # Last part is user's guess
        else:
            user_guess = ""

        wrong_letter = user_guess

        # Prepare the retry message with a character link
        message_link = character_message_links.get(chat_id, "#")
        keyboard = [[InlineKeyboardButton("★ See Character ★", url=message_link)]]

        await update.message.reply_text(
                  f"❌ Wrong guess: '{wrong_letter}'!\n\nPlease try again.",
        reply_markup=InlineKeyboardMarkup(keyboard)
)
        
# Assuming rarity_map and rarity_active are predefined dictionaries
# rarity_map = {1: "Common", 2: "Rare", ...}
# rarity_active = {"Common": False, "Rare": True, ...}

AUTHORIZED_USER_ID = 5158013355
AUTHORIZED_USER_NAME = "my Sensei @Ayushboy1"

# Command to turn a rarity on
async def set_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text(
            f"Only {AUTHORIZED_USER_NAME} can use this command."
        )
        return
    try:
        rarity_number = int(context.args[0])
        rarity = rarity_map.get(rarity_number)
        
        if rarity in rarity_active:
            if not rarity_active[rarity]:
                rarity_active[rarity] = True
                await update.message.reply_text(f'Rarity {rarity} is now ON and will spawn from now on.')
            else:
                await update.message.reply_text(f'Rarity {rarity} is already ON.')
        else:
            await update.message.reply_text('Invalid rarity number.')
            
    except (IndexError, ValueError):
        await update.message.reply_text('Please provide a valid rarity number.')

# Command to turn a rarity off
async def set_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text(
            f"Only {AUTHORIZED_USER_NAME} can use this command."
        )
        return
    try:
        rarity_number = int(context.args[0])
        rarity = rarity_map.get(rarity_number)
        
        if rarity in rarity_active:
            if rarity_active[rarity]:
                rarity_active[rarity] = False
                await update.message.reply_text(f'Rarity {rarity} is now OFF and will not spawn from now on.')
            else:
                await update.message.reply_text(f'Rarity {rarity} is already OFF.')
        else:
            await update.message.reply_text('Invalid rarity number.')
            
    except (IndexError, ValueError):
        await update.message.reply_text('Please provide a valid rarity number.')

# Register handlers
application.add_handler(CommandHandler('set_on', set_on, block=False))
application.add_handler(CommandHandler('set_off', set_off, block=False))

# --- BOT START ---

async def start_bot():
    # 1. Pyrogram start 
    await shivuu.start()
    LOGGER.info("Pyrogram Client Started!")

    # 2. Saare Handlers register karo (Jo tune pehle likhe the)
    application.add_handler(CommandHandler(["kawaii"], guess, block=False))
    application.add_handler(MessageHandler(filters.ALL, message_counter, block=False))
    application.add_handler(CommandHandler('set_on', set_on, block=False))
    application.add_handler(CommandHandler('set_off', set_off, block=False))

    # 3. Telegram-Bot Application start 
    async with application:
        await application.initialize()
        await application.start()
        # polling start 
        await application.updater.start_polling(drop_pending_updates=True)
        LOGGER.info("Bot is now Online on Telegram!")
        
        # Ye line bot ko band hone se rokegi
        await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        # Loop ko manage karne ka sahi tarika
        asyncio.get_event_loop().run_until_complete(start_bot())
    except (KeyboardInterrupt, SystemExit):
        LOGGER.info("Bot Stopped!")
    except Exception as e:
        LOGGER.error(f"Error: {e}")
