# LeadAgent — WhatsApp Lead Management Agent (MCP-powered)

**AI agent for Indian SMBs to manage sales leads via WhatsApp in plain English/Hindi.**

LeadAgent lets a small business owner text a WhatsApp bot like they'd text an employee — *"which leads haven't I called in 2 days?"*, *"mark Ramesh as converted"*, *"send a follow-up to Priya"* — and get safe, auditable results. No app, no dashboard, no login.

Under the hood: a **real MCP server** with typed tools, a **Groq-powered agent loop** that decides which tools to call, and a **FastAPI webhook** wired to Meta's WhatsApp Cloud API. Every write that matters asks for confirmation first. Every query is scoped to one owner's phone number.

---

## Architecture

```
┌─────────────────┐     webhook      ┌──────────────────┐
│  Business Owner │ ───────────────► │  FastAPI         │
│  (WhatsApp)     │ ◄─────────────── │  POST /webhook   │
└─────────────────┘    reply via     └────────┬─────────┘
                         Graph API              │
                                                ▼
                                     ┌──────────────────┐
                                     │  Groq Agent Loop │
                                     │  (tool-calling)  │
                                     │  openai/gpt-oss  │
                                     │  -120b           │
                                     └────────┬─────────┘
                                              │ calls
                                              ▼
                                     ┌──────────────────┐
                                     │  MCP Tools (×9)  │
                                     │  read + write    │
                                     └────────┬─────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │  SQLite (leads,  │
                                     │  action_log)     │
                                     └──────────────────┘
```

**Request flow:** WhatsApp message → HMAC-validated webhook → `handle_message()` → Groq selects MCP tools → SQLite read/write → confirmation gate for sends & terminal status changes → reply sent back on WhatsApp.

---

## Features

- **Plain English/Hindi commands** — owners interact entirely over WhatsApp
- **9 MCP tools** — 4 read (`list_leads`, `get_stale_leads`, `search_leads`, `get_lead_details`) + 5 write (`create_lead`, `update_lead_status`, `add_lead_note`, `draft_followup_message`, `send_whatsapp_message`)
- **Confirmation flow** — destructive actions (send message, mark `converted`/`lost`) require an explicit YES before execution
- **Owner isolation** — every query filters by `owner_phone`; one business cannot see or touch another's data
- **Full audit log** — every write recorded in `action_log` with human-readable details
- **Secure by design** — HMAC webhook validation, parameterized SQL only, scoped permissions, no stack traces to users

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| API / Webhook | FastAPI + Uvicorn |
| Agent protocol | MCP (official Python SDK, FastMCP) |
| LLM | Groq API — `openai/gpt-oss-120b` (OpenAI-compatible tool calling) |
| Messaging | Meta WhatsApp Cloud API |
| Database | Supabase Postgres (production) / SQLite (local tests) |
| Rate limiting | slowapi (30 req/min on webhook) |
| Hosting target | Render.com |

---

## Local development

### 1. Clone and install

```bash
git clone https://github.com/ayushanand27/mcp-build.git
cd mcp-build/lead-agent

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Fill in all values (see table below). **Never commit `.env`.**

### 3. Run tests

```bash
python scripts/test_read_tools.py
python scripts/test_write_tools.py
python scripts/test_agent.py      # requires GROQ_API_KEY
python scripts/test_webhook.py
pytest tests/ -v
```

### 4. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

- Health check: `http://localhost:8000/health`
- Webhook: `http://localhost:8000/webhook` (use ngrok for Meta setup)

### 5. Run MCP server standalone (optional)

```bash
python -m app.mcp_server
```

Register in Cursor or Claude Desktop, or inspect with `mcp dev app/mcp_server.py`.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for the agent loop (`openai/gpt-oss-120b`) |
| `WHATSAPP_TOKEN` | Yes | Meta permanent access token for sending messages |
| `WHATSAPP_PHONE_NUMBER_ID` | Yes | WhatsApp Business phone number ID from Meta dashboard |
| `WHATSAPP_VERIFY_TOKEN` | Yes | Arbitrary string for `GET /webhook` subscription verification |
| `WHATSAPP_APP_SECRET` | Yes | App secret for `X-Hub-Signature-256` HMAC validation |
| `DATABASE_URL` | Production | Supabase Postgres URI (transaction pooler, port 6543) |
| `DATABASE_PATH` | Local only | SQLite path when `DATABASE_URL` is unset (default: `leads.db`) |

---

## Example WhatsApp commands

| Owner sends | Agent does |
|-------------|------------|
| `list all my leads` | Returns a numbered list of leads with status |
| `which leads haven't been contacted in 2 days?` | Calls `get_stale_leads` (excludes converted/lost) |
| `mark Ramesh as converted` | Queues status update → asks YES → updates on confirm |
| `send a follow up to Priya` | Drafts message → shows preview → sends only after YES |
| `add note to Amit: called twice, no answer` | Appends timestamped note to Amit's lead |

Hindi works too — the agent replies in the same language the owner uses.

---

## Security

| Control | Implementation |
|---------|----------------|
| **Owner isolation** | Every `leads` / `action_log` query uses `WHERE owner_phone = ?`; lead writes use `WHERE id = ? AND owner_phone = ?` |
| **Webhook authenticity** | `X-Hub-Signature-256` verified with `hmac.compare_digest` + `WHATSAPP_APP_SECRET` |
| **Confirmation gate** | `send_whatsapp_message` and terminal status changes stored in `PendingActionStore` until owner confirms |
| **Audit trail** | `action_log` records every write (`lead_created`, `status_updated`, `note_added`, `message_sent`) |
| **Safe errors** | Generic messages to owners; details logged server-side only |
| **SQL injection** | Parameterized queries only — no string-interpolated SQL |
| **Rate limiting** | 30 requests/minute per IP on `POST /webhook` |

Run isolation tests anytime:

```bash
pytest tests/test_owner_isolation.py -v
```

---

## Project structure

```
lead-agent/
├── app/
│   ├── main.py            # FastAPI webhook + health routes
│   ├── agent.py           # Groq agent loop + confirmation flow
│   ├── mcp_server.py      # MCP server (9 tools)
│   ├── lead_service.py    # Business logic layer
│   ├── db.py              # Postgres (Supabase) + SQLite queries
│   ├── models.py          # Pydantic models + tool schemas
│   ├── pending_actions.py # In-memory confirmation store
│   └── whatsapp.py        # Meta Cloud API helpers
├── scripts/
│   ├── test_read_tools.py
│   ├── test_write_tools.py
│   ├── test_agent.py
│   └── test_webhook.py
├── tests/
│   └── test_owner_isolation.py
├── migrations/
│   └── 001_leads_schema.sql
├── DEPLOY.md              # Meta + Supabase + Render setup guide
└── .env.example
```

---

## Test results

All local test suites passing:

| Suite | Command | Status |
|-------|---------|--------|
| Read tools | `python scripts/test_read_tools.py` | Pass |
| Write tools | `python scripts/test_write_tools.py` | Pass |
| Agent loop | `python scripts/test_agent.py` | Pass |
| Webhook | `python scripts/test_webhook.py` | Pass |
| Owner isolation | `pytest tests/ -v` | 3/3 pass |

---

## Deployment

**Full setup guide:** see **[DEPLOY.md](DEPLOY.md)** — Meta webhook, Supabase Postgres, Render env vars, and keep-alive.

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set `DATABASE_URL` (Supabase) plus all WhatsApp/Groq env vars on Render. Point Meta's webhook to `https://<your-app>.onrender.com/webhook`.

---

## License

MIT
