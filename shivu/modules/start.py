import asyncio
from html import escape
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackContext, CommandHandler, CallbackQueryHandler
from shivu import db, GROUP_ID, OWNER_ID 
from shivu import application, GROUP_ID, user_collection
collection = db['total_pm_users']
# Define your sudo users' IDs here
sudo_user_ids = [5158013355]  # Replace with actual user IDs of the sudo users
SUPPORT_GROUP_ID = "@upper_moon_chat"  # Replace with the actual group username or ID
IMAGE_URL = "https://files.catbox.moe/sn06ft.jpg"  # Replace with the actual image URL

async def notify_sudo_users(application: Application):
    """Notify sudo users that the bot has restarted."""
    message = "The bot has restarted successfully!"
    for user_id in sudo_user_ids:
        try:
            await application.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Failed to send restart notification to user {user_id}: {e}")

def escape_markdown(text: str) -> str:
    """Escape characters in MarkdownV2."""
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username
    args = context.args
    referring_user_id = None

    try:
        # Check if user has joined the support group
        member_status = await context.bot.get_chat_member(SUPPORT_GROUP_ID, user_id)
        if member_status.status == 'left':
            join_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("๏ Join Support ๏", url=f"https://t.me/{SUPPORT_GROUP_ID.lstrip('@')}")]
            ])
            await update.message.reply_photo(
                photo=IMAGE_URL,
                caption="๏ It appears you haven't joined our Support Group yet. Please join to access my features!",
                reply_markup=join_button
            )
            return
    except Exception as e:
        print(f"Error checking user membership in support group: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")
        return

    # Animated emojis
    emojis = ["✨", "🚀", "🎉"]
    for emoji in emojis:
        emoji_message = await update.message.reply_text(emoji)
        await asyncio.sleep(1.0)  # Wait for 1 second between emojis
        await emoji_message.delete()

    # "Starting..." animation message
    starting_message = await update.message.reply_text("Starting...")
    await asyncio.sleep(1.0)  # Wait for 1 second before deleting
    await starting_message.delete()

    # Handle referral if present
    if args and args[0].startswith('r_'):
        referring_user_id = int(args[0][2:])

    user_data = await user_collection.find_one({"id": user_id})

    if user_data is None:
        new_user = {
            "id": user_id,
            "first_name": first_name,
            "username": username,
            "tokens": 500,
            "characters": []
        }
        await user_collection.insert_one(new_user)

        if referring_user_id:
            referring_user_data = await user_collection.find_one({"id": referring_user_id})
            if referring_user_data:
                await user_collection.update_one({"id": referring_user_id}, {"$inc": {"tokens": 1000}})
                referrer_message = f"{first_name} used your referral link and you've received 1000 tokens!"
                try:
                    await context.bot.send_message(chat_id=referring_user_id, text=referrer_message)
                except Exception as e:
                    print(f"Failed to send referral message: {e}")

        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"🫧 #ɴᴇᴡ ᴜsᴇʀ ᴊᴏɪɴᴇᴅ \n\n"
                 f"🌿 User: <a href='tg://user?id={user_id}'>{first_name}</a>",
            parse_mode='HTML'
        )
    else:
        # Update user info if it has changed
        if user_data['first_name'] != first_name or user_data['username'] != username:
            await user_collection.update_one(
                {"id": user_id},
                {"$set": {"first_name": first_name, "username": username}}
            )

    # Send DM to user with profile picture and details
    try:
        profile_picture = await context.bot.get_user_profile_photos(user_id)
        photo = profile_picture.photos[0][0].file_id if profile_picture.total_count > 0 else None

        button = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{first_name}", url=f"tg://user?id={user_id}")
        ]])

        await context.bot.send_photo(
            chat_id=user_id,
            photo=photo or DEFAULT_IMAGE_URL,  # Fallback to a default image if no profile picture exists
            caption=f"ㅤ<b>ʜᴀs sᴛᴀʀᴛᴇᴅ ʙᴏᴛ.</b>\n\n"
                    f"• <b>ɴᴀᴍᴇ :</b> {first_name}\n"
                    f"• <b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{username if username else 'N/A'}\n"
                    f"• <b>ɪᴅ :</b> <code>{user_id}</code>\n\n"
                    f"Thanks for starting the bot!",
            reply_markup=button,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Error sending DM to user: {e}")

    if update.effective_chat.type == "private":
        bot_id = "8748211605"  # Replace with the actual bot ID
        bot_name = "『 ᴄʜᴀʀᴀᴄᴛᴇʀ ᴋᴀᴡᴀɪɪ ʙᴏᴛ 』"  # Replace with the bot's display name

        caption = (
            f"┬── ⋅ ⋅ ───── ᯽ ───── ⋅ ⋅ ──┬\n"
            f"  Kση'ηɪᴄʜɪᴡᴧ <a href='tg://user?id={user_id}'>{first_name}</a>!\n"
            f"┴── ⋅ ⋅ ───── ᯽ ───── ⋅ ⋅ ──┴\n\n"
            f"────────────────────────\n"
            f"│ ᴡєʟᴄσϻє ᴛσ <a href='tg://user?id={bot_id}'>{bot_name}</a>, ʏσυꝛ ғʀɪєηᴅʟʏ ᴡᴧiғᴜ ᴋᴀᴡᴀɪɪ ʙσᴛ ☄ │\n"
            f"────────────────────────\n\n"
            f"━━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ \n"
            f" ❖ ᴡᴧɪғᴜ ᴋᴀᴡᴀɪɪ ʙσᴛ ᴡɪʟʟ  ᴧυᴛσϻᴧᴛɪᴄᴧʟʟʏ sᴘᴧᴡη ᴧ ηєᴡ  ᴡᴧɪғυ ɪη ʏσυʀ ᴄʜᴧᴛ ᴀғᴛєʀ єᴠєʀʏ  100 ϻєssᴧɢєs ʙʏ ᴅєғᴧυʟᴛ.\n"
            f" ❖ ʏσᴜ ᴄᴧη ᴧʟsσ ᴄυsᴛσᴍɪᴢє ᴛʜє  sᴘᴧᴡη ʀᴧᴛє ᴧηᴅ σᴛʜєꝛ sєᴛᴛɪηɢs  ᴛσ ʏσυʀ ʟɪᴋɪηɢ.\n"
            f"━━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ \n\n"
            f"──────────────────────\n"
            f"❖ ʜσᴡ ᴛσ υsє ᴍє:\n"
            f" sɪϻᴘʟʏ ᴧᴅᴅ ϻє ᴛσ ʏσυʀ ɢꝛσυᴘ.\n"
            f"──────────────────────\n"
        )

        keyboard = [
            [InlineKeyboardButton("✜ ᴧᴅᴅ ϻє ɪη ʏσυʀ ɢʀσυᴘ ✜", url=f'https://t.me/{context.bot.username}?startgroup=new')],
            [InlineKeyboardButton("˹ sυᴘᴘσʀᴛ ˼", url=f'https://t.me/{SUPPORT_GROUP_ID.lstrip("@")}'),
             InlineKeyboardButton("˹ ᴜᴘᴅᴧᴛєs ˼", url='https://t.me/Seizer_updates')],
            [InlineKeyboardButton("✧ʜᴇʟᴘ✧", callback_data='help')],
      ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        video_url = "https://telegra.ph/file/40254b3883dfcaec52120.mp4"
        sticker_url = "CAACAgUAAxkBAAEBeVpm-jtB-lkO8Oixy5SZHTAy1Ymp4QACEgwAAv75EFbYc5vQ3hQ1Ph4E"
        
        await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=sticker_url)
        await context.bot.send_video(chat_id=update.effective_chat.id, video=video_url, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
    else:
        keyboard = [
            [InlineKeyboardButton("Ⰶ ᴘᴍ ᴍᴇ Ⰶ", url=f'https://t.me/{context.bot.username}?start=true')],
            [InlineKeyboardButton("ꔷ sυᴘᴘσʀᴛ ꔷ", url=f'https://t.me/{SUPPORT_GROUP_ID.lstrip("@")}'),
             InlineKeyboardButton("ꔷ ᴜᴘᴅᴧᴛєs ꔷ", url='https://t.me/upper_moon_chat')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        video_url = "https://telegra.ph/file/0b2e8e33d07a0d0e5914f.mp4"
        await context.bot.send_video(chat_id=update.effective_chat.id, video=video_url, caption=f"👋 Hi there, <a href='tg://user?id={user_id}'>{first_name}</a>!\n\n✨ I'm online and ready to assist!", reply_markup=reply_markup, parse_mode='HTML')
        
async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    # Define the initial caption
    initial_caption = """Welcome to the Bot!

Choose an option:
- Help for commands
- Enjoy exploring features!

Use the buttons below to navigate."""
    
    if query.data == 'help':
        help_keyboard = [
            [InlineKeyboardButton("Basic Commands", callback_data='basic')],
            [InlineKeyboardButton("Game Commands", callback_data='game')],
            [InlineKeyboardButton("⤾ Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(help_keyboard)
        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            caption="Choose a category to explore the commands.",
            reply_markup=reply_markup,
            parse_mode='markdown'
        )

    elif query.data == 'basic':
        basic_text = """
***➲ ʙᴇʟᴏᴡ ᴀʀᴇ ᴛʜᴇ ʙᴀsɪᴄ ᴄᴏᴍᴍᴀɴᴅs ғᴏʀ ᴜsᴇʀs::***

━─━─── ᴄᴏᴍᴍᴀɴᴅs────━─━
◈ /seize ➵ ᴛᴏ sᴇɪᴢᴇ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ
◈ /hmode ➵ ᴛᴏ ᴄʜᴀɴɢᴇ ʜᴀʀᴇᴍ ᴍᴏᴅᴇ
◈ /post ➵ ᴛᴏ ᴘᴏsᴛ ᴄʜᴀʀᴀᴄᴛᴇʀ 
◈ /placebid ➵ ᴘʟᴀᴄᴇ ᴀ ʙɪᴅ ᴏɴ ᴀɴ ᴀᴜᴄᴛɪᴏɴ 
◈ /bonus ➵ ᴄᴏʟʟᴇᴄᴛ ʏᴏᴜʀ ʙᴏɴᴜs ʀᴇᴡᴀʀᴅs
◈ /wclaim ➵ ᴄʟᴀɪᴍ ʏᴏᴜʀ ᴅᴀɪʟʏ ᴄʜᴀʀᴀᴄᴛᴇʀ
◈ /claim ➵ ᴄʟᴀɪᴍ ᴀɴᴏᴛʜᴇʀ ᴄʜᴀʀᴀᴄᴛᴇʀ  
◈ /check ➵ ᴛᴏ ᴄʜᴇᴄᴋ ᴄʜᴀʀᴀᴄᴛᴇʀ ɪɴғᴏ
◈ /fav ➵ ᴛᴏ ᴍᴀᴋᴇ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ ʏᴏᴜ ғᴀᴠᴏᴜʀɪᴛᴇ  
◈ /gift ➵ ᴛᴏ ɢɪғᴛ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ  
◈ /trade ➵ ᴛᴏ ᴛʀᴀᴅᴇ ᴄʜᴀʀᴀᴄᴛᴇʀs
◈ /harem ➵ ᴛᴏ sᴇᴇ ʏᴏᴜʀ sᴇɪᴢᴢᴇᴅ ᴄʜᴀʀᴀᴄᴛᴇʀs 
◈ /gtop ➵ ᴛᴏ sᴇᴇ ᴛᴏᴘ sᴇɪᴢᴇʀs  
◈ /ctop ➵ ᴛᴏ sᴇᴇ ᴛᴏᴘ ᴄʜᴀᴛ sᴇɪᴢᴇʀs  
◈ /status ➵ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ʙᴏᴛ sᴛᴀᴛᴜs 
◈ /store ➵ ᴛᴏ ᴏᴘᴇɴ ᴄʜᴀʀᴀᴄᴛᴇʀ ʙᴜʏ ᴀɴᴅ sᴇʟʟ sᴛᴏʀᴇ  
◈ /changetime ➵ ᴛᴏ ᴄʜᴀɴɢᴇ ᴄʜᴀʀᴀᴄᴛᴇʀ sᴘᴀᴡɴ ᴛɪᴍᴇ  
━─━─── ᴄᴏᴍᴍᴀɴᴅs────━─━
"""
        help_keyboard = [[InlineKeyboardButton("⤾ Back", callback_data='help')]]
        reply_markup = InlineKeyboardMarkup(help_keyboard)
        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            caption=basic_text,
            reply_markup=reply_markup,
            parse_mode='markdown'
        )

    elif query.data == 'game':
        game_text = """
***➲ ʙᴇʟᴏᴡ ᴀʀᴇ ᴛʜᴇ ɢᴀᴍᴇ ᴄᴏᴍᴍᴀɴᴅs ғᴏʀ ᴜsᴇʀs***

━─━─── ᴄᴏᴍᴍᴀɴᴅs────━─━
◉ /propose ➸ ᴘʀᴏᴘᴏsᴇ ᴛᴏ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ  
◉ /fight ➸ ғɪɢʜᴛ sᴜᴋᴜɴᴀ ᴠ/s ɢᴏᴊᴏ 
◉ /marry ➸ ᴍᴀʀʀʏ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ  
◉ /roll ➸ ʀᴏʟʟ ғᴏʀ ᴀ ʀᴀɴᴅᴏᴍ ᴄʜᴀʀᴀᴄᴛᴇʀ
◉ /crime ➸ ᴄᴏᴍᴍɪᴛ ᴀ ᴄʀɪᴍᴇ
◉ /explore ➸ ᴇxᴘʟᴏʀᴇ ᴄʜᴀʀᴀᴄᴛᴇʀs 
◉ /pass ➸ ʙᴜʏ ᴘᴀss ᴀɴᴅ ᴄʟᴀɪᴍ ʀᴇᴡᴀʀᴅs 
◉ /hunt ➸ ᴛᴏ ʜᴜɴᴛ
◉ /bal ➸ ᴄʜᴇᴄᴋ ʏᴏᴜʀ ʙᴀʟᴀɴᴄᴇ  
◉ /pay ➸ ᴘᴀʏ ᴀɴᴏᴛʜᴇʀ ᴜsᴇʀ 
◉ /football ➸ ᴘʟᴀʏ ᴀ ғᴏᴏᴛʙᴀʟʟ ɢᴀᴍᴇ { ʙʟᴜᴇ ʟᴏᴏᴋ ʙᴀsᴇᴅ }
◉ /basketball ➸ ᴘʟᴀʏ ᴀ ʙᴀsᴋᴇᴛʙᴀʟʟ { ʜᴀɪᴋʏᴜᴜ ʙᴀsᴇᴅ }  
◉ /guess ➸ ᴄʜᴀʀᴀᴄᴛᴇʀ ɢᴜᴇss   
◉ /quiz ➸ ᴀɴɪᴍᴇ ǫᴜɪᴢ   
◉ /tokens ➸ ᴠɪᴇᴡ ʏᴏᴜʀ ᴛᴏᴋᴇɴs  
◉ /beastshop ➸ sʜᴏᴘ ғᴏʀ ʙᴇᴀsᴛs
━─━─── ᴄᴏᴍᴍᴀɴᴅs────━─━ 
"""
        help_keyboard = [[InlineKeyboardButton("⤾ Back", callback_data='help')]]
        reply_markup = InlineKeyboardMarkup(help_keyboard)
        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            caption=game_text,
            reply_markup=reply_markup,
            parse_mode='markdown'
        )

    elif query.data == 'back':
        # Back to the main menu
        start_keyboard = [
            [InlineKeyboardButton("Help", callback_data='help')],
        ]
        reply_markup = InlineKeyboardMarkup(start_keyboard)
        await context.bot.edit_message_caption(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
            caption=initial_caption,
            reply_markup=reply_markup,
            parse_mode='markdown'
        )

application.add_handler(CallbackQueryHandler(button, pattern='^help$|^basic$|^game$|^back$', block=False))
start_handler = CommandHandler('start', start, block=False)
application.add_handler(start_handler)

async def main():
    await application.initialize()
    await application.start()
    asyncio.create_task(notify_sudo_users(application))
    await application.updater.start_polling()
    await application.idle()

if __name__ == '__main__':
    asyncio.run(main())
