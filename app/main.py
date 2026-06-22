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



@asynccontextmanager
async def lifespan(app: FastAPI):
    
    connect_db()
    await seed_tenants()     
    print("[App] Startup complete. Listening for requests.")
    yield
    
    await close_client()     
    close_db()               
    print("[App] Shutdown complete.")



app = FastAPI(
    title="Krid AI — Multi-Tenant WhatsApp Orchestrator",
    description="LangGraph-powered WhatsApp AI agent SaaS with multi-tenant support.",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(webhook.router)
app.include_router(dashboard.router)




app.mount("/media", StaticFiles(directory="media"), name="media")




app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
