from pymongo import MongoClient
from django.conf import settings
import hashlib

client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]

def init_db():
    # Predefined kits
    kits = db['kits']
    if kits.count_documents({}) == 0:
        kits.insert_one({
            "id": "1",
            "name": "media_kit",
            "camera": True,
            "mic": True,
            "tripod": True,
            "current_booking_id": None,
            "ready_after": None
        })

    # Predefined users (roles: ADMIN, USER)
    users = db['users']
    if users.count_documents({}) == 0:
        def hash_pw(pw):
            return hashlib.sha256(pw.encode()).hexdigest()
        
        users.insert_many([
            {"username": "Admin", "password_hash": hash_pw("1234"), "role": "ADMIN"},
            {"username": "User1", "password_hash": hash_pw("1234"), "role": "USER"},
            {"username": "User2", "password_hash": hash_pw("1234"), "role": "USER"},
        ])
        
from pymongo.errors import ConnectionFailure

try:
    init_db()
except ConnectionFailure:
    pass
except Exception:
    pass
