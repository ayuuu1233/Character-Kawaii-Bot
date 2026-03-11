from pymongo import MongoClient
import os

# MongoDB URI (Yahan apne credentials sahi rakhein)
MONGO_URI = os.getenv("MONGO_URL", "mongodb+srv://Ayuu123_db_user:kawaiiibot124@cluster0.jqv8tga.mongodb.net/kawaii_bot?retryWrites=true&w=majority")
DB_NAME = os.getenv("DB_NAME", "kawaiiiwaifubot")
COLLECTION_NAME = "users"

# Client initialization
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def get_user_data(user_id):
    """Specific user ka data fetch karne ke liye"""
    return collection.find_one({"user_id": user_id})

def save_user_data(user_id, user_data):
    """User data update ya insert karne ke liye"""
    collection.update_one(
        {"user_id": user_id}, 
        {"$set": user_data}, 
        upsert=True
    )
    print(f"User {user_id} data saved successfully.")
