# mcp-build

**LeadAgent** — WhatsApp Lead Management Agent powered by MCP, Groq, and Supabase.

[![CI](https://github.com/ayushanand27/mcp-build/actions/workflows/ci.yml/badge.svg)](https://github.com/ayushanand27/mcp-build/actions/workflows/ci.yml)

Indian SMB owners manage sales leads over WhatsApp in plain English or Hindi — no app, no dashboard, no login. Text the bot like you'd text an employee; a real MCP tool server and Groq agent handle the rest safely.

**Live:** [lead-agent-to63.onrender.com/health](https://lead-agent-to63.onrender.com/health)  
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

---

## Architecture

```
WhatsApp  →  Render (FastAPI)  →  Groq agent  →  MCP tools (×9)  →  Supabase Postgres
                ↑ webhook
           Meta Cloud API
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
| CI | GitHub Actions |

---

## Status

| Milestone | Status |
|-----------|--------|
| MCP read/write tools (9) | ✅ |
| Groq agent + confirmation flow | ✅ |
| WhatsApp webhook + HMAC validation | ✅ |
| Supabase Postgres (persistent storage) | ✅ |
| Deployed on Render | ✅ |
| GitHub Actions CI | ✅ |
| Meta test sandbox (WhatsApp) | ✅ |

---

## License

MIT
