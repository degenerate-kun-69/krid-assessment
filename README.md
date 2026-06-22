# Krid AI — Multi-Tenant WhatsApp Orchestrator

> LangGraph-powered WhatsApp AI agent SaaS. Multiple companies (tenants) each get their own bot personality, media library, and conversation history — all on one backend.

---

## Architecture

```
[WhatsApp Customer]
        │  (inbound message)
        ▼
[Twilio WhatsApp] ──POST──► [FastAPI Webhook /api/webhooks/whatsapp]
                                      │
                              200 OK immediately
                                      │
                              BackgroundTask ──► [LangGraph Agent]
                                                       │
                              ┌────────────────────────┤
                              │                        │
                         ┌────▼─────┐          ┌───────▼────────┐
                         │Acknowledge│          │Context Retriever│
                         │ Node     │          │ Node           │
                         │log + ack │          │tenant+history  │
                         └────┬─────┘          └───────┬────────┘
                              │                        │
                         ┌────▼─────────────────────── ▼ ──────┐
                         │         LLM Reasoning Node          │
                         │  Ollama llama3.1:8b + tool calls    │
                         │  → decides text / image / document  │
                         └────────────────────┬────────────────┘
                                              │
                                    ┌─────────▼──────────┐
                                    │   Dispatcher Node   │
                                    │ send WA + log to DB │
                                    └─────────────────────┘
                                              │
                                    [MongoDB Atlas]
                                              │
                              ┌───────────────▼──────────────────┐
                              │   Dashboard Frontend (static JS)  │
                              │  polls GET /api/tenants/sessions  │
                              └───────────────────────────────────┘
```

---

## Project Structure

```
Krid ai/
├── app/
│   ├── main.py               # FastAPI entry point
│   ├── config.py             # Settings from .env
│   ├── database/
│   │   ├── mongo.py          # Motor async client
│   │   └── seed.py           # Seeds Tenant A & B with media libraries
│   ├── models/
│   │   ├── tenant.py
│   │   ├── session.py
│   │   └── message.py
│   ├── routers/
│   │   ├── webhook.py        # Twilio webhook endpoints
│   │   └── dashboard.py      # Frontend API endpoints
│   ├── services/
│   │   ├── whatsapp.py       # Twilio WhatsApp API helpers
│   │   └── langgraph_agent.py # Graph definition
│   └── nodes/
│       ├── acknowledge.py
│       ├── context_retriever.py
│       ├── llm_reasoning.py
│       └── dispatcher.py
├── media/                     # Self-hosted media assets for tenants
│   ├── minecraft/             # 10 Minecraft scene images
│   │   ├── house.png
│   │   ├── cave.png
│   │   ├── village.png
│   │   ├── nether.png
│   │   ├── castle.png
│   │   ├── ocean_monument.png
│   │   ├── ender_dragon.png
│   │   ├── farm.png
│   │   ├── enchanting.png
│   │   └── snow_biome.png
│   ├── sofas/                 # 3 luxury sofa images
│   │   ├── white_sectional.png
│   │   ├── green_velvet.png
│   │   └── leather_chesterfield.png
│   ├── restaurant_menu.pdf    # Sample restaurant menu (PDF)
│   └── generate_menu_pdf.py   # Script to regenerate the PDF
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── TWILIO_SETUP.md           # How to set up the Twilio WhatsApp Sandbox
└── README.md
```

---

## Media Library & Rich Media Support

The system supports sending **images**, **documents (PDFs)**, and **text** via WhatsApp using Twilio's `MediaUrl` parameter. Each tenant has a `media_library` stored in MongoDB Atlas that maps keywords to publicly accessible URLs.

### How It Works

1. **Media assets** are stored in the `media/` directory and served by FastAPI at `/media/*`
2. On startup, `seed.py` builds absolute URLs using `BASE_URL` + `/media/<path>` and writes them to MongoDB Atlas as part of each tenant's `media_library` field
3. When a customer sends a message, the **LLM Reasoning Node** checks if the message matches a media keyword and calls `attach_image` or `attach_document` tools
4. The **Dispatcher Node** sends the media via Twilio's API using the public URL

### Tenant A — Luxury Furniture Store

| Keyword | Type | Asset |
|---|---|---|
| `sofa` / `white sofa` | Image | White sectional sofa |
| `green sofa` | Image | Green velvet sofa |
| `leather sofa` | Image | Leather chesterfield sofa |
| `showroom` | Image | Showroom view |
| `table` | Image | Dining table |
| `catalog` / `menu` | PDF | Restaurant menu catalog |

### Tenant B — Minecraft Gaming Store

| Keyword | Type | Asset |
|---|---|---|
| `house` | Image | Minecraft wooden house |
| `cave` | Image | Underground cave with lava & diamonds |
| `village` | Image | Village at sunset |
| `nether` | Image | Nether dimension with ghast |
| `castle` | Image | Epic stone castle with moat |
| `ocean` / `ocean monument` | Image | Underwater ocean monument |
| `dragon` / `ender dragon` | Image | Ender Dragon boss fight |
| `farm` | Image | Organized crop farm |
| `enchanting` | Image | Enchanting room with books |
| `snow` | Image | Snowy mountain biome with aurora |
| `catalog` / `menu` | PDF | Store catalog |

### MongoDB Atlas Schema (Tenant Document)

```json
{
  "tenant_id": "tenant_b",
  "name": "Minecraft Gaming Store",
  "system_prompt": "You are an enthusiastic gaming advisor...",
  "media_library": {
    "house": "https://<your-app>.onrender.com/media/minecraft/house.png",
    "cave": "https://<your-app>.onrender.com/media/minecraft/cave.png",
    "castle": "https://<your-app>.onrender.com/media/minecraft/castle.png",
    "catalog": "https://<your-app>.onrender.com/media/restaurant_menu.pdf"
  }
}
```

### Twilio Media Sending (Template)

The Twilio Whatsapp API sends media using the `MediaUrl` parameter in a standard REST call:

```python
# Download the helper library from https://www.twilio.com/docs/python/install
import os
from twilio.rest import Client

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
client = Client(account_sid, auth_token)

message = client.messages.create(
    media_url=["https://<your-app>.onrender.com/media/minecraft/castle.png"],
    from_="whatsapp:+14155238886",
    to="whatsapp:+15017122661",
)

print(message.sid)
```

In Krid AI, this is handled automatically by `app/services/whatsapp.py` using the raw Twilio REST API with `httpx`:

```python
payload = {
    "From": "whatsapp:+14155238886",
    "To": "whatsapp:+919876543210",
    "Body": "Here's the castle build you asked for! 🏰",
    "MediaUrl": "https://<your-app>.onrender.com/media/minecraft/castle.png",
}
```

---

## Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com/download/linux) installed on your machine (for local LLM)
- Docker + Docker Compose (for containerised local dev)
- MongoDB Atlas account (free M0 tier) — OR use the local MongoDB in docker-compose for dev
- Twilio account (free sandbox) — see `TWILIO_SETUP.md`

### Install Ollama & pull the model

```bash
# Install Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the model (fits in 16 GB VRAM)
ollama pull llama3.1:8b

# Verify it's running
ollama run llama3.1:8b "Hello!"
```

> **AMD GPU**: Ollama uses ROCm automatically if you installed it via the official script.
> Check GPU usage: `rocm-smi` while running a prompt.

---

## Local Development (without Docker)

### 1. Clone & set up environment

```bash
git clone <repo-url>
cd "Krid ai"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in:
#   MONGODB_URI          — Atlas URI or mongodb://localhost:27017
#   TWILIO_ACCOUNT_SID   — from Twilio Console
#   TWILIO_AUTH_TOKEN     — from Twilio Console
#   TWILIO_WHATSAPP_NUMBER — sandbox: whatsapp:+14155238886
#   BASE_URL             — http://localhost:8080 (local) or your deployed URL
#   OLLAMA_*             — defaults work if Ollama is running locally
nano .env
```

### 3. Seed the database

```bash
python -m app.database.seed
# Output: [Seed] Inserted tenant: Luxury Furniture Store
#         [Seed] Inserted tenant: Minecraft Gaming Store
```

This writes the tenant documents (including `media_library` URL mappings) to MongoDB Atlas.

### 4. Start the server

```bash
uvicorn app.main:app --reload --port 8080
```

Open **http://localhost:8080** — the dashboard should load.
Media assets are served at **http://localhost:8080/media/*** (e.g. `/media/minecraft/castle.png`).

### 5. Test without WhatsApp (Chat Simulator)

The dashboard includes a built-in **Chat Simulator** that triggers the full LangGraph pipeline without needing a real WhatsApp connection. Click the 🧪 button in the sidebar.

---

## Local Development (with Docker Compose)

```bash
# Copy and fill in your .env
cp .env.example .env

# Start everything (MongoDB + backend)
docker compose up --build

# Dashboard: http://localhost:8080
# Ollama must still be running on the host
```

---

## Deployment on Render

1. **Push to GitHub** — make sure `.env` is in `.gitignore` (it is)
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Environment**: Docker
   - **Dockerfile path**: `./Dockerfile`
   - **Port**: `8080`
5. Add **Environment Variables** in the Render dashboard (not in the repo):
   ```
   MONGODB_URI            = mongodb+srv://...  (your Atlas URI)
   TWILIO_ACCOUNT_SID     = ACxxxxxxxxx
   TWILIO_AUTH_TOKEN       = xxxxxxxx
   TWILIO_WHATSAPP_NUMBER = whatsapp:+14155238886
   BASE_URL               = https://<your-app>.onrender.com
   OLLAMA_BASE_URL        = https://<your-ollama-server>  (or ngrok tunnel to local)
   OLLAMA_MODEL           = llama3.1:8b
   ```
6. Click **Deploy**
7. Copy the Render public URL → use it in Twilio's webhook config (see `TWILIO_SETUP.md` Step 4)

> **Important**: Set `BASE_URL` to your Render public URL so that media library URLs in MongoDB Atlas point to the correct host. Twilio needs publicly accessible URLs to send media.

> **Note on Ollama in production**: Render free tier doesn't have GPUs. For production, either:
> - Run Ollama on a separate GPU VM and expose it (set `OLLAMA_BASE_URL` to that server)
> - Use an ngrok tunnel from your local machine (quick demo only)

---

## Environment Variables Reference

| Variable | Description | Example |
|---|---|---|
| `MONGODB_URI` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `DB_NAME` | Database name | `krid_whatsapp` |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_WHATSAPP_NUMBER` | Twilio WhatsApp sender | `whatsapp:+14155238886` |
| `BASE_URL` | Public URL for media assets | `https://krid-ai.onrender.com` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Model name in Ollama | `llama3.1:8b` |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/webhooks/whatsapp` | Health check |
| `POST` | `/api/webhooks/whatsapp` | Inbound WhatsApp message handler (Twilio format) |
| `GET` | `/api/tenants` | List all tenants |
| `GET` | `/api/tenants/{id}/sessions` | Sessions for a tenant |
| `GET` | `/api/sessions/{id}/messages` | Message thread |
| `POST` | `/api/broadcast` | Broadcast message to phone list |
| `POST` | `/api/simulate` | Simulate inbound message (testing) |
| `GET` | `/media/*` | Static media assets (images, PDFs) |
| `GET` | `/` | Dashboard frontend |

---

## LangGraph State Flow

```
AgentState fields:
  tenant_id          ← set by webhook (from Twilio "To" number mapping)
  customer_phone     ← from Twilio "From" field
  wa_message_id      ← Twilio MessageSid
  inbound_text       ← customer's message (Twilio "Body")
  inbound_media_url  ← if customer sent media (Twilio "MediaUrl0")
  tenant_doc         ← filled by context_retriever (system_prompt + media_library)
  chat_history       ← last 5 messages from MongoDB
  llm_reply          ← filled by llm_reasoning (text to send)
  media_attachment   ← filled by llm_reasoning if tool was called
  session_id         ← filled by acknowledge ({tenant_id}_{phone})

Node sequence:
  acknowledge → context_retriever → llm_reasoning → dispatcher → END
```

---

## Making Your First Real Test

1. Complete Twilio Sandbox setup (see `TWILIO_SETUP.md`)
2. Start Ollama: `ollama serve`
3. Start the backend: `uvicorn app.main:app --reload --port 8080`
4. Expose locally with ngrok: `ngrok http 8080`
5. Update `BASE_URL` in `.env` to the ngrok URL (e.g. `https://xxxx.ngrok-free.app`)
6. Set the ngrok URL as the Twilio webhook URL (see `TWILIO_SETUP.md` Step 4)
7. Send a WhatsApp message to the Twilio Sandbox number
8. Watch the server logs — you should see all 4 nodes execute
9. Open `http://localhost:8080` and see the conversation appear on the dashboard

### Testing Media (Example WhatsApp Messages)

**Tenant A (Luxury Furniture Store):**
- _"Can you show me a sofa?"_ → Bot sends white sectional sofa image
- _"I'd like to see the leather sofa"_ → Bot sends chesterfield sofa image
- _"Send me the catalog"_ → Bot sends restaurant menu PDF

**Tenant B (Minecraft Gaming Store):**
- _"Show me a castle build"_ → Bot sends epic castle image
- _"What does the nether look like?"_ → Bot sends nether dimension image
- _"I want to see the ender dragon"_ → Bot sends dragon boss fight image
