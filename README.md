# mcp-build

**LeadAgent** — WhatsApp Lead Management Agent powered by MCP, Groq, and Supabase.

[![CI](https://github.com/ayushanand27/mcp-build/actions/workflows/ci.yml/badge.svg)](https://github.com/ayushanand27/mcp-build/actions/workflows/ci.yml)

Indian SMB owners manage sales leads over WhatsApp in plain English or Hindi. Text the bot like you'd text an employee; a real MCP tool server and Groq agent handle the rest safely. A dark admin dashboard at `/admin` complements WhatsApp for leads, edits, Sheets sync, and export.

**Live:** [lead-agent-to63.onrender.com](https://lead-agent-to63.onrender.com/health)  
**Admin:** [lead-agent-to63.onrender.com/admin](https://lead-agent-to63.onrender.com/admin)  
**Repo:** [github.com/ayushanand27/mcp-build](https://github.com/ayushanand27/mcp-build)

---

## What's in this repo

| Path | Description |
|------|-------------|
| [`lead-agent/`](lead-agent/) | **Main application** — FastAPI webhook, Groq agent, MCP tools, Supabase Postgres |
| [`render.yaml`](render.yaml) | Render.com infrastructure-as-code |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions — tests on every push |

All application code, tests, migrations, and **full documentation** live in **`lead-agent/`**.

**→ [Read the complete documentation](lead-agent/README.md)** (architecture, setup, deployment, API, security)

**Client handover:** [docs/CLIENT_SETUP.md](lead-agent/docs/CLIENT_SETUP.md) · [docs/CLIENT_GUIDE.md](lead-agent/docs/CLIENT_GUIDE.md) · [docs/ZAPIER_INDIA_MART.md](lead-agent/docs/ZAPIER_INDIA_MART.md)

---

## Architecture

```
WhatsApp / Webhook  →  Render (FastAPI)  →  Groq agent  →  MCP tools (×10)  →  Supabase Postgres
        ↑                      │                                    │
   Meta Cloud API         /admin dashboard                    Google Sheets
   cron-job.org           lead webhook API                     (Apps Script)
```

---

## Quick start

```bash
git clone https://github.com/ayushanand27/mcp-build.git
cd mcp-build/lead-agent
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
python scripts/test_read_tools.py
uvicorn app.main:app --reload --port 8000
```

---

## Production stack

| Layer | Technology |
|-------|------------|
| API | FastAPI + Uvicorn (Python 3.11) |
| Agent | Groq `openai/gpt-oss-120b` + MCP (official SDK) |
| Messaging | Meta WhatsApp Cloud API |
| Database | Supabase Postgres (persistent) |
| Hosting | Render.com (free tier) |
| Cron | [cron-job.org](https://cron-job.org) (free daily summary) |
| CI | GitHub Actions |

---

## Status (live demo — June 2026)

| Feature | Status |
|---------|--------|
| MCP read/write tools (10) | ✅ |
| Groq agent + confirmation flow | ✅ |
| WhatsApp webhook + HMAC validation | ✅ |
| Multi-owner shared lead pool | ✅ |
| Admin dashboard (edit, tags, CSV, activity) | ✅ |
| Google Sheets upsert sync | ✅ |
| Lead capture webhook (`POST /api/leads`) | ✅ |
| WhatsApp alert on new webhook lead | ✅ |
| Daily summary cron (9 AM IST) | ✅ |
| Supabase Postgres | ✅ |
| Deployed on Render | ✅ |
| Meta test sandbox (up to 5 recipients) | ✅ |
| GitHub Actions CI (12 tests) | ✅ |

---

## License

MIT
