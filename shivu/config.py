from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import os
from dotenv import load_dotenv

load_dotenv()


class Development:
    # Get this value from my.telegram.org/apps
    OWNER_ID = "5158013355"
    sudo_users = "5158013355"
    GROUP_ID = -1001945969614
    TOKEN = "8748211605:AAGe3Q0rahlCcF4v0QP6saFXR2VeiuUycIY"
    mongo_url = "mongodb+srv://Ayuu123_db_user:kawaiiibot124@cluster0.jqv8tga.mongodb.net/?appName=Cluster0"
    PHOTO_URL = ["https://telegra.ph/file/c74151f4c2b56a107a24b.jpg", "https://telegra.ph/file/6a81a91aa4a660a73194b.jpg"]
    SUPPORT_CHAT = "upper_moon_chat"
    UPDATE_CHAT = "upper_moon_chat"
    BOT_USERNAME = "@kawaii_character_Bot"
    CHARA_CHANNEL_ID = "-1002596866659"
    api_id = 21621475
    api_hash = "50c4947b6fe96901599c8b18b09f3e13"

    

# User Roles
    GRADE4 = []
    GRADE3 = ["7334126640"]
    GRADE2 = ["6305653111", "5421067814"]
    GRADE1 = ["7004889403", "1374057577", "5158013355", "5630057244", "7334126640", "5421067814"]
    SPECIALGRADE = ["6402009857", "1993290981", "6835013483", "5158013355"]
    # Additional user roles
    Genin = []
    Chunin = []
    Jonin = ["7334126640"]
    Hokage = ["5421067814"]
    Akatsuki = ["6402009857", "5158013355", "5630057244"]
    Princess = ["1993290981"]
    
    
