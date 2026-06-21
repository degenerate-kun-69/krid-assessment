"""
app/routers/dashboard.py — REST API endpoints for the frontend dashboard.

Endpoints:
  GET  /api/tenants                           — List all tenants
  GET  /api/tenants/{tenant_id}/sessions      — Active sessions for a tenant
  GET  /api/sessions/{session_id}/messages    — Message thread for a session
  POST /api/broadcast                         — Send a template message to a list of phones
  POST /api/simulate                          — Simulate an inbound message (testing w/o WhatsApp)
"""

import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
from app.database.mongo import get_tenants_col, get_sessions_col, get_messages_col
from app.services.whatsapp import send_text
from app.services.langgraph_agent import get_agent

router = APIRouter(prefix="/api", tags=["dashboard"])


# ── GET /api/tenants ───────────────────────────────────────────────────────────
@router.get("/tenants")
async def list_tenants():
    """Return all registered tenants (without internal MongoDB _id)."""
    col = get_tenants_col()
    tenants = await col.find({}, {"_id": 0}).to_list(length=100)
    return {"tenants": tenants}


# ── GET /api/tenants/{tenant_id}/sessions ─────────────────────────────────────
@router.get("/tenants/{tenant_id}/sessions")
async def list_sessions(tenant_id: str):
    """
    Return all chat sessions for a given tenant, sorted newest first.
    Used by the frontend's session list panel.
    """
    col = get_sessions_col()
    sessions = (
        await col
        .find({"tenant_id": tenant_id}, {"_id": 0})
        .sort("updated_at", -1)
        .to_list(length=500)
    )
    # Serialize datetime fields for JSON response
    for s in sessions:
        for field in ("created_at", "updated_at"):
            if field in s and hasattr(s[field], "isoformat"):
                s[field] = s[field].isoformat()
    return {"sessions": sessions}


# ── GET /api/sessions/{session_id}/messages ───────────────────────────────────
@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    """
    Return the full message thread for a session, sorted oldest first.
    Used by the frontend's chat thread panel.
    """
    col = get_messages_col()
    messages = (
        await col
        .find({"session_id": session_id}, {"_id": 0})
        .sort("timestamp", 1)
        .to_list(length=1000)
    )
    for m in messages:
        if "timestamp" in m and hasattr(m["timestamp"], "isoformat"):
            m["timestamp"] = m["timestamp"].isoformat()
    return {"messages": messages}


# ── POST /api/broadcast ───────────────────────────────────────────────────────
class BroadcastRequest(BaseModel):
    tenant_id: str
    phone_numbers: List[str]
    message: str


@router.post("/broadcast")
async def broadcast_message(body: BroadcastRequest):
    """
    Send a text message to a list of phone numbers on behalf of a tenant.
    This is the 'Broadcast Campaign' feature in the dashboard drawer.

    NOTE: In production you should use WhatsApp Template Messages for broadcasts.
    For this demo, we send a plain text message.
    """
    if not body.phone_numbers:
        raise HTTPException(status_code=400, detail="No phone numbers provided.")

    results = []
    for phone in body.phone_numbers:
        try:
            await send_text(to=phone, body=body.message)
            results.append({"phone": phone, "status": "sent"})
        except Exception as exc:
            results.append({"phone": phone, "status": "failed", "error": str(exc)})

    return {"broadcast_results": results}


# ── POST /api/simulate ────────────────────────────────────────────────────────
# This endpoint lets you test the full LangGraph pipeline from the dashboard
# without needing a real WhatsApp account. It mimics what the webhook POST does.

class SimulateRequest(BaseModel):
    tenant_id: str
    customer_phone: str
    message: str


async def _run_simulated_agent(initial_state: dict) -> None:
    """Background task: run the LangGraph agent for a simulated message."""
    try:
        agent = get_agent()
        await agent.ainvoke(initial_state)
    except Exception as exc:
        import traceback
        print(f"[Simulate] Agent error: {exc}")
        traceback.print_exc()


@router.post("/simulate")
async def simulate_message(body: SimulateRequest, background_tasks: BackgroundTasks):
    """
    Simulate an inbound WhatsApp message. Triggers the full LangGraph pipeline
    (acknowledge → context → LLM → dispatcher) without needing Meta credentials.

    Use this from the dashboard's chat simulator to test the bot's behavior.
    """
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Generate a fake WhatsApp message ID
    fake_wa_id = f"sim_{uuid.uuid4().hex[:12]}"

    initial_state = {
        "tenant_id": body.tenant_id,
        "customer_phone": body.customer_phone,
        "wa_message_id": fake_wa_id,
        "inbound_text": body.message,
        "inbound_media_url": None,
        "tenant_doc": None,
        "chat_history": [],
        "llm_reply": None,
        "media_attachment": None,
        "session_id": None,
    }

    # Run agent in background — returns 200 immediately (same pattern as real webhook)
    background_tasks.add_task(_run_simulated_agent, initial_state)

    return {
        "status": "ok",
        "message_id": fake_wa_id,
        "note": "Agent running in background. Poll /api/sessions to see the reply.",
    }
