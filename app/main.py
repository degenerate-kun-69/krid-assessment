"""
app/main.py — FastAPI application entry point.

Responsibilities:
  - Create the FastAPI app instance
  - Register all API routers
  - Handle startup/shutdown lifecycle (DB connect, seed, HTTP client cleanup)
  - Mount the frontend/ directory as static files at the root path "/"
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.database.mongo import connect_db, close_db
from app.database.seed import seed_tenants
from app.services.whatsapp import close_client
from app.routers import webhook, dashboard


# ── Lifespan: startup / shutdown ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    connect_db()
    await seed_tenants()     # Idempotent — safe to call every time
    print("[App] Startup complete. Listening for requests.")
    yield
    # ── Shutdown ──
    await close_client()     # Close the httpx WhatsApp client
    close_db()               # Close the Motor MongoDB client
    print("[App] Shutdown complete.")


# ── App instance ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Krid AI — Multi-Tenant WhatsApp Orchestrator",
    description="LangGraph-powered WhatsApp AI agent SaaS with multi-tenant support.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (needed for the frontend to call the API from the browser) ────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ────────────────────────────────────────────────────────────────
app.include_router(webhook.router)
app.include_router(dashboard.router)

# ── Static frontend ────────────────────────────────────────────────────────────
# Serves index.html, style.css, app.js from the frontend/ directory.
# IMPORTANT: Mount AFTER the API routers so /api/* routes take priority.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
