# LeadAgent — Production deployment guide

Step-by-step setup for **Meta (WhatsApp)**, **Supabase (Postgres)**, and **Render (hosting)**.

---

## Architecture (production)

```
WhatsApp  →  Render (FastAPI)  →  Groq (agent)  →  Supabase Postgres (leads)
              ↑ webhook URL
         Meta Cloud API
```

---

## 1. Supabase (database — persistent storage)

### 1.1 Create or restore project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard)
2. **New project** (or **Restore** if paused — free tier pauses after inactivity)
   - Name: `leadagent` (or any name)
   - Region: **Mumbai (ap-south-1)** or closest to India
   - Set a strong **database password** — save it somewhere safe

### 1.2 Run the schema migration

**Option A — SQL Editor (easiest)**

1. Project → **SQL Editor** → **New query**
2. Paste contents of `migrations/001_leads_schema.sql`
3. Click **Run**

**Option B — Supabase CLI**

```bash
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

### 1.3 Get `DATABASE_URL` for Render

1. Project → **Settings** → **Database**
2. Under **Connection string**, choose **URI**
3. Select **Transaction pooler** (port **6543**) — best for Render serverless/free tier
4. Copy the URI. It looks like:

```
postgresql://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

5. Replace `[YOUR_PASSWORD]` with your database password
6. Ensure the URL ends with `?sslmode=require` if not already present

**Important:** Use the **database password**, not the Supabase API keys. Never commit this URL to git.

### 1.4 Security (already in migration)

- Row Level Security (RLS) is **enabled** on `leads` and `action_log`
- No public policies — data is only reachable via your app’s `DATABASE_URL` (postgres role)
- Do **not** expose `service_role` or `DATABASE_URL` in frontend code

### 1.5 Verify tables

SQL Editor:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ('leads', 'action_log');
```

You should see both tables.

---

## 2. Render (hosting)

### 2.1 Environment variables

In [Render Dashboard](https://dashboard.render.com) → your **lead-agent** service → **Environment**:

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | Supabase Postgres URI (transaction pooler, port 6543) — password optional if using `DATABASE_PASSWORD` |
| `DATABASE_PASSWORD` | **Recommended on Render** — plain database password (handles `@`, `#`, spaces) |
| `GROQ_API_KEY` | Your Groq API key |
| `WHATSAPP_TOKEN` | Meta **System User** permanent token |
| `WHATSAPP_PHONE_NUMBER_ID` | e.g. `1144225728778614` |
| `WHATSAPP_VERIFY_TOKEN` | e.g. `leadagent_verify_2026` |
| `WHATSAPP_APP_SECRET` | From Meta App → Settings → Basic |

**Remove** `DATABASE_PATH` from Render (or leave unset) — production uses Postgres only.

**Recommended — two env vars (passwords with `@` or special chars):**

```bash
DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF@aws-1-REGION.pooler.supabase.com:6543/postgres?sslmode=require
DATABASE_PASSWORD=your-plain-database-password
```

Do **not** put the password inside `DATABASE_URL` when using `DATABASE_PASSWORD`.

### 2.2 Deploy settings

| Setting | Value |
|---------|--------|
| Root directory | `lead-agent` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

### 2.3 Redeploy

After adding `DATABASE_URL`, click **Manual Deploy** → **Deploy latest commit**.

On startup, `init_db()` creates tables if missing (safe to run twice).

### 2.4 Keep service warm (free tier)

Render free tier sleeps after ~15 min idle. Meta webhooks can fail during cold start.

**Free fix:** [UptimeRobot](https://uptimerobot.com) or [cron-job.org](https://cron-job.org)

- URL: `https://lead-agent-to63.onrender.com/health`
- Interval: every **5 minutes**

### 2.5 Verify

```bash
curl https://lead-agent-to63.onrender.com/health
# {"status":"ok","timestamp":...}
```

---

## 3. Meta / WhatsApp (one-time checklist)

### 3.1 Developer Console

[developers.facebook.com](https://developers.facebook.com) → **LeadAgent** app

| Step | Location | Action |
|------|----------|--------|
| Webhook URL | WhatsApp → **Configuration** | `https://lead-agent-to63.onrender.com/webhook` |
| Verify token | Same page | Must match `WHATSAPP_VERIFY_TOKEN` on Render |
| Subscribe | Same page | **messages** field = Subscribed ✓ |
| Test number | WhatsApp → **API Setup** | Message **+1 555-195-9098** |
| Recipients | API Setup | Your phone `917073245149` in recipient list |

### 3.2 Permanent token (System User)

1. [business.facebook.com](https://business.facebook.com) → **Business Settings**
2. **Users** → **System Users** → create or select user
3. **Generate token** for your LeadAgent app
4. Permissions: `whatsapp_business_messaging`, `whatsapp_business_management`
5. Copy token → Render `WHATSAPP_TOKEN`

Tokens from API Setup page expire in ~24h — **always use System User token** for production.

### 3.3 App subscribed to WhatsApp Business Account

Your app must be subscribed to receive webhooks. Verify via Graph API:

```bash
curl "https://graph.facebook.com/v19.0/1682424813032373/subscribed_apps" \
  -H "Authorization: Bearer YOUR_WHATSAPP_TOKEN"
```

Response should include your app **LeadAgent** (`2108222013057101`).

If missing, subscribe:

```bash
curl -X POST "https://graph.facebook.com/v19.0/1682424813032373/subscribed_apps" \
  -H "Authorization: Bearer YOUR_WHATSAPP_TOKEN"
```

Or run: `python scripts/check_meta_webhook.py` (with `RENDER_API_KEY` set).

### 3.4 Test end-to-end

1. Ping `/health` (wake Render)
2. From whitelisted phone, WhatsApp **+1 555-195-9098**:
   - `Add lead Ramesh Kumar phone 9876543210 from Surat`
   - `List all my leads`
3. Check Supabase **Table Editor** → `leads` — row should appear
4. Redeploy Render — message again — leads should **still be there** (persistent)

---

## 4. Local development

| Mode | Config |
|------|--------|
| SQLite (default) | Leave `DATABASE_URL` unset, use `DATABASE_PATH=leads.db` |
| Supabase locally | Set `DATABASE_URL` in `.env` (same as Render) |

```bash
cd lead-agent
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

---

## 5. Admin dashboard (free tier)

After deploy, set these on **Render → Environment**:

| Variable | Example |
|----------|---------|
| `ADMIN_DASHBOARD_PASSWORD` | Strong password you share with the client |
| `ADMIN_SESSION_SECRET` | Random 32+ char string |
| `BUSINESS_NAME` | `Sharma Realty` |
| `BUSINESS_OWNER_PHONES` | `917073245149` (your WhatsApp, digits only) |

Open: `https://lead-agent-to63.onrender.com/admin`

Login with **owner phone** + **dashboard password**. UI is dark zinc (industry-standard admin look) — no paid UI library.

**Daily summary (optional, free):** set `CRON_SECRET`, then on [cron-job.org](https://cron-job.org) create a daily job:

```
POST https://lead-agent-to63.onrender.com/internal/cron/daily-summary
Header: X-Cron-Secret: <your CRON_SECRET>
```

---

## 6. Render Starter (client production — no cold start)

When a client pays, upgrade from **Free** to **Starter** (~$7/mo):

1. Render dashboard → your service → **Settings → Instance Type → Starter**
2. Keep same env vars — no code change
3. Optional: remove UptimeRobot ping (not needed on Starter)
4. Set `ENVIRONMENT=production` and `SENTRY_DSN` if using monitoring

**Client handover checklist:**
- [ ] Real WABA number on Meta
- [ ] Render Starter + custom domain (optional)
- [ ] `ADMIN_DASHBOARD_PASSWORD` as bcrypt hash
- [ ] Google Sheets upsert script (CLIENT_SETUP.md §3)
- [ ] Zapier/IndiaMART webhook (docs/ZAPIER_INDIA_MART.md)
- [ ] Give client docs/CLIENT_GUIDE.md

---

## 7. Going to real production (later)

Test number `+1 555…` is for development only. For real Indian SMB customers:

1. Register a real WhatsApp Business phone number
2. Complete Meta **Business Verification**
3. Submit app for **App Review** (`whatsapp_business_messaging`)
4. Consider Render **Starter** plan (no cold start) or always-on ping

---

## Quick troubleshooting

| Symptom | Fix |
|---------|-----|
| No WhatsApp reply | Wake Render (`/health`); check Meta webhook subscribed; check `WHATSAPP_TOKEN` not expired |
| "No leads" after redeploy | Add `DATABASE_URL` on Render pointing to Supabase |
| `connection refused` to DB | Restore Supabase project if paused; use pooler URL port 6543 |
| Webhook 403 | `WHATSAPP_APP_SECRET` mismatch on Render |
| OAuth error 190 | Regenerate System User token, update Render |
