# LeadAgent — Client setup guide ($1000 tier, free hosting)

Step-by-step setup for **Render (free) + Supabase (free) + Meta test WhatsApp**. No paid Cursor deploy required.

---

## 1. Render environment variables

After deploy, set these in **Render → Environment**:

### Required (already have most)

| Variable | Example |
|----------|---------|
| `GROQ_API_KEY` | From console.groq.com |
| `WHATSAPP_*` | Meta developer dashboard |
| `DATABASE_URL` + `DATABASE_PASSWORD` | Supabase pooler |
| `BUSINESS_NAME` | `Sharma Realty` |
| `BUSINESS_OWNER_PHONES` | `917073245149` |
| `ADMIN_DASHBOARD_PASSWORD` | See §2 below |
| `ADMIN_SESSION_SECRET` | Long random string |

### Security (recommended)

| Variable | Purpose |
|----------|---------|
| `ADMIN_DASHBOARD_PASSWORD` | Use **bcrypt hash** in production (§2) |
| `ADMIN_IP_ALLOWLIST` | Optional: `1.2.3.4,5.6.7.8` — only these IPs reach `/admin` |
| `LEAD_WEBHOOK_SECRET` | Secret for `POST /api/leads` (§4) |
| `CRON_SECRET` | Daily summary cron (§5) |

### Integrations (optional, free)

| Variable | Purpose |
|----------|---------|
| `GOOGLE_SHEETS_WEBHOOK_URL` | Apps Script URL (§3) |
| `BUSINESS_INDUSTRY` | `general` \| `real_estate` \| `trading` \| `coaching` |

---

## 2. Secure admin password (bcrypt)

**Plain password works** but for clients use a hash:

```bash
cd lead-agent
pip install bcrypt
python scripts/hash_admin_password.py
```

Copy output to Render as `ADMIN_DASHBOARD_PASSWORD` (value starts with `$2b$`).

Login still uses the **plain password** you typed — only the stored env value is hashed.

---

## 3. Google Sheets backup (free — no Google Cloud billing)

### A. Create sheet

1. Google Sheets → new spreadsheet → name tab **Leads**
2. Row 1 headers: `id | name | phone | source | status | notes | consent_source | consent_at | last_contacted_at | created_at | owner_phone`

### B. Apps Script

1. **Extensions → Apps Script**
2. Paste:

```javascript
function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Leads");
  if (!sheet) {
    return ContentService.createTextOutput(JSON.stringify({ error: "Leads sheet missing" }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var data = JSON.parse(e.postData.contents);
  sheet.appendRow([
    data.id || "",
    data.name || "",
    data.phone || "",
    data.source || "",
    data.status || "",
    data.notes || "",
    data.consent_source || "",
    data.consent_at || "",
    data.last_contacted_at || "",
    data.created_at || "",
    data.owner_phone || ""
  ]);
  return ContentService.createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

3. **Deploy → New deployment → Web app**
   - Execute as: **Me**
   - Who has access: **Anyone**
4. Copy **Web app URL** → Render env: `GOOGLE_SHEETS_WEBHOOK_URL`

Every lead create/update from WhatsApp or webhook syncs to the sheet automatically.

---

## 4. Website / form lead capture

Set `LEAD_WEBHOOK_SECRET` on Render (random string).

```bash
curl -X POST "https://lead-agent-to63.onrender.com/api/leads" \
  -H "Content-Type: application/json" \
  -H "X-Lead-Webhook-Secret: YOUR_SECRET" \
  -d '{
    "name": "Priya Sharma",
    "phone": "919876543210",
    "source": "website",
    "notes": "Interested in 2BHK",
    "consent_source": "contact_form"
  }'
```

**Zapier / Make:** HTTP POST action with same header + JSON body.

Check: `GET /api/leads/health` → `webhook_configured: true`

---

## 5. Daily summary cron (free)

1. Render: `CRON_SECRET=your-random-secret`
2. [cron-job.org](https://cron-job.org) → free account
3. Job: `POST https://YOUR-APP.onrender.com/internal/cron/daily-summary`
4. Header: `X-Cron-Secret: your-random-secret`
5. Schedule: daily 9:00 AM IST

---

## 6. WhatsApp command cheat sheet (give to client)

### English

| Say this | Bot does |
|----------|----------|
| `list all my leads` | Shows all leads |
| `who haven't I contacted in 2 days?` | Stale leads |
| `add lead Ramesh phone 9876543210 from Surat` | Creates lead |
| `mark Ramesh as converted` | Asks YES → updates |
| `send follow up to Priya` | Draft → YES → sends |

### Hindi

| Bolo | Bot karega |
|------|------------|
| `saare leads dikhao` | List |
| `2 din se contact nahi hua kaun?` | Stale leads |
| `Ramesh ko converted mark karo` | YES confirm |

### Safety

- **YES** / **haan** = confirm pending action  
- **NO** / **nahi** = cancel  

---

## 7. Security features included

| Feature | Status |
|---------|--------|
| Webhook HMAC (Meta) | Built-in |
| Admin login rate limit | 5 fails / 15 min |
| Login audit log | Activity page |
| bcrypt password | Supported |
| IP allowlist | Optional env |
| Security headers | HSTS, X-Frame-Options, etc. |
| Lead consent metadata | Webhook captures |
| Owner isolation | All queries scoped |

---

## 8. What you sell for ~$1000

| Included | Not included (upsell later) |
|----------|----------------------------|
| Deploy + env setup | Real WABA number + Meta verification |
| WhatsApp AI agent | Team shared inbox |
| Admin dashboard | Broadcast campaigns |
| Google Sheets sync | AI voice calling |
| Lead webhook | GST / invoicing |
| 30-day bugfix support (your terms) | Render paid tier (no cold start) |

---

## 9. Verify everything works

```bash
curl https://lead-agent-to63.onrender.com/health
curl https://lead-agent-to63.onrender.com/api/leads/health
```

1. WhatsApp: add a lead  
2. Dashboard: `/admin` — lead visible  
3. Sheets: new row (if configured)  
4. Webhook: curl test above  
5. Activity: login + lead_created events  

---

**Live demo:** https://lead-agent-to63.onrender.com/admin
