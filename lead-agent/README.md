# WhatsApp Lead Management Agent

A WhatsApp bot for small business owners to manage sales leads via plain English/Hindi messages. Built with FastAPI, SQLite, the official MCP Python SDK, and Groq.

## Current status

**Steps 1–2 complete:** SQLite schema, seed data, and four MCP read tools (`list_leads`, `get_stale_leads`, `search_leads`, `get_lead_details`).

## Setup

```bash
cd lead-agent
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # fill in keys when wiring WhatsApp/Groq (not needed for read-tool test)
```

## Test locally (read tools)

```bash
python scripts/test_read_tools.py
```

This script will:

1. Create `leads.db` with the `leads` and `action_log` tables
2. Seed five sample leads for a test owner phone number
3. Exercise all four read tools via both the service layer and MCP tool wrappers
4. Verify owner isolation (owner B cannot read owner A's lead id=1)

Run pytest for isolation tests:

```bash
pytest tests/ -v
```

## Run the MCP server (stdio)

The MCP server can be registered in Cursor or Claude Desktop:

```bash
python -m app.mcp_server
```

Or with the MCP dev inspector:

```bash
mcp dev app/mcp_server.py
```

## Environment variables

See `.env.example`. Required later:

| Variable | Used in |
|----------|---------|
| `GROQ_API_KEY` | Agent loop (step 4) |
| `WHATSAPP_TOKEN` | WhatsApp send/receive (step 5) |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp send/receive (step 5) |
| `WHATSAPP_VERIFY_TOKEN` | Webhook verification (step 5) |
| `WHATSAPP_APP_SECRET` | Webhook signature validation (step 5) |
| `DATABASE_PATH` | Optional SQLite path override |

## Project layout

```
lead-agent/
├── app/
│   ├── db.py              # SQLite schema + parameterized queries
│   ├── lead_service.py    # Business logic for read (and later write) tools
│   ├── mcp_server.py      # MCP server with tool definitions
│   ├── models.py          # Pydantic models + tool input schemas
│   ├── pending_actions.py # Confirmation flow store (stub for step 3)
│   ├── agent.py           # Groq agent loop (step 4)
│   ├── whatsapp.py        # Meta Cloud API (step 5)
│   └── main.py            # FastAPI app (step 5)
├── scripts/
│   └── test_read_tools.py # Local read-tool smoke test
└── tests/
    └── test_owner_isolation.py
```

## Next steps

3. Write tools + `PendingActionStore` confirmation logic  
4. Groq agent loop with defensive tool-call validation  
5. FastAPI webhook + WhatsApp Cloud API  
6. Deploy to Render
