import logging
import os
import pytz  
from pyrogram import Client
from telegram.ext import ApplicationBuilder
from motor.motor_asyncio import AsyncIOMotorClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.FileHandler("log.txt"), logging.StreamHandler()],
    level=logging.INFO,
)

logging.getLogger("apscheduler").setLevel(logging.ERROR)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger("pyrate_limiter").setLevel(logging.ERROR)
LOGGER = logging.getLogger(__name__)

from shivu.config import Development as Config

# --- AAPKI PURANI VARIABLES (SAME TO SAME) ---
api_id = Config.api_id
api_hash = Config.api_hash
TOKEN = Config.TOKEN
GROUP_ID = Config.GROUP_ID
CHARA_CHANNEL_ID = Config.CHARA_CHANNEL_ID
mongo_url = Config.mongo_url
PHOTO_URL = Config.PHOTO_URL
SUPPORT_CHAT = Config.SUPPORT_CHAT
UPDATE_CHAT = Config.UPDATE_CHAT
BOT_USERNAME = Config.BOT_USERNAME
sudo_users = Config.sudo_users
OWNER_ID = Config.OWNER_ID
JOINLOGS = Config.JOINLOGS
LEAVELOGS = Config.LEAVELOGS
owner = Config.OWNER_ID
GRADE4 = Config.GRADE4
GRADE3 = Config.GRADE3
GRADE2 = Config.GRADE2
GRADE1 = Config.GRADE1
SPECIALGRADE = Config.SPECIALGRADE
Genin= Config.Genin
Chunin= Config.Chunin
Jonin= Config.Jonin
Hokage= Config.Hokage
Akatsuki = Config.Akatsuki
Princess = Config.Princess

# --- NEW FIX CODE (TIMEZONE ERROR KILLER) ---
# Forced UTC timezone taaki Hugging Face crash na ho
scheduler = AsyncIOScheduler(timezone=pytz.utc)
application = ApplicationBuilder().token(TOKEN).build()

# --- AAPKI PURANI COLLECTIONS (SAME TO SAME) ---
shivuu = Client("Shivu", api_id, api_hash, bot_token=TOKEN)
lol = AsyncIOMotorClient(mongo_url)
db = lol['Character_catcher']
set_on_data = db['set_on_data']
refeer_collection = db['refeer_collection']
set_off_data = db['set_off_data']
collection = db['anime_characters_lol']
safari_cooldown_collection = db["safari_cooldown"]
safari_users_collection = db["safari_users_collection"]
sudo_users_collection= db["sudo_users_collection"]
user_totals_collection = db['user_totals_lmaoooo']
user_collection = db["user_collection_lmaoooo"]
group_user_totals_collection = db['group_user_totalsssssss']
top_global_groups_collection = db['top_global_groups']
pm_users = db['total_pm_users']
registered_users = db['registered_users']
backup_collection = db['backup_collection']
settings_collection = db["settings"]
event_collection = db['event_collection']

async def get_served_chat():
    served_chats = []
    async for chat in top_global_groups_collection.find():
        served_chats.append(chat['id'])
    return served_chats

async def get_pm_users():
    pm_users_list = []
    async for user in pm_users.find():
        pm_users_list.append(user['id'])
    return pm_users_list
