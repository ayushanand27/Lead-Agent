# mcp-build — WhatsApp Lead Management Agent

A WhatsApp bot that lets small business owners manage sales leads using plain English/Hindi messages — no app, no dashboard, no login. The owner texts the bot like they'd text an employee; an MCP-powered agent reads/writes lead data safely and asks for confirmation before any action that changes data or sends a message to a customer.

**Repository:** [github.com/ayushanand27/mcp-build](https://github.com/ayushanand27/mcp-build)

---

## What this is

| Layer | Role |
|-------|------|
| **WhatsApp** | Meta Cloud API webhook — how owners send/receive messages |
| **Agent loop** | Groq (`openai/gpt-oss-120b`) decides which tools to call from natural language |
| **MCP server** | Typed tools for lead CRUD, search, follow-up drafts, and outbound WhatsApp |
| **SQLite** | Single-file `leads.db` — every query scoped by `owner_phone` |

This is not a toy chatbot. Every write operation requires confirmation where specified. Every action is scoped to the requesting owner's phone number. Every write is logged in `action_log`.

---

## Tech stack

- **Backend:** Python 3.11+, FastAPI
- **Database:** SQLite (`leads.db`), parameterized queries only
- **MCP:** Official [`mcp`](https://github.com/modelcontextprotocol/python-sdk) Python SDK (FastMCP)
- **LLM:** Groq API, model `openai/gpt-oss-120b` (OpenAI-compatible tool calling)
- **WhatsApp:** Meta WhatsApp Cloud API (webhooks + Graph API)
- **Hosting target:** Render.com free tier (`uvicorn` single process)
- **Secrets:** `.env` via `python-dotenv` (never committed)

---

## Build progress

| Step | Description | Status |
|------|-------------|--------|
| 1 | SQLite schema + seed leads | ✅ Done |
| 2 | MCP read tools (4 tools) | ✅ Done |
| 3 | Write tools + `PendingActionStore` confirmation | 🔲 Pending |
| 4 | Groq agent loop + defensive validation | 🔲 Pending |
| 5 | FastAPI webhook + WhatsApp integration | 🔲 Pending |
| 6 | Deploy to Render | 🔲 Pending |

---

## Quick start

All application code lives in [`lead-agent/`](lead-agent/).

```bash
git clone https://github.com/ayushanand27/mcp-build.git
cd mcp-build/lead-agent

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # fill in keys when wiring Groq / WhatsApp
```

### Test read tools locally (no API keys needed)

```bash
python scripts/test_read_tools.py
pytest tests/ -v
```

### Run the MCP server (stdio)

```bash
python -m app.mcp_server
```

Register in Cursor or Claude Desktop, or inspect with:

```bash
mcp dev app/mcp_server.py
```

---

## Environment variables

Copy `lead-agent/.env.example` to `lead-agent/.env`:

| Variable | Required for | Description |
|----------|--------------|-------------|
| `GROQ_API_KEY` | Step 4+ | Groq API key for the agent loop |
| `WHATSAPP_TOKEN` | Step 5+ | Meta permanent access token |
| `WHATSAPP_PHONE_NUMBER_ID` | Step 5+ | Your WhatsApp Business phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | Step 5+ | Arbitrary string for webhook verification |
| `WHATSAPP_APP_SECRET` | Step 5+ | App secret for webhook signature validation |
| `DATABASE_PATH` | Optional | Override default `leads.db` path |

---

## Data model

### `leads`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Autoincrement |
| `owner_phone` | TEXT | **Security boundary** — every query filters on this |
| `name` | TEXT | Lead name |
| `phone` | TEXT | Lead phone |
| `source` | TEXT | e.g. IndiaMART, WhatsApp, Walk-in |
| `status` | TEXT | `new`, `contacted`, `warm`, `hot`, `converted`, `lost` |
| `notes` | TEXT | Nullable |
| `last_contacted_at` | TIMESTAMP | Nullable |
| `created_at` | TIMESTAMP | Default now |

### `action_log`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Autoincrement |
| `owner_phone` | TEXT | Owner who triggered the action |
| `action` | TEXT | e.g. `status_updated`, `message_sent` |
| `details` | TEXT | Human-readable description |
| `timestamp` | TIMESTAMP | Default now |

---

## MCP tools

### Read tools (no confirmation)

| Tool | Description |
|------|-------------|
| `list_leads` | List leads, optional status filter |
| `get_stale_leads` | Leads not contacted in N days (excludes converted/lost) |
| `search_leads` | Fuzzy match on name, phone, source, notes |
| `get_lead_details` | Full record for one lead |

### Write tools (planned — step 3+)

| Tool | Confirmation |
|------|--------------|
| `create_lead` | TBD |
| `update_lead_status` | Required for `converted` / `lost` |
| `add_lead_note` | TBD |
| `draft_followup_message` | Read-only draft (Groq) |
| `send_whatsapp_message` | **Always** requires owner YES |

---

## Project layout

```
mcp-build/
├── README.md                 # This file
└── lead-agent/
    ├── .env.example
    ├── .gitignore
    ├── requirements.txt
    ├── pytest.ini
    ├── app/
    │   ├── main.py           # FastAPI app + webhooks (step 5)
    │   ├── db.py             # SQLite schema + queries
    │   ├── mcp_server.py     # MCP server + tool definitions
    │   ├── lead_service.py   # Business logic
    │   ├── agent.py          # Groq agent loop (step 4)
    │   ├── pending_actions.py# Confirmation flow store
    │   ├── whatsapp.py       # Meta Cloud API helpers
    │   └── models.py         # Pydantic models
    ├── scripts/
    │   └── test_read_tools.py
    └── tests/
        └── test_owner_isolation.py
```

---

## Security

- Every DB query on `leads` / `action_log` filters by `owner_phone`
- All SQL is parameterized (no string interpolation)
- Secrets only from environment variables; `.env` is gitignored
- Write tools require confirmation — agent cannot bypass
- Status values validated against an allowlist
- Webhook rate limiting (step 5)
- Errors never leak stack traces to WhatsApp users
- `action_log` records every write for audit

Run isolation tests anytime:

```bash
cd lead-agent && pytest tests/test_owner_isolation.py -v
```

---

## Deployment (Render — step 6)

Planned start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set all env vars from `.env.example` in the Render dashboard. Point Meta webhook to `https://<your-app>.onrender.com/webhook`.

---

## License

MIT (or update as you prefer)
