import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import ASCENDING

from telegram import Update, InlineQueryResultPhoto, InlineQueryResultVideo
from telegram.ext import InlineQueryHandler, CallbackContext

from shivu import user_collection, collection, application, db

# -------------------- SAFE INDEXING --------------------
async def ensure_indexes():
    char_indexes = await db.characters.index_information()

    if "id_1" in char_indexes:
        # Agar pehle se non-unique hai toh drop karo
        await db.characters.drop_index("id_1")

    await db.characters.create_index([('id', ASCENDING)], unique=True)
    await db.characters.create_index([('anime', ASCENDING)])
    await db.characters.create_index([('img_url', ASCENDING)])

    user_indexes = await db.user_collection.index_information()

    if "id_1" not in user_indexes:
        await db.user_collection.create_index([('id', ASCENDING)])

    await db.user_collection.create_index([('characters.id', ASCENDING)])
    await db.user_collection.create_index([('characters.name', ASCENDING)])
    await db.user_collection.create_index([('characters.img_url', ASCENDING)])


# -------------------- CACHE --------------------
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)


# -------------------- INLINE QUERY --------------------
async def inlinequery(update: Update, context: CallbackContext):
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    all_characters = []

    # ---------------- USER COLLECTION ----------------
    if query.startswith('collection.'):
        user_id_str = query.split(' ')[0].split('.')[1]
        search_terms = ' '.join(query.split(' ')[1:])

        if user_id_str.isdigit():
            user_id = int(user_id_str)

            if user_id_str in user_collection_cache:
                user = user_collection_cache[user_id_str]
            else:
                user = await user_collection.find_one({'id': user_id})
                user_collection_cache[user_id_str] = user

            if user:
                # Remove duplicates
                all_characters = list({v['id']: v for v in user['characters']}.values())

                if search_terms:
                    regex = re.compile(search_terms, re.IGNORECASE)
                    all_characters = [
                        c for c in all_characters
                        if regex.search(c['name']) or regex.search(c['anime'])
                    ]

    # ---------------- GLOBAL SEARCH ----------------
    else:
        if query:
            regex = re.compile(query, re.IGNORECASE)
            all_characters = await collection.find({
                "$or": [{"name": regex}, {"anime": regex}]
            }).to_list(length=200)   # ⚡ limit lagaya for speed
        else:
            if 'all_characters' in all_characters_cache:
                all_characters = all_characters_cache['all_characters']
            else:
                all_characters = await collection.find({}).to_list(length=500)
                all_characters_cache['all_characters'] = all_characters

    # ---------------- PAGINATION ----------------
    characters = all_characters[offset:offset + 50]
    next_offset = str(offset + 50) if len(all_characters) > offset + 50 else ""

    results = []

    for i, character in enumerate(characters):
        global_count = await user_collection.count_documents({'characters.id': character['id']})
        anime_characters = await collection.count_documents({'anime': character['anime']})

        # ---------------- CAPTION ----------------
        if query.startswith('collection.') and 'user' in locals() and user:
            user_character_count = sum(c['id'] == character['id'] for c in user['characters'])
            user_anime_characters = sum(c['anime'] == character['anime'] for c in user['characters'])

            caption = (
                f"<b>{escape(user.get('first_name', str(user['id'])))}'s Character</b>\n\n"
                f"🌸 <b>{character['name']} (x{user_character_count})</b>\n"
                f"🏖️ <b>{character['anime']} ({user_anime_characters}/{anime_characters})</b>\n"
                f"{character['rarity']}\n\n"
                f"🆔 {character['id']}"
            )
        else:
            caption = (
                f"<b>{character['name']}</b>\n"
                f"🏖️ {character['anime']}\n"
                f"{character['rarity']}\n"
                f"🆔 {character['id']}\n\n"
                f"🌍 Guessed: {global_count} times"
            )

        url = character.get('img_url') or character.get('video_url')
        if not url:
            continue

        unique_id = f"{character['id']}_{time.time()}_{i}"

        # ---------------- VIDEO ----------------
        if url.lower().endswith(('.mp4', '.mov', '.mkv', '.webm')):
            results.append(
                InlineQueryResultVideo(
                    id=unique_id,
                    video_url=url,
                    mime_type="video/mp4",
                    thumbnail_url="https://telegra.ph/file/7c1f1b0f5c5e6c7f1c.jpg",
                    title=f"🎥 {character['name']}",
                    caption=caption,
                    parse_mode='HTML'
                )
            )

        # ---------------- IMAGE ----------------
        else:
            results.append(
                InlineQueryResultPhoto(
                    id=unique_id,
                    photo_url=url,
                    thumbnail_url=url,
                    caption=caption,
                    parse_mode='HTML'
                )
            )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)


# -------------------- HANDLER --------------------
application.add_handler(InlineQueryHandler(inlinequery, block=False))
