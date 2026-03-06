class Config(object):
    LOGGER = True

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

    
class Production(Config):
    LOGGER = True


class Development(Config):
    LOGGER = True
