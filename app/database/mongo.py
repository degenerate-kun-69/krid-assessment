"""
app/database/mongo.py — Motor (async) MongoDB client.

Usage in other modules:
    from app.database.mongo import db
    doc = await db.tenants.find_one({"tenant_id": "tenant_a"})
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings



_client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None  


def connect_db() -> None:
    """
    Create the Motor client and bind the database reference.
    Call this once at FastAPI startup (see app/main.py lifespan).
    """
    global _client, db
    _client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = _client[settings.DB_NAME]
    print(f"[DB] Connected to MongoDB — database: '{settings.DB_NAME}'")


def close_db() -> None:
    """Close the Motor client. Call at FastAPI shutdown."""
    global _client
    if _client is not None:
        _client.close()
        print("[DB] MongoDB connection closed.")







def get_tenants_col():
    return db["tenants"]

def get_sessions_col():
    return db["sessions"]

def get_messages_col():
    return db["messages"]
