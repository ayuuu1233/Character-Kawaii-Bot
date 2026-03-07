from pyrogram import filters, Client, types as t
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, ChatAdminRequired
from pyrogram.enums import ChatMemberStatus
from shivu import user_collection, shivuu as bot
import asyncio
import logging

# ---------------- SETTINGS ---------------- #
CHANNEL_ID = -1002208875879
CHANNEL_USERNAME = "seize_market"
GROUP_URL = "https://t.me/Dyna_community"

# ---------------- LOGGING ---------------- #
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ---------------- UTIL FUNCTIONS ---------------- #
async def check_channel_membership(user_id, channel_username):
    """Check if a user is member of the channel."""
    try:
        member_status = await bot.get_chat_member(channel_username, user_id)
        return member_status.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except UserNotParticipant:
        return False
    except ChatAdminRequired:
        logging.warning("Bot needs to be admin in channel to check membership.")
        return False
    except Exception as e:
        logging.error(f"Error checking channel membership: {e}")
        return False

async def update_balance(user_id, amount):
    """Add or subtract balance for a user."""
    user_data = await user_collection.find_one({'id': user_id}) or {'id': user_id, 'balance': 0}
    user_data['balance'] = user_data.get('balance', 0) + amount
    await user_collection.update_one({'id': user_id}, {'$set': user_data}, upsert=True)

async def send_with_retry(func, *args, retries=3, **kwargs):
    """Retry sending message if RANDOM_ID_DUPLICATE occurs."""
    attempt = 0
    while attempt < retries:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if "RANDOM_ID_DUPLICATE" in str(e):
                attempt += 1
                await asyncio.sleep(1)
            else:
                raise e
    raise Exception("Failed to send message after retries")

# ---------------- COMMAND: POST CHARACTER ---------------- #
@bot.on_message(filters.command("post"))
async def post_character(_, message: t.Message):
    user_id = message.from_user.id
    args = message.command

    # Check membership
    if not await check_channel_membership(user_id, CHANNEL_USERNAME):
        return await message.reply_text(
            "🚫 You must join our official channel to post characters!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")]
            ])
        )

    # Validate args
    if len(args) != 3:
        return await message.reply_text("❓ Usage: `/post {char_id} {price}`. Example: `/post c001 500`")

    character_id, price_str = args[1], args[2]

    try:
        price_in_balance = int(price_str)
    except ValueError:
        return await message.reply_text("💸 Price must be a valid integer.")

    # Fetch user data
    user_data = await user_collection.find_one({'id': user_id})
    if not user_data or 'characters' not in user_data or not user_data['characters']:
        return await message.reply_text("😢 You don't own any characters yet.")

    # Find character
    character = next((c for c in user_data['characters'] if c['id'] == character_id), None)
    if not character:
        return await message.reply_text("🚫 Character not found! Make sure you own it.")

    # Safe image
    photo_url = character.get('img_url') or 'https://i.imgur.com/1M0qv.gif'

    # Post caption
    caption = (
        f"🥂 {message.from_user.mention} is selling a character!\n\n"
        f"⚡ **Name**: {character['name']}\n"
        f"⚜️ **Anime**: {character['anime']}\n"
        f"❄️ **Rarity**: {character['rarity']}\n"
        f"💵 **Price**: {price_in_balance} balance\n\n"
        "💡 *Grab it before someone else does!*"
    )

    # Inline Buy button (using | as delimiter for safety)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Buy It", callback_data=f"buy|{user_id}|{character_id}|{price_in_balance}")]
    ])

    # Send post with retry
    try:
        post_msg = await send_with_retry(
            bot.send_photo,
            chat_id=f"@{CHANNEL_USERNAME}",
            photo=photo_url,
            caption=caption,
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Error posting character: {e}")
        return await message.reply_text("😓 Failed to post character. Try again later.")

    post_message_id = getattr(post_msg, 'id', getattr(post_msg, 'message_id', None))

    await message.reply_text(
        f"🎉 Your character has been posted!\n[👀 View Post](https://t.me/{CHANNEL_USERNAME}/{post_message_id})",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 View Post", url=f"https://t.me/{CHANNEL_USERNAME}/{post_message_id}")]
        ])
    )

# ---------------- CALLBACK: BUY CHARACTER ---------------- #
@bot.on_callback_query(filters.regex(r"buy\|(\d+)\|(.+)\|(\d+)"))
async def handle_buy(_, query: t.CallbackQuery):
    try:
        data = query.data.split('|')
        if len(data) != 4:
            return await query.answer("🚫 Invalid callback data.", show_alert=True)

        seller_id = int(data[1])
        character_id = data[2]
        price_in_balance = int(data[3])
        buyer_id = query.from_user.id

        if buyer_id == seller_id:
            return await query.answer("🛑 You cannot buy your own character!", show_alert=True)

        # Fetch buyer and seller
        buyer_data = await user_collection.find_one({'id': buyer_id}) or {'balance': 0, 'characters': []}
        seller_data = await user_collection.find_one({'id': seller_id}) or {'balance': 0, 'characters': []}

        if buyer_data.get('balance', 0) < price_in_balance:
            return await query.answer("💸 Insufficient balance!", show_alert=True)

        # Check character exists
        character = next((c for c in seller_data.get('characters', []) if c['id'] == character_id), None)
        if not character:
            return await query.answer("❌ Character is no longer available!", show_alert=True)

        # Transfer character
        seller_data['characters'].remove(character)
        buyer_data.setdefault('characters', []).append(character)

        # Update balances using utility
        await update_balance(buyer_id, -price_in_balance)
        await update_balance(seller_id, price_in_balance)

        # Save updated characters
        await user_collection.update_one({'id': buyer_id}, {'$set': {'characters': buyer_data['characters']}}, upsert=True)
        await user_collection.update_one({'id': seller_id}, {'$set': {'characters': seller_data['characters']}}, upsert=True)

        # Mentions
        try: seller_mention = (await bot.get_users(seller_id)).mention
        except: seller_mention = "Seller"
        try: buyer_mention = (await bot.get_users(buyer_id)).mention
        except: buyer_mention = "Buyer"

        # Update sold-out caption
        sold_caption = (
            f"{seller_mention} is selling a character!\n\n"
            f"🎀 **Name**: {character['name']}\n"
            f"⚜️ **Anime**: {character['anime']}\n"
            f"⚕️ **Rarity**: {character['rarity']}\n"
            f"💵 **Status**: Sold Out\n"
            f"🔖 **Bought by**: {buyer_mention}"
        )
        try:
            await query.message.edit_caption(sold_caption)
        except Exception as e:
            logging.warning(f"Cannot update caption: {e}")

        # Notify buyer and seller
        await query.answer("🎉 Purchase successful!", show_alert=True)
        await bot.send_message(seller_id, f"🎉 Your character **{character['name']}** has been bought by {buyer_mention}! 💰 +{price_in_balance} balance.")
        await bot.send_message(buyer_id, f"🎉 You bought **{character['name']}** from {seller_mention} for {price_in_balance} balance. Enjoy!")

    except Exception as e:
        logging.error(f"Error in handle_buy: {e}")
        await query.answer("⚠️ An error occurred. Try again later.", show_alert=True)
