import urllib.request
import os
from pymongo import ReturnDocument
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, collection, db, user_collection
from html import escape

async def check_character(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        # Agar button dabaya hai toh callback_query se data uthayenge, nahi toh command args se
        args = context.args if not query else context.args

        if not args or not args[0].isdigit():
            if not query:
                await update.message.reply_text('Incorrect format. Please use: /check character_id [page_number]')
            return

        character_id = args[0]
        page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1

        # Character details fetch karein
        character = await collection.find_one({'id': character_id})
        if not character:
            if query:
                await query.answer("Wrong ID.", show_alert=True)
            else:
                await update.message.reply_text('Wrong id.')
            return
        
        global_count = await user_collection.count_documents({'characters.id': character['id']})

        response_message = (
            f"<b>🧋 ᴏᴡᴏ! ᴄʜᴇᴄᴋ ᴏᴜᴛ ᴛʜɪs ᴄʜᴀʀᴀᴄᴛᴇʀ !!</b>\n\n"
            f"ID: {character['id']}\n"
            f"Name: <b>{escape(character['name'])}</b>\n"
            f"Anime: <b>{escape(character['anime'])}</b>\n"
            f"Rarity: <b>{character['rarity']}</b>\n\n"
            f"🌐 <b>Globally Seized:</b> {global_count}x"
        )

        # Top Grabbers logic
        cursor = user_collection.find(
            {'characters.id': character_id},
            {'id': 1, 'first_name': 1, 'last_name': 1, 'username': 1, 'profile_name': 1, 'characters.$': 1}
        )
        users = await cursor.to_list(length=None)
        users.sort(key=lambda x: x['characters'][0].get('count', 1), reverse=True)

        per_page = 10
        total_pages = max((len(users) + per_page - 1) // per_page, 1)
        start_index = (page - 1) * per_page
        users_page = users[start_index:start_index + per_page]

        if users_page:
            response_message += f"\n\n🌐 <b>Top Grabbers (Page {page}/{total_pages}):</b>\n\n"
            for user in users_page:
                full_name = user.get('profile_name') or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get('username', 'Unknown User')
                mention = f"<a href='tg://user?id={user['id']}'>{escape(full_name)}</a>"
                response_message += f"• {mention}\n"
        else:
            response_message += "\n\nNo users found with this character."
        
        keyboard_buttons = []
        if page > 1:
            keyboard_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{character_id}_{page - 1}"))
        if page < total_pages:
            keyboard_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{character_id}_{page + 1}"))

        keyboard = InlineKeyboardMarkup([keyboard_buttons]) if keyboard_buttons else None

        # --- VIDEO VS PHOTO LOGIC (YEH FIX KIYA HAI) ---
        media_url = character.get("img_url")
        is_video = media_url.endswith(('.mp4', '.mkv', '.webm', '.mov')) if media_url else False

        if query:
            # Caption update karein buttons ke liye
            await query.edit_message_caption(caption=response_message, parse_mode="HTML", reply_markup=keyboard)
        else:
            if is_video:
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=media_url,
                    caption=response_message,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=media_url,
                    caption=response_message,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
    
    except Exception as e:
        print(f"Error in check_character: {e}")

async def handle_callback_query(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data
    if data.startswith("page_"):
        _, char_id, page = data.split('_')
        context.args = [char_id, page]
        await check_character(update, context)
        await query.answer()

# Handlers register karein
application.add_handler(CommandHandler('check', check_character, block=False))
application.add_handler(CallbackQueryHandler(handle_callback_query, pattern='^page_', block=False))
