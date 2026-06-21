"""
app/config.py — Application settings loaded from .env via pydantic-settings.
All other modules import `settings` from here. Never hard-code secrets.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── MongoDB ────────────────────────────────────────────────
    MONGODB_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "krid_whatsapp"

    # ── Twilio WhatsApp API ────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    # The Twilio WhatsApp sandbox number (e.g. "whatsapp:+14155238886")
    # or your approved Twilio WhatsApp sender number.
    TWILIO_WHATSAPP_NUMBER: str = ""

    # ── Ollama (local LLM) ─────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # ── Convenience property ───────────────────────────────────
    @property
    def twilio_messages_url(self) -> str:
        """Twilio REST API endpoint for sending messages."""
        return (
            f"https://api.twilio.com/2010-04-01/Accounts"
            f"/{self.TWILIO_ACCOUNT_SID}/Messages.json"
        )


# Single shared instance — import this everywhere
settings = Settings()
