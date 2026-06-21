"""
app/models/message.py — Message audit log model.
Every inbound and outbound WhatsApp message is stored here for the dashboard.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime, timezone


class MessageDirection(str, Enum):
    INBOUND = "inbound"    # Customer → Bot
    OUTBOUND = "outbound"  # Bot → Customer


class MessageLog(BaseModel):
    message_id: str = Field(..., description="Meta WA message ID or generated UUID for outbound")
    session_id: str = Field(..., description="References ChatSession.session_id")
    tenant_id: str
    direction: MessageDirection
    sender: str = Field(..., description="Phone number or 'bot'")
    text: Optional[str] = None
    media_url: Optional[str] = None
    mime_type: Optional[str] = None          # e.g. 'application/pdf', 'image/jpeg'
    bot_was_typing: bool = False             # True if typing indicator was active before this msg
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
