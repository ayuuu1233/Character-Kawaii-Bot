import asyncio
import aiohttp
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from shivu import shivuu as app, LEAVELOGS, JOINLOGS


WELCOME_TEMPLATE = """
❀ **Welcome to {chat_title}** ❀

✦ Name ➛ {user_mention}
✦ ID ➛ `{user_id}`
✦ Username ➛ @{user_username}

✨ Enjoy your stay Senpai!
"""

JOIN_TEXT_TEMPLATE = """
⬤ **Bot Added In New Group**

● Group ➠ {chat_title}
● ID ➠ `{chat_id}`
● Username ➠ @{chat_username}
● Members ➠ {total_members}

⬤ Added By ➠ {added_by_mention}
"""


# ---------------- IMAGE DOWNLOAD ----------------
async def download_image(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return BytesIO(await resp.read())
    return None


# ---------------- GENERATE WELCOME IMAGE ----------------
async def generate_welcome_image(photo_bytes, user_name):

    base = Image.open(photo_bytes).convert("RGBA")

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = int(base.size[0] * 0.08)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    text = f"Welcome {user_name}"

    bbox = draw.textbbox((0, 0), text, font=font)

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    pos = ((base.size[0] - text_width) // 2, base.size[1] - text_height - 20)

    draw.text(pos, text, font=font, fill="white", stroke_width=2, stroke_fill="black")

    combined = Image.alpha_composite(base, overlay)

    output = BytesIO()
    combined.save(output, "PNG")
    output.seek(0)

    return output


# ---------------- SEND GROUP PROFILE ----------------
async def send_group_profile_image(client, chat, join_text):

    group = await client.get_chat(chat.id)

    if group.photo:
        file = await client.download_media(group.photo.big_file_id)

        await client.send_photo(
            chat_id=JOINLOGS,
            photo=file,
            caption=join_text
        )

        os.remove(file)

    else:
        await client.send_message(JOINLOGS, join_text)


# ---------------- WELCOME HANDLER ----------------
@app.on_message(filters.new_chat_members)
async def welcome(client: Client, message: Message):

    total_members = await client.get_chat_members_count(message.chat.id)

    # leave small groups
    if total_members < 15:

        await message.reply_text(
            "🌿 Leaving because group has less than **15 members**"
        )

        await client.leave_chat(message.chat.id)
        return

    for user in message.new_chat_members:

        name = user.first_name
        user_id = user.id
        username = user.username or "None"

        photo_file = None

        # get first profile photo
        async for photo in client.get_chat_photos(user_id, limit=1):
            photo_file = photo.file_id
            break

        if photo_file:

            file = await client.download_media(photo_file)

            with open(file, "rb") as f:
                photo_bytes = BytesIO(f.read())

            os.remove(file)

            welcome_img = await generate_welcome_image(photo_bytes, name)

            await message.reply_photo(
                welcome_img,
                caption=WELCOME_TEMPLATE.format(
                    chat_title=message.chat.title,
                    user_mention=user.mention,
                    user_id=user_id,
                    user_username=username
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "➕ Add Me",
                                url="https://t.me/kawaii_character_Bot?startgroup=true"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "Support",
                                url="https://t.me/upper_moon_chat"
                            )
                        ]
                    ]
                )
            )

        else:

            await message.reply_text(
                WELCOME_TEMPLATE.format(
                    chat_title=message.chat.title,
                    user_mention=user.mention,
                    user_id=user_id,
                    user_username=username
                )
            )

    # ---------------- BOT ADDED LOG ----------------
    me = await client.get_me()

    if me.id in [u.id for u in message.new_chat_members]:

        added_by = message.from_user

        join_text = JOIN_TEXT_TEMPLATE.format(
            chat_title=message.chat.title,
            chat_id=message.chat.id,
            chat_username=message.chat.username or "None",
            total_members=total_members,
            added_by_mention=added_by.mention
        )

        await send_group_profile_image(client, message.chat, join_text)
