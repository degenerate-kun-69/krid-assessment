"""
app/models/session.py — Chat session model.
One session = one customer phone number talking to one tenant's bot.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime, timezone


class SessionStatus(str, Enum):
    WAITING_FOR_BOT = "WAITING_FOR_BOT"      
    AGENT_RESPONDING = "AGENT_RESPONDING"    
    RESOLVED = "RESOLVED"                    
    NEEDS_HUMAN = "NEEDS_HUMAN"              


class ChatSession(BaseModel):
    session_id: str = Field(..., description="Composite key: '{tenant_id}_{customer_phone}'")
    tenant_id: str
    customer_phone: str = Field(..., description="E.164 format, e.g. '+919876543210'")
    status: SessionStatus = SessionStatus.WAITING_FOR_BOT
    context_vars: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value store for session context (e.g. last_intent).",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
