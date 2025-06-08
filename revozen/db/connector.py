from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

try:
    client = MongoClient(os.getenv("MONGO_URI"))
    client.admin.command("ping")
    print("✅ MongoDB connection successful!")
    print("✅ Available Collections:", client["tyres"].list_collection_names())
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")

db = client["tyres"]

def get_db():
    return db
