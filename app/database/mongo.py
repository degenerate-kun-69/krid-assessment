"""
app/database/mongo.py — Motor (async) MongoDB client.

Usage in other modules:
    from app.database.mongo import db
    doc = await db.tenants.find_one({"tenant_id": "tenant_a"})
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

# ── Client singleton ───────────────────────────────────────────────────────────
# Motor is thread-safe and the client should be created once at startup.
_client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None  # type: ignore[assignment]


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


# ── Collection shortcuts ───────────────────────────────────────────────────────
# These are properties so they always reference the current `db` instance.
# Usage: from app.database.mongo import get_tenants_col
#        col = get_tenants_col()

def get_tenants_col():
    return db["tenants"]

def get_sessions_col():
    return db["sessions"]

def get_messages_col():
    return db["messages"]
