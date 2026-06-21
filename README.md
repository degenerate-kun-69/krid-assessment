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
│   │   └── seed.py           # Seeds Tenant A & B
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
#   OLLAMA_*             — defaults work if Ollama is running locally
nano .env
```

### 3. Seed the database

```bash
python -m app.database.seed
# Output: [Seed] Inserted tenant: Luxury Furniture Store
#         [Seed] Inserted tenant: Automotive Care Center
```

### 4. Start the server

```bash
uvicorn app.main:app --reload --port 8080
```

Open **http://localhost:8080** — the dashboard should load.

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
   OLLAMA_BASE_URL        = https://<your-ollama-server>  (or ngrok tunnel to local)
   OLLAMA_MODEL           = llama3.1:8b
   ```
6. Click **Deploy**
7. Copy the Render public URL → use it in Twilio's webhook config (see `TWILIO_SETUP.md` Step 4)

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
5. Set the ngrok URL as the Twilio webhook URL (see `TWILIO_SETUP.md` Step 4)
6. Send a WhatsApp message to the Twilio Sandbox number
7. Watch the server logs — you should see all 4 nodes execute
8. Open `http://localhost:8080` and see the conversation appear on the dashboard
