"""
app/database/seed.py — Seeds the database with two demo tenants on startup.

Run standalone:  python -m app.database.seed
Or called from:  app/main.py lifespan (after connect_db())

Tenants are only inserted if they don't already exist (idempotent).
Media library URLs are built from BASE_URL so they resolve correctly
both locally and on the deployed instance.
"""

import asyncio
from app.config import settings
from app.database.mongo import connect_db, get_tenants_col



def _media_url(path: str) -> str:
    """Build a full public URL for a media asset."""
    base = settings.BASE_URL.rstrip("/")
    return f"{base}/media/{path.lstrip('/')}"




def _build_tenants() -> list[dict]:
    """
    Build tenant seed documents with absolute media URLs.
    Called at import-time or seed-time so BASE_URL is resolved.
    """
    return [
        {
            "tenant_id": "tenant_a",
            "name": "Luxury Furniture Store",
            "system_prompt": (
                "You are a knowledgeable and elegant sales assistant for a luxury furniture brand. "
                "Be warm, professional, and concise. Help customers discover our premium collections. "
                "If a customer asks about product images, catalogs, or specific items like sofas or "
                "tables, retrieve and attach the relevant media from our library. "
                "Always end your replies with an offer to help further."
            ),
            "media_library": {
                
                "sofa": _media_url("sofas/white_sectional.png"),
                "white sofa": _media_url("sofas/white_sectional.png"),
                "green sofa": _media_url("sofas/green_velvet.png"),
                "leather sofa": _media_url("sofas/leather_chesterfield.png"),
                
                "showroom": _media_url("sofas/green_velvet.png"),
                "table": "https://images.unsplash.com/photo-1533090481720-856c6e3c1fdc?w=800",
                
                "catalog": _media_url("restaurant_menu.pdf"),
                "menu": _media_url("restaurant_menu.pdf"),
            },
        },
        {
            "tenant_id": "tenant_b",
            "name": "Minecraft Gaming Store",
            "system_prompt": (
                "You are an enthusiastic and knowledgeable gaming advisor for a Minecraft-themed store. "
                "Help customers find builds, scenes, and inspiration for their Minecraft worlds. "
                "When a customer asks about specific biomes, builds, or scenes, share the relevant "
                "images from our gallery. Be fun, use gaming lingo, and keep it engaging! "
                "Always end your replies with an offer to help further."
            ),
            "media_library": {
                
                "house": _media_url("minecraft/house.png"),
                "cave": _media_url("minecraft/cave.png"),
                "village": _media_url("minecraft/village.png"),
                "nether": _media_url("minecraft/nether.png"),
                "castle": _media_url("minecraft/castle.png"),
                "ocean": _media_url("minecraft/ocean_monument.png"),
                "ocean monument": _media_url("minecraft/ocean_monument.png"),
                "ender dragon": _media_url("minecraft/ender_dragon.png"),
                "dragon": _media_url("minecraft/ender_dragon.png"),
                "farm": _media_url("minecraft/farm.png"),
                "enchanting": _media_url("minecraft/enchanting.png"),
                "snow": _media_url("minecraft/snow_biome.png"),
                
                "catalog": _media_url("restaurant_menu.pdf"),
                "menu": _media_url("restaurant_menu.pdf"),
            },
        },
    ]


async def seed_tenants() -> None:
    """Insert tenants that don't already exist in the DB."""
    col = get_tenants_col()
    tenants = _build_tenants()
    for tenant in tenants:
        existing = await col.find_one({"tenant_id": tenant["tenant_id"]})
        if existing is None:
            await col.insert_one(tenant)
            print(f"[Seed] Inserted tenant: {tenant['name']}")
        else:
            
            await col.update_one(
                {"tenant_id": tenant["tenant_id"]},
                {"$set": {"media_library": tenant["media_library"]}},
            )
            print(f"[Seed] Tenant exists, updated media_library: {tenant['name']}")



if __name__ == "__main__":
    connect_db()
    asyncio.run(seed_tenants())
    print("[Seed] Done.")

