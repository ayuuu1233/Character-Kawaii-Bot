import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import ASCENDING

from telegram import Update, InlineQueryResultPhoto, InlineQueryResultVideo
from telegram.ext import InlineQueryHandler, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from shivu import user_collection, collection, application, db

# --- DATABASE INDEXING (Speed optimized) ---
# Yeh lines startup par indexing check karengi
db.characters.create_index([('id', ASCENDING)], unique=True)
db.characters.create_index([('anime', ASCENDING)])
db.characters.create_index([('img_url', ASCENDING)])

db.user_collection.create_index([('id', ASCENDING)])
db.user_collection.create_index([('characters.id', ASCENDING)])
db.user_collection.create_index([('characters.name', ASCENDING)])
db.user_collection.create_index([('characters.img_url', ASCENDING)])

# Caches for better performance
all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

async def inlinequery(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

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
                # Remove duplicates from user collection for display
                all_characters = list({v['id']:v for v in user['characters']}.values())
                if search_terms:
                    regex = re.compile(search_terms, re.IGNORECASE)
                    all_characters = [character for character in all_characters if regex.search(character['name']) or regex.search(character['anime'])]
            else:
                all_characters = []
        else:
            all_characters = []
    else:
        if query:
            regex = re.compile(query, re.IGNORECASE)
            all_characters = await collection.find({"$or": [{"name": regex}, {"anime": regex}]}).to_list(length=None)
        else:
            if 'all_characters' in all_characters_cache:
                all_characters = all_characters_cache['all_characters']
            else:
                all_characters = await collection.find({}).to_list(length=None)
                all_characters_cache['all_characters'] = all_characters

    # Pagination logic (50 results per page)
    characters = all_characters[offset:offset+50]
    if len(all_characters) > offset + 50:
        next_offset = str(offset + 50)
    else:
        next_offset = ""

    results = []
    for character in characters:
        # Global count calculate karna
        global_count = await user_collection.count_documents({'characters.id': character['id']})
        # Anime ke total characters count karna
        anime_characters = await collection.count_documents({'anime': character['anime']})

        # Caption Logic
        if query.startswith('collection.'):
            user_character_count = sum(c['id'] == character['id'] for c in user['characters'])
            user_anime_characters = sum(c['anime'] == character['anime'] for c in user['characters'])
            caption = (
                f"<b>Look At <a href='tg://user?id={user['id']}'>{escape(user.get('first_name', str(user['id'])))}</a>'s Character</b>\n\n"
                f"🌸: <b>{character['name']} (x{user_character_count})</b>\n"
                f"🏖️: <b>{character['anime']} ({user_anime_characters}/{anime_characters})</b>\n"
                f"<b>{character['rarity']}</b>\n\n"
                f"<b>🆔️:</b> {character['id']}"
            )
        else:
            caption = (
                f"<b>Look At This Character !!</b>\n\n"
                f"🌸:<b> {character['name']}</b>\n"
                f"🏖️: <b>{character['anime']}</b>\n"
                f"<b>{character['rarity']}</b>\n"
                f"🆔️: <b>{character['id']}</b>\n\n"
                f"<b>Globally Guessed {global_count} Times...</b>"
            )

        url = character.get('img_url') or character.get('video_url')
        if not url:
            continue

        # --- PHOTO AUR VIDEO HANDLING ---
        if url.lower().endswith(('.mp4', '.mov', '.mkv', '.webm')):
            results.append(
                InlineQueryResultVideo(
                    id=f"{character['id']}_{time.time()}_{characters.index(character)}",
                    video_url=url,
                    mime_type="video/mp4",
                    thumbnail_url="https://telegra.ph/file/default-thumbnail.jpg", # Placeholder thumbnail
                    title=f"🎥 {character['name']}",
                    caption=caption,
                    parse_mode='HTML'
                )
            )
        else:
            results.append(
                InlineQueryResultPhoto(
                    id=f"{character['id']}_{time.time()}_{characters.index(character)}",
                    photo_url=url,
                    thumbnail_url=url,
                    caption=caption,
                    parse_mode='HTML'
                )
            )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)

# Register the handler
application.add_handler(InlineQueryHandler(inlinequery, block=False))
