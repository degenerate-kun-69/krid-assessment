"""
app/services/whatsapp.py — Twilio WhatsApp API helper functions.

All functions are async and use a shared httpx.AsyncClient.
Import the helpers and await them from LangGraph nodes.

When TWILIO_ACCOUNT_SID is empty or set to a placeholder, all API calls
are skipped gracefully (mock mode). This lets us develop and test the full
LangGraph pipeline + dashboard without a Twilio account.

Twilio REST API for WhatsApp:
  POST https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json
  Auth: HTTP Basic (ACCOUNT_SID : AUTH_TOKEN)
  Body: application/x-www-form-urlencoded
    From=whatsapp:+14155238886
    To=whatsapp:+919876543210
    Body=Hello!
    MediaUrl=https://example.com/image.jpg  (optional, for images/documents)
"""

import httpx
from app.config import settings




_http_client: httpx.AsyncClient | None = None


def _is_configured() -> bool:
    """
    Returns True only if the Twilio credentials look like real values.
    When they're empty or still placeholders, we run in mock mode
    and skip all Twilio API calls.
    """
    sid = settings.TWILIO_ACCOUNT_SID
    token = settings.TWILIO_AUTH_TOKEN
    number = settings.TWILIO_WHATSAPP_NUMBER
    if not sid or not token or not number:
        return False
    
    if "<" in sid or "<" in token or "<" in number:
        return False
    return True


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=15.0,
        )
    return _http_client


async def close_client() -> None:
    """Call at app shutdown to cleanly close the HTTP connection pool."""
    global _http_client
    if _http_client and not _http_client.is_closed:
        await _http_client.aclose()


def _normalize_phone(phone: str) -> str:
    """
    Ensure the phone number is in Twilio's 'whatsapp:+...' format.
    If it's already prefixed, return as-is. Otherwise, prepend 'whatsapp:'.
    """
    if phone.startswith("whatsapp:"):
        return phone
    
    if not phone.startswith("+"):
        phone = "+" + phone
    return f"whatsapp:{phone}"




async def mark_as_read(wa_message_id: str) -> None:
    """
    Mark an inbound message as read.
    Twilio does not support manual read receipts — this is a no-op.
    """
    print(f"[WA] mark_as_read({wa_message_id}) — no-op (Twilio handles automatically)")


async def send_typing(to: str) -> None:
    """
    Show the WhatsApp native typing indicator to a customer.
    Twilio does not expose a typing indicator API — this is a no-op.
    The session status in MongoDB (AGENT_RESPONDING) still tracks this state
    for the frontend dashboard typing animation.
    """
    print(f"[WA] send_typing({to}) — no-op (not available via Twilio)")


async def send_text(to: str, body: str) -> dict:
    """
    Send a plain text WhatsApp message via Twilio.
    Returns the API response JSON.
    """
    if not _is_configured():
        print(f"[WA Mock] send_text({to}, '{body[:60]}...') — skipped (no credentials)")
        return {"mock": True, "status": "sent"}

    payload = {
        "From": settings.TWILIO_WHATSAPP_NUMBER,
        "To": _normalize_phone(to),
        "Body": body,
    }
    client = _get_client()
    resp = await client.post(settings.twilio_messages_url, data=payload)
    resp.raise_for_status()
    result = resp.json()
    print(f"[WA] Sent text to {to} | SID: {result.get('sid', 'N/A')}")
    return result


async def send_image(to: str, url: str, caption: str = "") -> dict:
    """
    Send an image message using a publicly accessible URL via Twilio.
    Returns the API response JSON.
    """
    if not _is_configured():
        print(f"[WA Mock] send_image({to}, {url[:50]}...) — skipped (no credentials)")
        return {"mock": True, "status": "sent"}

    payload = {
        "From": settings.TWILIO_WHATSAPP_NUMBER,
        "To": _normalize_phone(to),
        "MediaUrl": url,
    }
    
    if caption:
        payload["Body"] = caption
    else:
        payload["Body"] = ""  

    client = _get_client()
    resp = await client.post(settings.twilio_messages_url, data=payload)
    resp.raise_for_status()
    result = resp.json()
    print(f"[WA] Sent image to {to} | SID: {result.get('sid', 'N/A')}")
    return result


async def send_document(to: str, url: str, filename: str, caption: str = "") -> dict:
    """
    Send a document (e.g. PDF) using a publicly accessible URL via Twilio.
    Twilio treats documents the same as media — uses MediaUrl.
    Returns the API response JSON.
    """
    if not _is_configured():
        print(f"[WA Mock] send_document({to}, {filename}) — skipped (no credentials)")
        return {"mock": True, "status": "sent"}

    body_text = caption if caption else f"📄 {filename}"
    payload = {
        "From": settings.TWILIO_WHATSAPP_NUMBER,
        "To": _normalize_phone(to),
        "Body": body_text,
        "MediaUrl": url,
    }
    client = _get_client()
    resp = await client.post(settings.twilio_messages_url, data=payload)
    resp.raise_for_status()
    result = resp.json()
    print(f"[WA] Sent document to {to} | SID: {result.get('sid', 'N/A')}")
    return result
