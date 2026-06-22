"""
app/routers/webhook.py — Twilio WhatsApp Webhook Handler

Two endpoints:
  GET  /api/webhooks/whatsapp  — Health check / verification
  POST /api/webhooks/whatsapp  — Inbound message handler (Twilio format)

CRITICAL: The POST endpoint MUST return 200 OK quickly.
  If it takes too long, Twilio re-delivers the message, causing duplicates.
  Solution: FastAPI BackgroundTasks kicks off the LangGraph agent after
  the response is already sent.

Twilio sends inbound WhatsApp messages as application/x-www-form-urlencoded
with fields: MessageSid, From (whatsapp:+...), To, Body, NumMedia, MediaUrl0, etc.
"""

from fastapi import APIRouter, BackgroundTasks, Request
from app.services.langgraph_agent import get_agent

router = APIRouter(prefix="/api/webhooks", tags=["webhook"])



@router.get("/whatsapp")
async def verify_webhook():
    """
    Simple health check endpoint. Twilio doesn't use Meta-style challenge
    verification, but this endpoint is useful for monitoring and can serve
    as a connectivity check.
    """
    return {"status": "ok", "provider": "twilio"}



async def _run_agent(initial_state: dict) -> None:
    """
    Called as a background task — runs AFTER 200 OK is returned to Twilio.
    Any exception here is logged but does NOT affect the HTTP response.
    """
    try:
        agent = get_agent()
        await agent.ainvoke(initial_state)
    except Exception as exc:
        import traceback
        print(f"[Webhook] Agent error: {exc}")
        traceback.print_exc()



@router.post("/whatsapp", status_code=200)
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """
    Twilio POSTs every inbound WhatsApp message to this endpoint as
    application/x-www-form-urlencoded.

    Key fields from Twilio:
      MessageSid   — Unique message ID
      From         — e.g. "whatsapp:+919876543210"
      To           — e.g. "whatsapp:+14155238886"
      Body         — The text content of the message
      NumMedia     — Number of media attachments
      MediaUrl0    — URL of the first media attachment (if any)
      MediaContentType0 — MIME type of the first media attachment
    """
    form = await request.form()

    try:
        
        message_sid: str = form.get("MessageSid", "")
        from_number: str = form.get("From", "")        
        to_number: str = form.get("To", "")            
        body: str = form.get("Body", "")
        num_media: int = int(form.get("NumMedia", "0"))

        if not from_number or not message_sid:
            
            return {"status": "ok"}

        
        customer_phone = from_number.replace("whatsapp:", "")

        
        inbound_media_url = None
        if num_media > 0:
            inbound_media_url = form.get("MediaUrl0", None)

        
        tenant_id = _resolve_tenant(to_number)

        
        initial_state = {
            "tenant_id": tenant_id,
            "customer_phone": customer_phone,
            "wa_message_id": message_sid,
            "inbound_text": body,
            "inbound_media_url": inbound_media_url,
            "tenant_doc": None,
            "chat_history": [],
            "llm_reply": None,
            "media_attachment": None,
            "session_id": None,
        }

        print(f"[Webhook] Inbound from {customer_phone}: '{body[:80]}' | SID={message_sid}")

        
        background_tasks.add_task(_run_agent, initial_state)
        return {"status": "ok"}

    except Exception as exc:
        
        print(f"[Webhook] Parse error (returning 200): {exc}")
        return {"status": "ok"}


def _resolve_tenant(to_number: str) -> str:
    """
    Map the receiving WhatsApp number to a tenant_id.

    In a production multi-tenant setup, each tenant would have its own
    WhatsApp number. For the Twilio Sandbox demo, all messages arrive
    at the same sandbox number, so we default to tenant_a.

    TODO: For production, store tenant-phone mappings in the DB and
    look them up here.
    """
    
    phone = to_number.replace("whatsapp:", "")

    
    tenant_map = {
        
        
    }
    return tenant_map.get(phone, "tenant_a")
