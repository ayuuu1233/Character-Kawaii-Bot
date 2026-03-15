import urllib.request
import os
from pymongo import ReturnDocument
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, collection, db, user_collection
from html import escape

async def check_character(update: Update, context: CallbackContext) -> None:
    try:
        # Callback query hai ya direct message, check karein
        query = update.callback_query
        
        if query:
            args = context.args
        else:
            args = context.args

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
        
        # Count globally seized times
        global_count = await user_collection.count_documents({'characters.id': character['id']})

        response_message = (
            f"<b>🧋 ᴏᴡᴏ! ᴄʜᴇᴄᴋ ᴏᴜᴛ ᴛʜɪs ᴄʜᴀʀᴀᴄᴛᴇʀ !!</b>\n\n"
            f"ID: {character['id']}\n"
            f"Name: <b>{escape(character['name'])}</b>\n"
            f"Anime: <b>{escape(character['anime'])}</b>\n"
            f"Rarity: <b>{character['rarity']}</b>\n\n"
            f"🌐 <b>Globally Seized:</b> {global_count}x"
        )

        # Top Grabbers fetch karein
        cursor = user_collection.find(
            {'characters.id': character_id},
            {'id': 1, 'first_name': 1, 'last_name': 1, 'username': 1, 'profile_name': 1, 'characters.$': 1}
        )

        users = await cursor.to_list(length=None)
        # Sort manually by count since $ projection is used
        users.sort(key=lambda x: x['characters'][0].get('count', 1), reverse=True)

        per_page = 10
        total_pages = (len(users) + per_page - 1) // per_page
        if total_pages == 0: total_pages = 1
        
        start_index = (page - 1) * per_page
        users_page = users[start_index:start_index + per_page]

        if users_page:
            response_message += f"\n\n🌐 <b>Top Grabbers (Page {page}/{total_pages}):</b>\n\n"
            for user in users_page:
                full_name = user.get('profile_name') or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get('username', 'Unknown User')
                # Mention link
                mention = f"<a href='tg://user?id={user['id']}'>{escape(full_name)}</a>"
                response_message += f"• {mention}\n"
        else:
            response_message += "\n\nNo users found with this character."
        
        # Pagination buttons
        keyboard_buttons = []
        if page > 1:
            keyboard_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{character_id}_{page - 1}"))
        if page < total_pages:
            keyboard_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{character_id}_{page + 1}"))

        keyboard = InlineKeyboardMarkup([keyboard_buttons]) if keyboard_buttons else None

        if query:
            await query.edit_message_caption(caption=response_message, parse_mode="HTML", reply_markup=keyboard)
        else:
            if character.get("video_url"):
                await context.bot.send_video(
                    chat_id=update.effective_chat.id,
                    video=character["video_url"],
                    caption=response_message,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=character["img_url"],
                    caption=response_message,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
    
    except Exception as e:
        print(f"Error in check_character: {e}")
        if not update.callback_query:
            await update.message.reply_text(f'Error: {str(e)}')

async def handle_callback_query(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data
    try:
        if data.startswith("page_"):
            _, char_id, page = data.split('_')
            context.args = [char_id, page]
            await check_character(update, context)
            await query.answer()
    except Exception as e:
        print(f"Error in handle_callback_query: {e}")

# Handlers
application.add_handler(CommandHandler('check', check_character, block=False))
application.add_handler(CallbackQueryHandler(handle_callback_query, pattern='^page_', block=False))
