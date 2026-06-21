"""
app/nodes/dispatcher.py — Node 4: Dispatcher

Responsibilities:
1. Send image or document to customer if media_attachment is set.
2. Send the text reply from the LLM.
3. Log each outbound message to the messages collection.
4. Update session status back to WAITING_FOR_BOT.

Error handling: If the Twilio API call fails (e.g. phone not opted into
sandbox, 400 Bad Request), the message is still logged to MongoDB and
the session status is updated so the dashboard doesn't get stuck on "typing".
"""

import uuid
from datetime import datetime, timezone
from app.services import whatsapp
from app.database.mongo import get_sessions_col, get_messages_col
from app.models.session import SessionStatus


async def _log_outbound(
    session_id: str,
    tenant_id: str,
    text: str | None = None,
    media_url: str | None = None,
    mime_type: str | None = None,
    bot_was_typing: bool = True,
) -> None:
    """Helper: write a single outbound message record to MongoDB."""
    messages_col = get_messages_col()
    await messages_col.insert_one(
        {
            "message_id": str(uuid.uuid4()),   # Generated ID for outbound msgs
            "session_id": session_id,
            "tenant_id": tenant_id,
            "direction": "outbound",
            "sender": "bot",
            "text": text,
            "media_url": media_url,
            "mime_type": mime_type,
            "bot_was_typing": bot_was_typing,
            "timestamp": datetime.now(timezone.utc),
        }
    )


async def dispatcher_node(state: dict) -> dict:
    """
    LangGraph node function.
    Sends the WhatsApp reply and logs everything to MongoDB.
    """
    customer_phone = state["customer_phone"]
    session_id = state["session_id"]
    tenant_id = state["tenant_id"]
    llm_reply = state.get("llm_reply") or "Sorry, something went wrong."
    media_attachment = state.get("media_attachment")

    # ── Step 1: Send media if the LLM requested it ─────────────────
    if media_attachment:
        media_type = media_attachment["type"]
        url = media_attachment["url"]

        if media_type == "image":
            try:
                await whatsapp.send_image(
                    to=customer_phone,
                    url=url,
                    caption=media_attachment.get("caption", ""),
                )
            except Exception as exc:
                print(f"[Dispatcher] WARNING: Failed to send image via Twilio: {exc}")
            # Always log the media, even if sending failed
            await _log_outbound(
                session_id=session_id,
                tenant_id=tenant_id,
                media_url=url,
                mime_type="image/jpeg",
            )

        elif media_type == "document":
            try:
                await whatsapp.send_document(
                    to=customer_phone,
                    url=url,
                    filename=media_attachment.get("filename", "document.pdf"),
                    caption=media_attachment.get("caption", ""),
                )
            except Exception as exc:
                print(f"[Dispatcher] WARNING: Failed to send document via Twilio: {exc}")
            # Always log the media, even if sending failed
            await _log_outbound(
                session_id=session_id,
                tenant_id=tenant_id,
                media_url=url,
                mime_type="application/pdf",
            )

    # ── Step 2: Send the text reply ─────────────────────────────────
    try:
        await whatsapp.send_text(to=customer_phone, body=llm_reply)
    except Exception as exc:
        print(f"[Dispatcher] WARNING: Failed to send text via Twilio: {exc}")

    # Always log the reply, even if sending failed
    await _log_outbound(
        session_id=session_id,
        tenant_id=tenant_id,
        text=llm_reply,
        bot_was_typing=True,  # Typing was active before this message
    )

    # ── Step 3: Update session status ─────────────────────────────
    # This MUST run even if Twilio calls fail, otherwise the dashboard
    # gets stuck showing "typing..." forever.
    sessions_col = get_sessions_col()
    await sessions_col.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "status": SessionStatus.WAITING_FOR_BOT.value,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    print(f"[Dispatcher] Done for session={session_id} | media={media_attachment is not None}")

    # No new state fields needed — dispatcher is the final node.
    return {}
