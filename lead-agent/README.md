# LeadAgent — WhatsApp Lead Management Agent

[![CI](https://github.com/ayushanand27/Lead-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/ayushanand27/Lead-Agent/actions/workflows/ci.yml)

**Most Indian SMBs lose WhatsApp leads because follow-up is manual — notes in chat, Excel at midnight, no one knows who's stale.**

LeadAgent fixes that. Your sales team texts a WhatsApp bot in **plain Hindi or English** like they'd text an employee. It lists leads, flags who you haven't called, drafts follow-ups, and asks **YES** before anything goes to a customer. New leads from your website or IndiaMART ping the team instantly. Every morning: a summary of who needs attention. Google Sheets stays in sync. Two partners can share the same lead pool.

**Live demo:** [Admin portal](https://lead-agent-to63.onrender.com/admin/login) · **API health:** [/health](https://lead-agent-to63.onrender.com/health)

---

## Screenshots

| Dashboard | Leads + Edit | WhatsApp | Live deployment |
|:---:|:---:|:---:|:---:|
| ![Dashboard](../docs/screenshots/admin-dashboard.png) | ![Leads](../docs/screenshots/admin-leads.png) | ![WhatsApp](../docs/screenshots/whatsapp-flow.png) | [![Health](../docs/screenshots/health-check.png)](https://lead-agent-to63.onrender.com/health) |

**Links:** [admin login](https://lead-agent-to63.onrender.com/admin/login) · [health JSON](https://lead-agent-to63.onrender.com/health)

---

## Real estate example (Surat)

| Step | What happens |
|------|----------------|
| 1 | IndiaMART lead → Zapier → LeadAgent → **WhatsApp:** *"New lead: Ramesh, 98765…, 2BHK Surat"* |
| 2 | Agent: *"Surat ke stale leads dikhao"* |
| 3 | Bot lists leads with status + days since contact |
| 4 | *"Ramesh ko follow-up draft karo"* → preview → **YES** → ready to send |
| 5 | 9 AM cron → both owners get stale-lead count |
| 6 | Dashboard `/admin` → edit status, tags, export CSV, Sheets sync |

Set `BUSINESS_INDUSTRY=real_estate` for property-focused prompts. Same flow works for coaching, trading, general SMB.

---

## For developers

LeadAgent is an MCP-powered agent: a **real MCP server** with typed tools, a **Groq** loop (`openai/gpt-oss-120b`), and a **FastAPI** webhook on Meta WhatsApp Cloud API. Confirmation gate on destructive actions. Multi-owner scope via `BUSINESS_OWNER_PHONES`.

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
                                     │  MCP Tools (×11) │
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

### Webhooks vs WhatsApp chat (common confusion)

| Endpoint | Who calls it | Purpose |
|----------|----------------|---------|
| `GET/POST /webhook` | **Meta** (WhatsApp Cloud API) | Owner messages to the bot; bot replies on WhatsApp. Requires `WHATSAPP_APP_SECRET` + valid token. |
| `POST /api/leads` | **Your site / Zapier / IndiaMART** | New lead capture from forms (header `X-Lead-Webhook-Secret`). Not used for owner chat commands. |
| `GET/POST /internal/cron/daily-summary` | **cron-job.org** (or you) | Morning stale-lead summary (`CRON_SECRET`). |

If the bot **replies** in WhatsApp but behaves oddly (e.g. treats a phone number as search), the Meta webhook is fine — the issue is usually **agent fast paths** or **multi-turn context**, not a broken webhook.

### How owner messages are handled

1. **Fast paths (no Groq)** — reliable demo commands: `list all leads`, `search Priya`, `add lead X phone 99… from website`, `add lead X 99… from source`, `mark X as warm`, stale queries, etc.
2. **Multi-turn add lead** — e.g. `add lead aryan from muj without phone` → bot asks for digits → you send `89076968382` → lead is created (stored in `pending_actions` as a draft, not a YES/NO confirmation).
3. **Groq agent loop** — everything else; may ask clarifying questions but has no memory unless you use the draft phrases above.
4. **YES confirmation** — send message to customer, delete lead, mark converted/lost.

**Also:** `POST /api/leads` (Zapier/IndiaMART) → DB + optional Sheets sync + owner WhatsApp alert. Admin dashboard edits trigger Sheets upsert by lead `id`. Daily cron sends stale-lead summary to every owner phone.

**Production stack:** Render (app) + Supabase (database) + Meta WhatsApp Cloud API + Groq + cron-job.org (scheduled summary).

---

## Features

- **Plain English/Hindi commands** — owners interact entirely over WhatsApp
- **Admin dashboard** — dark UI at `/admin` (phone + password): stats, lead table, **Edit** (status/notes/tags), **Delete** (with confirm), search/filter, **Sync all to Google Sheets**, CSV export, activity log, settings
- **Multi-owner** — comma-separated `BUSINESS_OWNER_PHONES` share one lead pool (partners see the same leads)
- **Lead tags** — via WhatsApp, dashboard edit, or webhook payload
- **Google Sheets backup** — upsert by lead `id` (no duplicate rows on re-sync); Apps Script webhook
- **Lead capture webhook** — `POST /api/leads` for website forms, Zapier, IndiaMART (`X-Lead-Webhook-Secret`)
- **Webhook WhatsApp alert** — `NOTIFY_OWNERS_ON_WEBHOOK=true` pings all owners on new lead
- **Daily summary** — cron at 9 AM IST sends stale-lead counts to every owner (`GET` or `POST` + `CRON_SECRET`)
- **11 MCP tools** — 4 read + 7 write (`add_lead_tags`, `delete_lead` included)
- **Voice notes** — WhatsApp voice → text, optionally via Sarvam AI (Indian languages/accents) with automatic fallback to Groq Whisper
- **Confirmation flow** — destructive actions (send message, mark `converted`/`lost`, delete a lead) require an explicit YES before execution
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
| Hosting | Render.com |

---

## Quick start (local)

### 1. Clone and install

```bash
git clone https://github.com/ayushanand27/Lead-Agent.git
cd Lead-Agent/lead-agent

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Prefer a reproducible install matching the exact versions this repo is tested against? Use `pip install -r requirements-lock.txt` instead — `requirements.txt` only pins floor versions, so a fresh install months from now can otherwise resolve different (and untested) transitive dependency versions.

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
| `GROQ_API_KEY` | Yes (prod) | Groq API key for the agent loop (`openai/gpt-oss-120b`) and Whisper voice transcription |
| `SARVAM_API_KEY` | Optional | Sarvam AI speech-to-text — tried before Groq Whisper on voice notes, better accuracy for Indian languages/accents beyond Hindi (Tamil, Telugu, Bengali, Marathi, Kannada, etc.). Falls back to Whisper automatically if unset or if the call fails |
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
| `ENVIRONMENT` | Optional | Set to `production` to force HTTPS-only cookies + startup security warnings on non-Render hosts (Render sets its own `RENDER=true`, which already triggers this) |

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
**Client handover:** **[docs/CLIENT_SETUP.md](docs/CLIENT_SETUP.md)** — deploy, Sheets, webhook, cron, production WABA checklist.  
**Command guide:** **[docs/CLIENT_GUIDE.md](docs/CLIENT_GUIDE.md)** · **IndiaMART/Zapier:** **[docs/ZAPIER_INDIA_MART.md](docs/ZAPIER_INDIA_MART.md)**

**Demo hosting:** free Render + UptimeRobot ping on `/health` is enough for portfolio. Charge clients for Render Starter when they pay you.

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

### Keep-alive (free demo)

Ping every **5 minutes** so WhatsApp replies stay fast:

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
| `/admin/leads/{id}/delete` | POST | Permanently delete a lead (JS confirm + CSRF token) |
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
| RLS on database | Enabled on `leads` + `action_log`, but no policies defined — it's a fail-closed backstop if the anon key ever leaks, not the isolation mechanism. Real tenant isolation is enforced in application code (`owner_phone` scoping, see `Multi-tenant isolation` above) |
| Parameterized SQL | No string-interpolated queries |
| Pinned Python runtime | `runtime.txt` → 3.11.11 |

**Known limitations (demo vs paid client):**
- Meta **test number** — production WABA + Business Verification required for real customers (see [DEPLOY.md §7](DEPLOY.md#7-going-to-real-production-later))
- No broadcast campaigns or template blasts (not a WATI clone)
- Sentry optional
- `ADMIN_DASHBOARD_PASSWORD` still accepts a legacy plain-text value in addition to a bcrypt hash for backward compatibility — the app now logs a startup warning when it's plain text; run `scripts/hash_admin_password.py` and use the hash for any paid deploy
- CSRF tokens cover the authenticated dashboard forms (edit lead, delete lead, sync-to-sheets, logout); the pre-login form doesn't carry one, since there's no session yet to forge

**Verified 12 Aug 2026:** full suite run clean — `pytest tests/` (63/63), `test_read_tools.py`, `test_write_tools.py`, `test_webhook.py` (7/7 incl. HMAC + admin login flow), and `test_agent.py` against the live Groq API (5/5, real tool-calling + confirmation flow). Plus the always-on GitHub Actions CI on every push to `main`.

**Fixed 11 Aug 2026** (previously listed here as gaps): `POST /api/leads` is now rate-limited the same as the WhatsApp webhook (30/min/IP); dependency versions are now locked (see `requirements-lock.txt`) so a fresh install reproduces the exact tested environment instead of "whatever's newest today"; admin dashboard forms now carry session-bound CSRF tokens.

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
| `delete Ramesh` / `Ramesh ko hata do` | Finds the lead → asks YES → permanently deletes on confirm |

Hindi works too — the agent replies in the same language the owner uses.

---

## Security

| Control | Implementation |
|---------|----------------|
| **Owner isolation** | Every `leads` / `action_log` query uses `WHERE owner_phone = ?`; lead writes use `WHERE id = ? AND owner_phone = ?` |
| **Webhook authenticity** | `X-Hub-Signature-256` verified with `hmac.compare_digest` + `WHATSAPP_APP_SECRET` |
| **Confirmation gate** | `send_whatsapp_message`, terminal status changes, and `delete_lead` stored in `PendingActionStore` until owner confirms |
| **Audit trail** | `action_log` records every write (`lead_created`, `status_updated`, `note_added`, `message_sent`) |
| **Database RLS** | Enabled on Supabase tables as a fail-closed backstop (no policies defined); not the primary isolation mechanism — see Owner isolation above |
| **Safe errors** | Generic messages to owners; details logged server-side only |
| **SQL injection** | Parameterized queries only — no string-interpolated SQL |
| **Rate limiting** | 30 requests/minute per IP on both `POST /webhook` and `POST /api/leads` (shared `slowapi` limiter, see `app/security/limiter.py`); admin login capped at 5 attempts/15 min per IP. All counters are in-memory (single-instance only) |
| **Admin hardening** | bcrypt passwords supported (`scripts/hash_admin_password.py`) — legacy plain-text `ADMIN_DASHBOARD_PASSWORD` is still accepted for backward compatibility, but now logs a startup warning; optional IP allowlist, security headers, login audit |
| **CSRF** | Session-bound tokens (`app/security/csrf.py`) on authenticated dashboard forms — edit lead, delete lead, sync-to-sheets, logout. The pre-login form is intentionally excluded: no session exists yet to forge, and it's already behind IP allowlist + rate-limited lockout |

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
│   ├── CLIENT_SETUP.md    # Client deploy handover (Sheets, cron, webhook)
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
| No WhatsApp reply | Service waking / webhook | Ping `/health`, wait 30s; add UptimeRobot 5-min ping |
| No WhatsApp reply | Webhook not subscribed | Meta → WhatsApp → Configuration → subscribe `messages` |
| Leads gone after redeploy | SQLite on Render (old setup) | Set `DATABASE_URL` to Supabase |
| OAuth error 190 | Expired WhatsApp token | Regenerate System User token on Meta |
| Cron returns 403 | `CRON_SECRET` missing or mismatch | Set on Render → Save & redeploy; check `/health` → `cron_configured: true` |
| Cron `failed: 1` | Second owner not in Meta recipient list | Meta → API Setup → Manage phone number list → verify all `BUSINESS_OWNER_PHONES` |
| Sheets duplicate rows | Old rows before upsert script | Delete duplicates manually; header must be `tags` not `tag`; redeploy Apps Script |
| Edit button missing | Old Render deploy | Manual Deploy → hard refresh `/admin/leads` |

---

## Test results

```bash
cd lead-agent && pytest tests/ -v
```

Covers owner isolation, admin security, multi-owner pool, Sheets sync serialization.

**Last full run — 11 Aug 2026, all green:**

| Suite | Result |
|-------|--------|
| `pytest tests/` | 63/63 passed (incl. `test_csrf.py` — dashboard edit/delete/logout — `delete_lead` isolation, `test_media.py` Sarvam fallback) |
| `scripts/test_read_tools.py` | passed |
| `scripts/test_write_tools.py` | passed (incl. cross-owner write isolation, `delete_lead`) |
| `scripts/test_webhook.py` | 7/7 passed (signature validation, admin login, health checks) |
| `scripts/test_agent.py` | 5/5 passed against the live Groq API (tool-calling + confirmation flow) |

Run everything with your own virtualenv activated (`.venv\Scripts\activate` on Windows) — a stray global Python install with unrelated packages on `PATH` can resolve incompatible transitive dependency versions and produce false failures that don't reflect this repo's actual state.

---

## License

**Proprietary — all rights reserved.** See [LICENSE](../LICENSE).

Unauthorized copying, redistribution, or commercial use without written permission is prohibited.
