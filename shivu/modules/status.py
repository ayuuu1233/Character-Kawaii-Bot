import os
import random
import html
import asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from shivu import application, OWNER_ID, user_collection, top_global_groups_collection, group_user_totals_collection
from shivu import sudo_users as SUDO_USERS
from shivu import collection

async def get_global_rank(username: str) -> int:
    pipeline = [
        {"$match": {"characters": {"$exists": True, "$ne": []}}},
        {"$project": {"username": 1, "first_name": 1, "character_count": {"$size": "$characters"}}},
        {"$sort": {"character_count": -1}}
    ]
    cursor = user_collection.aggregate(pipeline)
    leaderboard_data = await cursor.to_list(length=None)
    total_users = await user_collection.count_documents({})
    for i, user in enumerate(leaderboard_data, start=1):
        if user.get('username') == username:
            return i, total_users
    return 0, total_users

async def my_profile(update: Update, context: CallbackContext):
    if update.message:
        loading_message = await update.message.reply_animation(
            animation="https://files.catbox.moe/gujd6o.mp4",  # Replace with an appropriate GIF URL
            caption="🌟 Fetching your profile details, please wait..."
        )

        user_id = update.effective_user.id
        user_data = await user_collection.find_one({'id': user_id})

        if user_data:
            user_first_name = user_data.get('first_name', 'Unknown')
            user_balance = user_data.get('balance', 0)
            total_characters = await collection.count_documents({})
            characters_count = len(user_data.get('characters', []))
            character_percentage = (characters_count / total_characters) * 100 if total_characters else 0

            username = user_data.get('username', 'Not set')
            global_rank, total_users = await get_global_rank(username)

            # Progress bar with percentages
            progress_bar_length = 10
            filled_blocks = int((character_percentage / 100) * progress_bar_length)
            progress_bar = f"[{'■' * filled_blocks}{'□' * (progress_bar_length - filled_blocks)} {character_percentage:.2f}%]"

            user_tag = f"<a href='tg://user?id={user_id}'>{html.escape(user_first_name)}</a>"
            user_bio = user_data.get('bio', "Bio not set")

            rarity_counts = {
                "⚪️ Common": 0,
                "🔮 Limited Edition": 0,
                "🫧 Premium": 0,
                "🌸 Exotic": 0,
                "💮 Exclusive": 0,
                "👶 Chibi": 0,
                "🟡 Legendary": 0,
                "🟠 Rare": 0,
                "🔵 Medium": 0,
                "🎐 Astral": 0,
                "💞 Valentine": 0
            }

            for char in user_data.get('characters', []):
                rarity = char.get('rarity', '⚪️ Common')
                if rarity in rarity_counts:
                    rarity_counts[rarity] += 1

            rarity_message = "\n".join([
                f"  ❍ {rarity} ➥ {count}" for rarity, count in rarity_counts.items()
            ])

            profile_message = (
                f"❖ <b>{user_tag} ɪɴғᴏʀᴍᴀᴛɪᴏɴ</b> ❖\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"⬤ <b>ᴜsᴇʀ ɪᴅ</b> ➥ <code>{user_id}</code>\n"
                f"⬤ <b>ᴍᴇɴᴛɪᴏɴ</b> ➥ {user_tag}\n"
                f"⬤ <b>ᴄᴏɪɴ</b> ➥ {user_balance}\n"
                f"⬤ <b>ᴄʜᴀʀᴀᴄᴛᴇʀ ᴄᴏʟʟᴇᴄᴛɪᴏɴ</b> ➥ {characters_count}/{total_characters}\n"
                f"⬤ <b>ᴘʀᴏɢʀᴇss ʙᴀʀ</b> ➥ {progress_bar}\n"
                f"⬤ <b>ɢʟᴏʙᴀʟ ʀᴀɴᴋ</b> ➥ {global_rank}/{total_users}\n"
                f"⬤ <b>ʀᴀʀɪᴛʏ ᴄᴏᴜɴᴛ</b> ➥\n{rarity_message}\n"
                f"━━━━━━━━━━━━━━━━━━━━━"
            )

            media_id = user_data.get("custom_photo")
            media_type = user_data.get("custom_media_type", "photo")

            close_button = InlineKeyboardButton("🔒 Close", callback_data="close")
            keyboard = InlineKeyboardMarkup([[close_button]])

            try:
                if media_id:
                    if media_type == "photo":
                        await update.message.reply_photo(media_id, caption=profile_message, reply_markup=keyboard, parse_mode='HTML')
                    elif media_type == "video":
                        await update.message.reply_video(media_id, caption=profile_message, reply_markup=keyboard, parse_mode='HTML')
                    elif media_type == "animation":
                        await update.message.reply_animation(media_id, caption=profile_message, reply_markup=keyboard, parse_mode='HTML')
                    elif media_type == "sticker":
                        await update.message.reply_sticker(media_id)
                        await update.message.reply_text(profile_message, reply_markup=keyboard, parse_mode='HTML')
                else:
                    profile_pic = update.effective_user.photo
                    if profile_pic:
                        await update.message.reply_photo(profile_pic.file_id, caption=profile_message, reply_markup=keyboard, parse_mode='HTML')
                    else:
                        await update.message.reply_text(profile_message, reply_markup=keyboard, parse_mode='HTML')
                await loading_message.delete()
            except Exception as e:
                print(f"Error in sending message: {e}")
        else:
            await update.message.reply_text("⚠️ Unable to retrieve your profile data.")
    else:
        print("No message to reply to.")

async def set_profile_pic(update: Update, context: CallbackContext):
    reply = update.message.reply_to_message
    user_id = update.effective_user.id
    if reply and (reply.photo or reply.video or reply.animation or reply.sticker):
        if reply.photo:
            media_id, media_type = reply.photo[-1].file_id, "photo"
        elif reply.video:
            media_id, media_type = reply.video.file_id, "video"
        elif reply.animation:
            media_id, media_type = reply.animation.file_id, "animation"
        elif reply.sticker:
            media_id, media_type = reply.sticker.file_id, "sticker"
        await user_collection.update_one(
            {'id': user_id},
            {'$set': {'custom_photo': media_id, 'custom_media_type': media_type}},
            upsert=True
        )
        await update.message.reply_text("✅ Profile picture updated successfully!")
    else:
        await update.message.reply_text("⚠️ Please reply with an image, video, GIF, or sticker.")
        
application.add_handler(CommandHandler("status", my_profile))
application.add_handler(CommandHandler("setpic", set_profile_pic))

async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == "close":
        try:
            await query.message.delete()
        except Exception as e:
            print(f"Error in deleting message: {e}")
    await query.answer()

application.add_handler(CallbackQueryHandler(button))
