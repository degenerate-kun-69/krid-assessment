"""
app/database/seed.py — Seeds the database with two demo tenants on startup.

Run standalone:  python -m app.database.seed
Or called from:  app/main.py lifespan (after connect_db())

Tenants are only inserted if they don't already exist (idempotent).
"""

import asyncio
from app.database.mongo import connect_db, get_tenants_col

# ── Tenant seed data ───────────────────────────────────────────────────────────

TENANTS = [
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
            # keyword (lowercase) → public URL
            "catalog": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/pdf-sample.pdf",
            "sofa": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800",
            "table": "https://images.unsplash.com/photo-1533090481720-856c6e3c1fdc?w=800",
            "showroom": "https://images.unsplash.com/photo-1567016432779-094069958ea5?w=800",
        },
    },
    {
        "tenant_id": "tenant_b",
        "name": "Automotive Care Center",
        "system_prompt": (
            "You are a helpful service advisor for an automotive care center. "
            "Be clear, technical when needed, and reassuring. Help customers schedule "
            "appointments, understand repair costs, and access service documents. "
            "If a customer requests an invoice, repair diagram, or service manual, "
            "attach the relevant document from our library."
        ),
        "media_library": {
            "invoice": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/pdf-sample.pdf",
            "repair": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=800",
            "manual": "https://www.w3.org/WAI/WCAG21/Techniques/pdf/pdf-sample.pdf",
            "diagram": "https://images.unsplash.com/photo-1518005020951-eccb494ad742?w=800",
        },
    },
]


async def seed_tenants() -> None:
    """Insert tenants that don't already exist in the DB."""
    col = get_tenants_col()
    for tenant in TENANTS:
        existing = await col.find_one({"tenant_id": tenant["tenant_id"]})
        if existing is None:
            await col.insert_one(tenant)
            print(f"[Seed] Inserted tenant: {tenant['name']}")
        else:
            print(f"[Seed] Tenant already exists, skipping: {tenant['name']}")


# ── Standalone entry point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    connect_db()
    asyncio.run(seed_tenants())
    print("[Seed] Done.")
