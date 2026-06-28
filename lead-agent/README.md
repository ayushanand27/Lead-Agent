# LeadAgent — WhatsApp Lead Management Agent (MCP-powered)

[![CI](https://github.com/ayushanand27/mcp-build/actions/workflows/ci.yml/badge.svg)](https://github.com/ayushanand27/mcp-build/actions/workflows/ci.yml)

**AI agent for Indian SMBs to manage sales leads via WhatsApp in plain English/Hindi.**

LeadAgent lets a small business owner text a WhatsApp bot like they'd text an employee — *"which leads haven't I called in 2 days?"*, *"mark Ramesh as converted"*, *"send a follow-up to Priya"* — and get safe, auditable results. A **classic dark admin dashboard** (`/admin`) complements WhatsApp for leads, activity, and CSV export.

Under the hood: a **real MCP server** with typed tools, a **Groq-powered agent loop** that decides which tools to call, and a **FastAPI webhook** wired to Meta's WhatsApp Cloud API. Every write that matters asks for confirmation first. Partners sharing one business see the same lead pool via `BUSINESS_OWNER_PHONES`.

**Live demo:** [lead-agent-to63.onrender.com](https://lead-agent-to63.onrender.com/health) · **Admin:** [/admin](https://lead-agent-to63.onrender.com/admin)

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
                                     │  MCP Tools (×10) │
                                     │  read + write    │
                                     └────────┬─────────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         ▼                    ▼                    ▼
                ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
                │  Supabase        │ │ Google Sheets│ │  Meta WhatsApp   │
                │  Postgres        │ │ (Apps Script)│ │  (outbound msgs) │
                └──────────────────┘ └──────────────┘ └──────────────────┘
```

**Request flow:** WhatsApp message → HMAC-validated webhook → `handle_message()` → Groq selects MCP tools → Postgres read/write → confirmation gate for sends & terminal status changes → reply sent back on WhatsApp.

**Also:** `POST /api/leads` (Zapier/IndiaMART) → DB + optional Sheets sync + owner WhatsApp alert. Admin dashboard edits trigger Sheets upsert by lead `id`. Daily cron sends stale-lead summary to every owner phone.

**Production stack:** Render (app) + Supabase (database) + Meta WhatsApp Cloud API + Groq + cron-job.org (scheduled summary).

---

## Features

- **Plain English/Hindi commands** — owners interact entirely over WhatsApp
- **Admin dashboard** — dark UI at `/admin` (phone + password): stats, lead table, **Edit** (status/notes/tags), search/filter, **Sync all to Google Sheets**, CSV export, activity log, settings
- **Multi-owner** — comma-separated `BUSINESS_OWNER_PHONES` share one lead pool (partners see the same leads)
- **Lead tags** — via WhatsApp, dashboard edit, or webhook payload
- **Google Sheets backup** — upsert by lead `id` (no duplicate rows on re-sync); Apps Script webhook
- **Lead capture webhook** — `POST /api/leads` for website forms, Zapier, IndiaMART (`X-Lead-Webhook-Secret`)
- **Webhook WhatsApp alert** — `NOTIFY_OWNERS_ON_WEBHOOK=true` pings all owners on new lead
- **Daily summary** — cron at 9 AM IST sends stale-lead counts to every owner (`GET` or `POST` + `CRON_SECRET`)
- **10 MCP tools** — 4 read + 6 write (`add_lead_tags` included)
- **Confirmation flow** — destructive actions (send message, mark `converted`/`lost`) require an explicit YES before execution
- **Owner isolation** — each deploy is scoped to registered owner phones; partners in the same business share data
- **Full audit log** — every write recorded in `action_log` with human-readable details
- **Persistent storage** — leads survive redeploys via Supabase Postgres (not ephemeral SQLite)
- **Secure by design** — HMAC webhook validation, bcrypt admin passwords, login rate limit, optional IP allowlist, security headers, parameterized SQL, RLS on database tables

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11 (`runtime.txt`) |
| API / Webhook | FastAPI + Uvicorn |
| Agent protocol | MCP (official Python SDK, FastMCP) |
| LLM | Groq API — `openai/gpt-oss-120b` (OpenAI-compatible tool calling) |
| Messaging | Meta WhatsApp Cloud API |
| Database | **Supabase Postgres** (production) / SQLite (local tests) |
| Rate limiting | slowapi (30 req/min on webhook) |
| CI/CD | GitHub Actions (`.github/workflows/ci.yml`) |
| IaC | `render.yaml` at repo root |
| Hosting | Render.com (free tier) |

---

## Quick start (local)

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

For **local dev**, leave `DATABASE_URL` unset — the app uses SQLite (`leads.db`). Fill in Groq and WhatsApp keys only if testing those integrations.

**Never commit `.env`.**

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
| `GROQ_API_KEY` | Yes (prod) | Groq API key for the agent loop (`openai/gpt-oss-120b`) |
| `WHATSAPP_TOKEN` | Yes (prod) | Meta **System User** permanent token (not 24h API Setup token) |
| `WHATSAPP_PHONE_NUMBER_ID` | Yes (prod) | WhatsApp Business phone number ID from Meta dashboard |
| `WHATSAPP_VERIFY_TOKEN` | Yes (prod) | Arbitrary string for `GET /webhook` subscription verification |
| `WHATSAPP_APP_SECRET` | Yes (prod) | App secret for `X-Hub-Signature-256` HMAC validation |
| `DATABASE_URL` | Production | Supabase Postgres URI — **transaction pooler**, port **6543** |
| `DATABASE_PASSWORD` | Production (recommended) | Database password as plain text — avoids URL-encoding issues on Render |
| `DATABASE_PATH` | Local only | SQLite path when `DATABASE_URL` is unset (default: `leads.db`) |
| `BUSINESS_NAME` | Optional | Display name in agent + dashboard (default: `LeadAgent`) |
| `BUSINESS_INDUSTRY` | Optional | `general`, `real_estate`, `trading`, `coaching` — tweaks system prompt |
| `BUSINESS_OWNER_PHONES` | Optional | Comma-separated owner numbers (digits only). Shared lead pool for all listed partners |
| `ADMIN_DASHBOARD_PASSWORD` | Dashboard | Password for `/admin` login (plain or bcrypt hash — see `scripts/hash_admin_password.py`) |
| `ADMIN_SESSION_SECRET` | Dashboard | Random string for signed session cookies |
| `ADMIN_IP_ALLOWLIST` | Optional | Comma-separated IPs allowed to access `/admin` |
| `LEAD_WEBHOOK_SECRET` | Webhook | Header `X-Lead-Webhook-Secret` for `POST /api/leads` |
| `GOOGLE_SHEETS_WEBHOOK_URL` | Optional | Google Apps Script web app URL for Sheets upsert sync |
| `CRON_SECRET` | Optional | Daily summary — header `X-Cron-Secret` or query `?secret=` |
| `STALE_LEAD_DAYS` | Optional | Days without contact before "stale" (default: `2`) |
| `NOTIFY_OWNERS_ON_WEBHOOK` | Optional | WhatsApp alert owners on `POST /api/leads` (default: `true`) |
| `SENTRY_DSN` | Optional | Error monitoring (Sentry) |

### Render database setup (recommended)

Use **two** env vars on Render so passwords with `@`, `#`, or spaces work without encoding:

```bash
# No password in this URL — user only, host, port, dbname
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF@aws-1-REGION.pooler.supabase.com:6543/postgres?sslmode=require

# Plain password — special characters OK
DATABASE_PASSWORD=your-database-password
```

**Alternative:** single `DATABASE_URL` with URL-encoded password (`@` → `%40`, `#` → `%23`, space → `%20`).

---

## Production deployment

**Step-by-step guide:** **[DEPLOY.md](DEPLOY.md)** — Supabase, Render, Meta webhook, and keep-alive.  
**Client handover ($1000 tier):** **[docs/CLIENT_SETUP.md](docs/CLIENT_SETUP.md)** — bcrypt, Google Sheets, lead webhook, cron.  
**Command guide:** **[docs/CLIENT_GUIDE.md](docs/CLIENT_GUIDE.md)** · **IndiaMART/Zapier:** **[docs/ZAPIER_INDIA_MART.md](docs/ZAPIER_INDIA_MART.md)**

### Summary

| Step | Platform | What to do |
|------|----------|------------|
| 1 | **Supabase** | Create project → run `migrations/001_leads_schema.sql` → copy pooler connection string |
| 2 | **Render** | Set env vars (`DATABASE_URL` + `DATABASE_PASSWORD`, Groq, WhatsApp) → deploy from `lead-agent/` root |
| 3 | **Meta** | Webhook URL `https://<app>.onrender.com/webhook` → subscribe `messages` → add **all owner phones** to test recipient list (up to 5) → System User token |
| 4 | **cron-job.org** | Daily 9 AM IST summary — see [DEPLOY.md §5](DEPLOY.md#5-admin-dashboard--daily-cron) |
| 5 | **UptimeRobot** (optional) | Ping `/health` every 5 min to reduce Render free-tier cold starts |

### Render settings

| Setting | Value |
|---------|--------|
| Root directory | `lead-agent` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Python version | `3.11.11` (via `runtime.txt`) |

### Verify deployment

```bash
curl https://lead-agent-to63.onrender.com/health
# {"status":"ok","timestamp":...,"database":"connected","cron_configured":true}

curl https://lead-agent-to63.onrender.com/health/ready
# {"status":"ready","database":"connected"}

curl https://lead-agent-to63.onrender.com/api/leads/health
# {"webhook_configured":true,...}
```

WhatsApp test: message the Meta test number → `Add lead Ramesh phone 9876543210 from Surat` → check row in Supabase **Table Editor** → `leads`.

### Keep-alive (Render free tier)

Use [UptimeRobot](https://uptimerobot.com) to ping every **5 minutes**:

```
https://lead-agent-to63.onrender.com/health
```

---

## HTTP API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | **Liveness** — includes `database` and `cron_configured` |
| `/health/ready` | GET | **Readiness** — 503 if database unreachable |
| `/webhook` | GET | Meta webhook verification challenge |
| `/webhook` | POST | Inbound WhatsApp messages (HMAC-validated; acks immediately, processes in background) |
| `/api/leads` | POST | Lead capture from website/Zapier/IndiaMART (`X-Lead-Webhook-Secret`) |
| `/api/leads/health` | GET | Webhook integration status |
| `/admin` | GET | Owner dashboard (session login) |
| `/admin/login` | GET/POST | Dashboard login (phone + `ADMIN_DASHBOARD_PASSWORD`) |
| `/admin/leads` | GET | Lead list, search, filter |
| `/admin/leads/{id}/edit` | GET/POST | Edit status, notes, tags (+ Sheets sync) |
| `/admin/leads/sync-sheets` | POST | Backfill all leads to Google Sheets |
| `/admin/leads/export` | GET | CSV download |
| `/admin/activity` | GET | Audit log |
| `/internal/cron/daily-summary` | GET, POST | Cron-triggered WhatsApp summary (`X-Cron-Secret` or `?secret=`) |

Set `LOG_LEVEL=DEBUG` for verbose server logs.

---

## CI/CD

Tests run automatically on every push to `main` via GitHub Actions:

- `test_read_tools.py`, `test_write_tools.py`, `test_webhook.py`
- `pytest tests/` (owner isolation)
- `test_agent.py` (optional — requires `GROQ_API_KEY` repo secret)

Run locally:

```bash
cd lead-agent
python scripts/test_read_tools.py
python scripts/test_write_tools.py
python scripts/test_webhook.py
pytest tests/ -v
```

---

## Industry standards implemented

| Practice | Implementation |
|----------|----------------|
| Stateless app + managed DB | Render + Supabase Postgres |
| Secrets via env vars | Never committed; `DATABASE_PASSWORD` for special chars |
| Webhook HMAC validation | `X-Hub-Signature-256` |
| Fast webhook ack | `BackgroundTasks` — 200 to Meta before agent loop |
| Health / readiness probes | `/health` + `/health/ready` |
| Infrastructure as code | `render.yaml` |
| Automated testing | GitHub Actions CI |
| Multi-tenant isolation | `owner_phone` on every query |
| Human-in-the-loop | Confirmation before send / terminal status |
| Audit logging | `action_log` table |
| RLS on database | Supabase `leads` + `action_log` |
| Parameterized SQL | No string-interpolated queries |
| Pinned Python runtime | `runtime.txt` → 3.11.11 |

**Known v1 limitations (acceptable for portfolio / test sandbox):**
- Meta **test number** only — messages deliver to **verified recipient list** (max 5 numbers); not production WABA
- No Redis / job queue (single Render instance)
- Sentry optional — not required for demo
- Render free tier cold starts (~15–30s wake) unless UptimeRobot ping or Starter plan

**Verified live (June 2026):** multi-owner cron summary, dashboard edit + Sheets upsert, webhook alerts, cron-job.org daily job at 9 AM IST.

---

## Example WhatsApp commands

| Owner sends | Agent does |
|-------------|------------|
| `list all my leads` | Returns a numbered list of leads with status |
| `which leads haven't been contacted in 2 days?` | Calls `get_stale_leads` (excludes converted/lost) |
| `mark Ramesh as converted` | Queues status update → asks YES → updates on confirm |
| `send a follow up to Priya` | Drafts message → shows preview → sends only after YES |
| `add note to Amit: called twice, no answer` | Appends timestamped note to Amit's lead |
| `tag Priya as hot and referral` | Adds comma-separated tags via `add_lead_tags` |

Hindi works too — the agent replies in the same language the owner uses.

---

## Security

| Control | Implementation |
|---------|----------------|
| **Owner isolation** | Every `leads` / `action_log` query uses `WHERE owner_phone = ?`; lead writes use `WHERE id = ? AND owner_phone = ?` |
| **Webhook authenticity** | `X-Hub-Signature-256` verified with `hmac.compare_digest` + `WHATSAPP_APP_SECRET` |
| **Confirmation gate** | `send_whatsapp_message` and terminal status changes stored in `PendingActionStore` until owner confirms |
| **Audit trail** | `action_log` records every write (`lead_created`, `status_updated`, `note_added`, `message_sent`) |
| **Database RLS** | Row Level Security enabled on Supabase tables; no public API policies |
| **Safe errors** | Generic messages to owners; details logged server-side only |
| **SQL injection** | Parameterized queries only — no string-interpolated SQL |
| **Rate limiting** | 30 requests/minute per IP on `POST /webhook`; admin login rate limit |
| **Admin hardening** | bcrypt passwords, optional IP allowlist, security headers, login audit |

Run isolation tests anytime:

```bash
pytest tests/test_owner_isolation.py -v
```

---

## Project structure

```
lead-agent/
├── app/
│   ├── main.py            # FastAPI webhook, health, cron routes
│   ├── api/leads.py       # POST /api/leads webhook
│   ├── agent.py           # Groq agent loop + confirmation flow
│   ├── mcp_server.py      # MCP server (10 tools)
│   ├── lead_service.py    # Business logic layer
│   ├── db.py              # Postgres (Supabase) + SQLite queries
│   ├── models.py          # Pydantic models + tool schemas
│   ├── pending_actions.py # DB-backed confirmation store
│   ├── config.py          # Business name, industry, multi-owner scope
│   ├── summary.py         # Daily WhatsApp summary
│   ├── notifications.py   # Owner alerts on webhook leads
│   ├── integrations/sheets.py  # Google Sheets upsert sync
│   ├── admin/             # Dashboard routes + session auth
│   ├── security/          # bcrypt, rate limit, headers
│   ├── static/admin.css   # Dark dashboard theme
│   ├── templates/admin/   # Jinja2 HTML (leads, lead_edit, …)
│   └── whatsapp.py        # Meta Cloud API helpers
├── docs/
│   ├── CLIENT_SETUP.md    # $1000 tier handover (Sheets, cron, webhook)
│   ├── CLIENT_GUIDE.md    # WhatsApp command cheat sheet
│   └── ZAPIER_INDIA_MART.md
├── scripts/
│   ├── test_read_tools.py
│   ├── test_write_tools.py
│   ├── test_agent.py
│   ├── test_webhook.py
│   ├── hash_admin_password.py
│   └── check_meta_webhook.py
├── tests/                 # pytest (isolation, security, sheets, multi-owner)
├── migrations/
│   ├── 001_leads_schema.sql
│   ├── 002_pending_actions.sql
│   ├── 003_lead_consent.sql
│   └── 004_lead_tags.sql
├── DEPLOY.md              # Meta + Supabase + Render + cron guide
├── runtime.txt            # Python 3.11 for Render
├── requirements.txt
└── .env.example
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Render deploy fails on startup | Bad `DATABASE_URL` | Use `DATABASE_URL` (no password) + `DATABASE_PASSWORD` separately |
| `password authentication failed` | `@` in password broke URL | Use separate `DATABASE_PASSWORD` or URL-encode password |
| No WhatsApp reply | Render asleep (free tier) | Ping `/health`, wait 30s, message again |
| No WhatsApp reply | Webhook not subscribed | Meta → WhatsApp → Configuration → subscribe `messages` |
| Leads gone after redeploy | SQLite on Render (old setup) | Set `DATABASE_URL` to Supabase |
| OAuth error 190 | Expired WhatsApp token | Regenerate System User token on Meta |
| Cron returns 403 | `CRON_SECRET` missing or mismatch | Set on Render → Save & redeploy; check `/health` → `cron_configured: true` |
| Cron `failed: 1` | Second owner not in Meta recipient list | Meta → API Setup → Manage phone number list → verify all `BUSINESS_OWNER_PHONES` |
| Sheets duplicate rows | Old rows before upsert script | Delete duplicates manually; header must be `tags` not `tag`; redeploy Apps Script |
| Edit button missing | Old Render deploy | Manual Deploy → hard refresh `/admin/leads` |

---

## Test results

All local test suites passing:

| Suite | Command | Status |
|-------|---------|--------|
| Read tools | `python scripts/test_read_tools.py` | Pass |
| Write tools | `python scripts/test_write_tools.py` | Pass |
| Agent loop | `python scripts/test_agent.py` | Pass |
| Webhook | `python scripts/test_webhook.py` | Pass |
| Owner isolation | `pytest tests/test_owner_isolation.py -v` | 3 pass |
| Security + webhook | `pytest tests/test_security.py -v` | 5 pass |
| Multi-owner + tags | `pytest tests/test_multi_owner.py -v` | 2 pass |
| Sheets sync | `pytest tests/test_sheets_sync.py -v` | 2 pass |
| **Total pytest** | `pytest tests/ -v` | **12 pass** |

---

## License

MIT
