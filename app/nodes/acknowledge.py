"""
app/nodes/acknowledge.py — Node 1: Acknowledge

Responsibilities:
1. Fire `mark_as_read` so the customer sees double blue ticks.
2. Fire `send_typing` so the customer sees the typing indicator.
3. Upsert the ChatSession in MongoDB with status AGENT_RESPONDING.
4. Save the inbound message to the messages collection.
5. Set state["session_id"] for downstream nodes.
"""

from datetime import datetime, timezone
from app.services import whatsapp
from app.database.mongo import get_sessions_col, get_messages_col
from app.models.session import SessionStatus


async def acknowledge_node(state: dict) -> dict:
    """
    LangGraph node function.
    Receives the full AgentState, returns a dict of state updates.
    """
    tenant_id = state["tenant_id"]
    customer_phone = state["customer_phone"]
    wa_message_id = state["wa_message_id"]

    # ── Step 1: WhatsApp UX signals ────────────────────────────────
    # These are no-ops when WA credentials aren't configured (mock mode).
    await whatsapp.mark_as_read(wa_message_id)
    await whatsapp.send_typing(customer_phone)

    # ── Step 2: Build session_id ───────────────────────────────────
    # Composite key ensures one session per (tenant, phone) pair.
    session_id = f"{tenant_id}_{customer_phone.replace('+', '')}"

    # ── Step 3: Upsert session in MongoDB ─────────────────────────
    sessions_col = get_sessions_col()
    now = datetime.now(timezone.utc)
    await sessions_col.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "tenant_id": tenant_id,
                "customer_phone": customer_phone,
                "status": SessionStatus.AGENT_RESPONDING.value,
                "updated_at": now,
            },
            "$setOnInsert": {
                "session_id": session_id,
                "context_vars": {},
                "created_at": now,
            },
        },
        upsert=True,
    )

    # ── Step 4: Log inbound message ────────────────────────────────
    messages_col = get_messages_col()
    await messages_col.insert_one(
        {
            "message_id": wa_message_id,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "direction": "inbound",
            "sender": customer_phone,
            "text": state.get("inbound_text"),
            "media_url": state.get("inbound_media_url"),
            "mime_type": None,
            "bot_was_typing": False,
            "timestamp": now,
        }
    )

    print(f"[Acknowledge] session={session_id} | msg_id={wa_message_id}")

    # ── Return state updates ───────────────────────────────────────
    return {"session_id": session_id}
