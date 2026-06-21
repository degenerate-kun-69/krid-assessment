# Multi-Tenant Agentic WhatsApp Orchestrator — Implementation Plan (Updated)

A 48-hour assessment to build a cloud-native SaaS that lets multiple companies (tenants)
handle customer queries over WhatsApp using a locally-hosted LLM via Ollama + LangGraph.

---

## Confirmed Decisions

| Concern | Decision |
|---|---|
| **LLM** | **Ollama** (local, GPU-accelerated) — model `llama3.1:8b` |
| **Database** | **MongoDB Atlas** (M0 free tier) — user will create account & add URI to `.env` |
| **Frontend** | **Plain HTML + CSS + Vanilla JS** — served as static files by FastAPI |
| **Deployment** | **Render** — single `Dockerfile` + `docker-compose.yml` for local dev |
| **Bonus features** | **Skipped** |

---

## Packages to Install (User Must Install — AMD GPU notes inline)

> [!IMPORTANT]
> Do NOT run `pip install` yourself. The user needs to install these after activating `.venv`. AMD GPU-specific notes are included.

```bash
# Activate venv first
source .venv/bin/activate

# Install all Python deps
pip install -r requirements.txt
```

**`requirements.txt` contents:**
```
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
motor>=3.4.0          # async MongoDB driver
pymongo>=4.7.0        # sync MongoDB (seed script)
httpx>=0.27.0         # async HTTP (WhatsApp API calls)
langgraph>=0.2.0
langchain>=0.2.0
langchain-ollama>=0.1.3   # Ollama ↔ LangChain bridge
langchain-core>=0.2.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
python-dotenv>=1.0.0
python-multipart>=0.0.9   # FastAPI file handling
```

> [!IMPORTANT]
> **Ollama AMD GPU setup** — Ollama must be installed on the *host* (not in Docker) to access the GPU.
> Install Ollama for ROCm: https://ollama.com/download/linux
> After install: `ollama pull llama3.1:8b`
> Verify GPU is used: `ollama run llama3.1:8b` — watch GPU memory with `rocm-smi`

---

## Project File Structure

```
Krid ai/                          ← workspace root
├── app/
│   ├── __init__.py
│   ├── main.py                   ← FastAPI app, mounts static frontend
│   ├── config.py                 ← pydantic-settings, reads .env
│   ├── database/
│   │   ├── __init__.py
│   │   ├── mongo.py              ← Motor async client & collection refs
│   │   └── seed.py               ← Seeds Tenant A & B with media library
│   ├── models/
│   │   ├── __init__.py
│   │   ├── tenant.py             ← Tenant Pydantic model
│   │   ├── session.py            ← ChatSession model + Status enum
│   │   └── message.py            ← MessageAuditLog model
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── webhook.py            ← GET verify + POST /webhook (async bg task)
│   │   └── dashboard.py          ← REST endpoints consumed by the frontend
│   ├── services/
│   │   ├── __init__.py
│   │   ├── whatsapp.py           ← httpx helpers: read/typing/text/image/doc
│   │   └── langgraph_agent.py    ← AgentState + compiled LangGraph
│   └── nodes/
│       ├── __init__.py
│       ├── acknowledge.py        ← Node 1: read receipt + typing on
│       ├── context_retriever.py  ← Node 2: tenant doc + last 5 messages
│       ├── llm_reasoning.py      ← Node 3: Ollama LLM + tool decision
│       └── dispatcher.py         ← Node 4: send WA message + log to DB
├── frontend/
│   ├── index.html                ← Single-page dashboard
│   ├── style.css                 ← Dark theme, responsive layout
│   └── app.js                    ← Vanilla JS: fetch API, render threads
├── Dockerfile                    ← Backend + static frontend in one image
├── docker-compose.yml            ← Backend + local MongoDB for dev
├── requirements.txt
├── .env.example                  ← Template for all required env vars
├── META_SETUP.md                 ← Step-by-step Meta Developer setup guide
└── README.md                     ← Local run + Render deployment guide
```

---

## Proposed Changes (Skeleton)

### Root Config

#### [NEW] `requirements.txt` — All Python dependencies
#### [NEW] `.env.example` — Env var template
#### [NEW] `.gitignore` — Updated with `__pycache__`, `.env`, etc.

---

### Backend — Config & Database

#### [NEW] `app/config.py`
`pydantic-settings` `Settings` class reading all vars from `.env`:
- `MONGODB_URI`, `DB_NAME`
- `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_API_VERSION`
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`

#### [NEW] `app/database/mongo.py`
Motor `AsyncIOMotorClient` singleton. Exposes `db.tenants`, `db.sessions`, `db.messages`.

#### [NEW] `app/database/seed.py`
Seeds two tenants if they don't exist:
- **Tenant A** — Luxury Furniture: system prompt + media library (`catalog`, `sofa`, `table`)
- **Tenant B** — Automotive Care: system prompt + media library (`invoice`, `repair`, `manual`)

---

### Backend — Models

#### [NEW] `app/models/tenant.py`
```
Tenant: tenant_id, name, system_prompt, media_library: dict[str, str]
```

#### [NEW] `app/models/session.py`
```
SessionStatus: WAITING_FOR_BOT | AGENT_RESPONDING | RESOLVED | NEEDS_HUMAN
ChatSession: session_id, tenant_id, customer_phone, status, context_vars, created_at, updated_at
```

#### [NEW] `app/models/message.py`
```
MessageDirection: inbound | outbound
MessageLog: message_id, session_id, tenant_id, direction, sender,
            text, media_url, mime_type, timestamp, bot_was_typing
```

---

### Backend — Services

#### [NEW] `app/services/whatsapp.py`
Async `httpx.AsyncClient` wrapper:
- `mark_as_read(wa_message_id)` → POST mark read to Meta Graph API
- `send_typing(to)` → POST typing indicator ON
- `send_text(to, body)` → POST text message
- `send_image(to, url, caption)` → POST image message
- `send_document(to, url, filename)` → POST document message

#### [NEW] `app/services/langgraph_agent.py`
`AgentState` TypedDict + `build_graph()` that wires all 4 nodes into a compiled `StateGraph`.
Exposes `agent = build_graph()` singleton used by the webhook router.

---

### Backend — LangGraph Nodes

#### [NEW] `app/nodes/acknowledge.py`
1. Fire `mark_as_read` + `send_typing` (async, non-blocking)
2. Upsert session in MongoDB → status `AGENT_RESPONDING`
3. Save inbound message to `messages` collection

#### [NEW] `app/nodes/context_retriever.py`
1. Fetch tenant doc from `tenants` collection
2. Fetch last 5 messages for `(tenant_id, customer_phone)` from `messages`
3. Return updated state with `tenant_doc` and `chat_history`

#### [NEW] `app/nodes/llm_reasoning.py`
1. Build `ChatOllama` with `bind_tools([attach_image_tool, attach_document_tool])`
2. Build prompt from `tenant_doc.system_prompt` + `chat_history` + inbound text
3. If LLM calls a tool → populate `state["media_attachment"]`
4. Always set `state["llm_reply"]`

#### [NEW] `app/nodes/dispatcher.py`
1. Call `send_image` or `send_document` if `media_attachment` is set
2. Call `send_text` with `llm_reply`
3. Save outbound message to `messages` collection
4. Update session status → `WAITING_FOR_BOT`

---

### Backend — Routers

#### [NEW] `app/routers/webhook.py`
- `GET /api/webhooks/whatsapp` — Meta challenge verification
- `POST /api/webhooks/whatsapp` — Parse payload, return `200 OK` immediately, run agent via `BackgroundTasks`

#### [NEW] `app/routers/dashboard.py`
- `GET /api/tenants` → list all tenants
- `GET /api/tenants/{tenant_id}/sessions` → active sessions
- `GET /api/sessions/{session_id}/messages` → message thread
- `POST /api/broadcast` → send template to a list of numbers

#### [NEW] `app/main.py`
- `FastAPI()` app instance
- Include webhook & dashboard routers
- Mount `frontend/` as `StaticFiles` at `/`
- Startup event: run `seed.py`

---

### Frontend

#### [NEW] `frontend/index.html`
Single-page dashboard skeleton:
- Top nav with app name
- Tenant switcher tabs (Tenant A / Tenant B)
- Left panel: session list (phone numbers + status badges)
- Right panel: chat thread (user/bot bubbles, PDF badges, typing indicator)
- Broadcast drawer (slide-in panel)

#### [NEW] `frontend/style.css`
Dark theme, CSS variables, chat bubble styles, status badge colors, animations.

#### [NEW] `frontend/app.js`
Vanilla JS:
- `fetchTenants()`, `fetchSessions(tenantId)`, `fetchMessages(sessionId)`
- Render session list, chat thread, media badges
- Poll for updates every 3 seconds
- Broadcast drawer toggle

---

### Deployment

#### [NEW] `Dockerfile`
```
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY frontend/ ./frontend/
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### [NEW] `docker-compose.yml`
Services:
- `mongodb` — mongo:7 (local dev only)
- `backend` — built from Dockerfile, `OLLAMA_BASE_URL=http://host.docker.internal:11434`
  (Ollama runs on host for GPU access; `extra_hosts: host-gateway` enables container→host)

#### [NEW] `META_SETUP.md`
Step-by-step guide for creating Meta Developer account, WhatsApp app, sandbox number, getting tokens.

#### [NEW] `README.md`
Local dev instructions, Render deployment steps, LangGraph diagram, env var reference.

---

## Verification Plan

| Step | What to test |
|---|---|
| `pip install -r requirements.txt` | No errors |
| `python -m app.database.seed` | Prints "Seeded Tenant A and B" |
| `uvicorn app.main:app --reload` | Server starts on 8080 |
| `GET /api/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=test&hub.challenge=abc` | Returns `abc` |
| `GET /api/tenants` | Returns 2 tenant docs |
| POST mock Meta payload to `/api/webhooks/whatsapp` | Returns 200 immediately, logs agent run |
| Open `http://localhost:8080` | Dashboard renders |
