from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shivu import shivuu as app, user_collection
import logging
import random

# Enhanced emojis and engaging text
ANIMATED_EMOJIS = ['✨', '🎉', '🌟', '🔥', '💖', '💫', '🎇', '🌈']
SUCCESS_EMOJIS = ['✅', '🏆', '🎯', '🥳', '🚀']
CANCEL_EMOJIS = ['❌', '⚠️', '🚫', '😔', '🔴']

# Rare character display enhancements
RARITY_EMOJIS = {
    'COMMON': ('⚪️', 'Common'),
    'MEDIUM': ('🔵', 'Medium'),
    'CHIBI': ('👶', 'Chibi'),
    'RARE': ('🟠', 'Rare'),
    'LEGENDARY': ('🟡', 'Legendary'),
    'EXCLUSIVE': ('💮', 'Exclusive'),
    'PREMIUM': ('🫧', 'Premium'),
    'LIMITED EDITION': ('🔮', 'Limited Edition'),
    'EXOTIC': ('🌸', 'Exotic'),
    'ASTRAL': ('🎐', 'Astral'),
    'VALENTINE': ('💞', 'Valentine')
}

if not hasattr(app, 'user_data'):
    app.user_data = {}

@app.on_message(filters.command("fav"))
async def fav(client: Client, message):
    user_id = message.from_user.id

    if len(message.command) < 2:
        await message.reply_text(
            f"{random.choice(CANCEL_EMOJIS)} **Oops! Invalid Usage!**\n"
            f"Use `/fav (waifu_id)` to set your favorite character.\n"
            f"**Example:** `/fav 42`."
        )
        return

    character_id = message.command[1]

    user = await user_collection.find_one({'id': user_id})
    if not user or 'characters' not in user:
        await message.reply_text(
            f"{random.choice(CANCEL_EMOJIS)} **No characters found!**\n"
            "Start your journey by capturing your first waifu!"
        )
        return

    # Look for the character in the user's collection
    character = next((c for c in user.get('characters', []) if str(c.get('id')) == character_id), None)
    
    if not character:
        await message.reply_text(
            f"{random.choice(CANCEL_EMOJIS)} **Character not found in your collection!**\n"
            "Try again with a valid ID."
        )
        return

    name = character.get('name', 'Unknown Name')
    anime = character.get('anime', 'Unknown Anime')
    rarity = character.get('rarity', 'Common').upper()
    rarity_emoji, rarity_display = RARITY_EMOJIS.get(rarity, ('', rarity))

    # We send the photo and store the character_id in the callback data itself
    confirmation_message = await message.reply_photo(
        photo=character['img_url'],
        caption=(
            f"💎 **Confirm Your Choice!** 💎\n\n"
            f"🎭 **Name:** `{name}`\n"
            f"⛩️ **Anime:** `{anime}`\n"
            f"🪄 **Rarity:** {rarity_emoji} `{rarity_display}`\n\n"
            f"⚡ Are you ready to set `{name}` as your favorite?\n"
            "Choose an option below:"
        ),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"fav_yes_{character_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"fav_no_{character_id}")
            ]
        ])
    )

    # FIXED: Changed .message_id to .id
    if not hasattr(app, 'user_data'):
        app.user_data = {}
    app.user_data.setdefault("fav_confirmations", {})
    app.user_data["fav_confirmations"][confirmation_message.id] = character_id

@app.on_callback_query(filters.regex(r"^fav_(yes|no)_(.+)"))
async def handle_fav_confirmation(client: Client, callback_query):
    # Extract data from the regex groups
    action = callback_query.matches[0].group(1)
    character_id = callback_query.matches[0].group(2)
    user_id = callback_query.from_user.id

    if action == "no":
        await callback_query.message.edit_caption(
            caption=f"{random.choice(CANCEL_EMOJIS)} **Operation cancelled.**",
            reply_markup=None
        )
        return

    # If action is 'yes'
    user = await user_collection.find_one({'id': user_id})
    character = next((c for c in user.get('characters', []) if str(c.get('id')) == character_id), None)

    if not character:
        await callback_query.answer("Character no longer in your collection!", show_alert=True)
        return

    await user_collection.update_one(
        {'id': user_id},
        {'$set': {'favorites': [character_id]}}
    )
    
    await callback_query.message.edit_caption(
        caption=(
            f"🌟 **Success!** `{character['name']}` is now your favorite character! "
            f"{random.choice(SUCCESS_EMOJIS)}\n\n"
            f"Enjoy your journey with **{character['name']}!**"
        ),
        reply_markup=None
    )


@app.on_message(filters.command("unfav"))
async def unfav(client: Client, message):
    user_id = message.from_user.id
    
    # Check if the user even has a favorite set
    user = await user_collection.find_one({'id': user_id, 'favorites': {'$exists': True}})
    
    if not user:
        await message.reply_text(
            f"{random.choice(CANCEL_EMOJIS)} **You don't have a favorite character set!**"
        )
        return

    # Unset the favorites field
    await user_collection.update_one({'id': user_id}, {'$unset': {'favorites': ''}})
    
    await message.reply_text(
        f"{random.choice(ANIMATED_EMOJIS)} **Favorite reset!**\n"
        f"You can now choose a new favorite waifu!"
    ) # Added the missing closing parenthesis here
