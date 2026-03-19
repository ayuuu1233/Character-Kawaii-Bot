import re
import time
from html import escape
from cachetools import TTLCache
from pymongo import MongoClient, ASCENDING

from telegram import Update, InlineQueryResultPhoto, InlineQueryResultVideo
from telegram.ext import InlineQueryHandler, CallbackContext

from shivu import user_collection, collection, application, db

CATEGORY_MAP = {
    '🏖': '🏖𝒔𝒖𝒎𝒎𝒆𝒓 🏖',
    '👘': '👘𝑲𝒊𝒎𝒐𝒏𝒐👘',
    '🧹': '🧹𝑴𝒂𝒊𝒅🧹',
    '🐰': '🐰𝑩𝒖𝒏𝒏𝒚🐰',
    '🏜️': '🏜️𝑬𝒈𝒚𝒑𝒕🏜️',
    '🎒': '🎒𝑺𝒄𝒉𝒐𝒐𝒍🎒',
    '💞': '💞𝑽𝒂𝒍𝒆𝒏𝒕𝒊𝒏𝒆💞',
    '🎃': '🎃𝑯𝒂𝒍𝒍𝒐𝒘𝒆𝒆𝒏🎃',
    '🥻': '🥻𝑺𝒂𝒓𝒆𝒆🥻',
    '💉': '💉𝑵𝒖𝒓𝒔𝒆💉',
    '☃️': '☃️𝑾𝒊𝒏𝒕𝒆𝒓☃️',
    '🎄': '🎄𝑪𝒉𝒓𝒊𝒔𝒕𝒎𝒂𝒔🎄',
    '👥': '👥𝐃𝐮𝐨👥',
    '🤝': '🤝𝐆𝐫𝐨𝐮𝐩🤝',
    '⚽': '⚽𝑭𝒐𝒐𝒕𝒃𝒂𝒍𝒍⚽',
    '🏀': '🏀𝑩𝒂𝒔𝒌𝒆𝒕𝒃𝒂𝒍𝒍🏀',
    '🎩': '🎩𝑻𝒖𝒙𝒆𝒅𝒐🎩',
    '🏮': '🏮𝑪𝒉𝒊𝒏𝒆𝒔𝒆🏮',
    '📙': '📙𝑴𝒂𝒏𝒉𝒘𝒂📙',
    '👙': '👙𝑩𝒊𝒌𝒊𝒏𝒊👙',
    '🎊': '🎊𝑪𝒉𝒆𝒆𝒓𝒍𝒆𝒂𝒅𝒆𝒓𝒔🎊',
    '🎮': '🎮𝑮𝒂𝒎𝒆🎮',
    '💍': '💍𝑴𝒂𝒓𝒓𝒊𝒆𝒅💍',
    '👶': '👶𝑪𝒉𝒊𝒃𝒊👶',
    '🕷️': '🕷️𝑺𝒑𝒊𝒅𝒆𝒓🕷️',
    '🔞': '🔞𝑵𝒖𝒅𝒆𝒔🔞',
    '🎗️': '🎗️𝑪𝒐𝒍𝒍𝒆𝒄𝒕𝒐𝒓🎗️'
}

# collection
db.characters.create_index([('id', ASCENDING)])
db.characters.create_index([('anime', ASCENDING)])
db.characters.create_index([('img_url', ASCENDING)])
db.characters.create_index([('category', ASCENDING)])

# user_collection
db.user_collection.create_index([('characters.id', ASCENDING)])
db.user_collection.create_index([('characters.name', ASCENDING)])
db.user_collection.create_index([('characters.img_url', ASCENDING)])
db.user_collection.create_index([('characters.category', ASCENDING)])

all_characters_cache = TTLCache(maxsize=10000, ttl=36000)
user_collection_cache = TTLCache(maxsize=10000, ttl=60)

def get_category(name):
    for emoji in CATEGORY_MAP:
        if emoji in name:
            return CATEGORY_MAP[emoji]
    return ""

async def inlinequery(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0

    if query.startswith('collection.'):
        user_id, *search_terms = query.split(' ')[0].split('.')[1], ' '.join(query.split(' ')[1:])
        if user_id.isdigit():
            if user_id in user_collection_cache:
                user = user_collection_cache[user_id]
            else:
                user = await user_collection.find_one({'id': int(user_id)})
                user_collection_cache[user_id] = user

            if user:
                all_characters = list({v['id']: v for v in user['characters']}.values())
                if search_terms:
                    regex = re.compile(' '.join(search_terms), re.IGNORECASE)
                    all_characters = [character for character in all_characters if regex.search(character['name']) or regex.search(character['anime'])]
            else:
                all_characters = []
        else:
            all_characters = []
    else:
        if query:
            regex = re.compile(query, re.IGNORECASE)
            all_characters = list(await collection.find({"$or": [{"name": regex}, {"anime": regex}]}).to_list(length=None))
        else:
            if 'all_characters' in all_characters_cache:
                all_characters = all_characters_cache['all_characters']
            else:
                all_characters = list(await collection.find({}).to_list(length=None))
                all_characters_cache['all_characters'] = all_characters

    characters = all_characters[offset:offset + 50]
    if len(characters) > 50:
        characters = characters[:50]
        next_offset = str(offset + 50)
    else:
        next_offset = str(offset + len(characters))

    results = []
    for character in characters:
        global_count = await user_collection.count_documents({'characters.id': character['id']})
        anime_characters = await collection.count_documents({'anime': character['anime']})

        category = get_category(character['name'])

        if query.startswith('collection.'):
            user_character_count = sum(c['id'] == character['id'] for c in user['characters'])
            user_anime_characters = sum(c['anime'] == character['anime'] for c in user['characters'])
            first_name = str(escape(user.get('first_name', str(user['id']))))
            caption = (
                f"<b> Look At <a href='tg://user?id={user['id']}'>{first_name}</a>'s Character</b>\n\n"
                f"<b>{character['anime']}</b>\n"
                f"<b>{character['id']}</b> {character['name']} x{user_character_count}\n"
                f"﹙{character['rarity'][0]} 𝙍𝘼𝙍𝙄𝙏𝙔: {character['rarity'][2:]}﹚\n\n"
                f"{category}\n"
            )
        else:
            caption = (
                f"<b>OwO! Check out This Anime!</b>\n\n"
                f"<b>{character['anime']}</b>\n"
                f"<b>{character['id']}</b> {character['name']}\n"
                f"﹙{character['rarity'][0]} 𝙍𝘼𝙍𝙄𝙏𝙔: {character['rarity'][2:]}﹚\n\n"
                f"{category}\n"
            )

        # Tentukan apakah karakter adalah video atau gambar
        if character['img_url'].endswith(('.mp4', '.gif')):
            results.append(
                InlineQueryResultVideo(
                    id=f"{character['id']}_{time.time()}",
                    video_url=character['img_url'],
                    mime_type="video/mp4",
                    thumbnail_url=character['img_url'],
                    title=character['name'],  # Judul video, Anda dapat mengubah ini sesuai keinginan
                    caption=caption,
                    parse_mode='HTML',
                    video_width=300,
                    video_height=300
                )
            )
        else:
            results.append(
                InlineQueryResultPhoto(
                    id=f"{character['id']}_{time.time()}",
                    photo_url=character['img_url'],
                    thumbnail_url=character['img_url'],
                    caption=caption,
                    parse_mode='HTML',
                    photo_width=300,
                    photo_height=300
                )
            )

    await update.inline_query.answer(results, next_offset=next_offset, cache_time=5)

# Menambahkan handler untuk inline query
application.add_handler(InlineQueryHandler(inlinequery, block=False))
