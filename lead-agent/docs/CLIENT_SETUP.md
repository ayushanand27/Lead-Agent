# LeadAgent — Client setup & handover guide

Step-by-step deploy for **Render + Supabase + Meta WhatsApp**. Use this when onboarding a paying client after demo.

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
| `BUSINESS_OWNER_PHONES` | `917073245149` or `917073245149,919876543210` (partners share leads) |
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
| `NOTIFY_OWNERS_ON_WEBHOOK` | `true` — WhatsApp alert on new webhook lead |
| `SENTRY_DSN` | Optional error monitoring (§10) |
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
2. Row 1 headers: `id | name | phone | source | status | notes | tags | consent_source | consent_at | last_contacted_at | created_at | owner_phone`

### B. Apps Script

1. **Extensions → Apps Script**
2. Paste:

```javascript
function doPost(e) {
  if (!e || !e.postData || !e.postData.contents) {
    return ContentService.createTextOutput(JSON.stringify({ error: "No data received" }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var data;
  try {
    data = JSON.parse(e.postData.contents);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ error: "Invalid JSON" }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Leads");
  if (!sheet) {
    return ContentService.createTextOutput(JSON.stringify({ error: "Leads sheet missing" }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  var row = [
    data.id || "",
    data.name || "",
    data.phone || "",
    data.source || "",
    data.status || "",
    data.notes || "",
    data.tags || "",
    data.consent_source || "",
    data.consent_at || "",
    data.last_contacted_at || "",
    data.created_at || "",
    data.owner_phone || ""
  ];
  var id = String(data.id || "");
  var lastRow = sheet.getLastRow();
  if (lastRow >= 2) {
    var allIds = sheet.getRange(2, 1, lastRow - 1, 1).getValues().flat().map(String);
    var rowIndex = allIds.indexOf(id);
    if (rowIndex !== -1) {
      sheet.getRange(rowIndex + 2, 1, 1, row.length).setValues([row]);
      return ContentService.createTextOutput(JSON.stringify({ ok: true, updated: true }))
        .setMimeType(ContentService.MimeType.JSON);
    }
  }
  sheet.appendRow(row);
  return ContentService.createTextOutput(JSON.stringify({ ok: true, created: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

3. **Deploy → Manage deployments → Edit** (keeps same URL) or New deployment
   - Execute as: **Me**
   - Who has access: **Anyone**
4. Copy **Web app URL** → Render env: `GOOGLE_SHEETS_WEBHOOK_URL`

If you create a **new** deployment, update `GOOGLE_SHEETS_WEBHOOK_URL` on Render with the new URL.

Every lead create/update from WhatsApp or webhook syncs to the sheet automatically.

**Troubleshooting:** If WhatsApp works but the sheet stays empty, redeploy after the latest app update (fixes Postgres datetime + Google redirect). Check Render **Logs** for `Google Sheets sync ok` or error lines.

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

1. Render: `CRON_SECRET=your-random-secret` → **Save & redeploy**
2. [cron-job.org](https://console.cron-job.org) → free account → **Create cronjob**

### Easy way (GET — no Advanced tab needed)

| Field | Value |
|-------|--------|
| Title | LeadAgent daily summary |
| URL | `https://lead-agent-to63.onrender.com/internal/cron/daily-summary?secret=YOUR_CRON_SECRET` |
| Enable job | ON |
| Schedule | Every day at **9:00** (set timezone to **Asia/Kolkata** in job settings if available) |

Replace `YOUR_CRON_SECRET` with the exact value from Render `CRON_SECRET`.

### Advanced way (POST + header)

After creating the job, open it → **ADVANCED** tab (not on the first screen):

| Setting | Value |
|---------|--------|
| Request method | **POST** |
| Headers | `X-Cron-Secret` = your `CRON_SECRET` |
| URL | `https://lead-agent-to63.onrender.com/internal/cron/daily-summary` (no `?secret`) |

### cron-job.org toggles (recommended)

| Toggle | Setting |
|--------|---------|
| Enable job | **ON** |
| Save responses in job history | **ON** (first week, for debugging) |
| Notify when execution fails | **ON** |
| Notify on success after failure | ON (optional) |
| Notify when disabled (too many failures) | **ON** |
| TLS cert expiry notify | OFF (optional) |
| Schedule expires | OFF |

Click **Test run** / **Run now** → should return `{"status":"ok",...}` and you get a WhatsApp summary if stale leads exist.

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

## 8. Production WhatsApp (paid client deliverable)

Demo uses Meta's **test number**. A paying client needs a **real WABA**:

| Step | Action |
|------|--------|
| 1 | Client buys / dedicates a phone number (not on regular WhatsApp app) |
| 2 | Meta Business Manager → add number → verify via SMS/voice |
| 3 | Complete **Business Verification** (2–5 business days) |
| 4 | App Review → `whatsapp_business_messaging` permission |
| 5 | Update Render: `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TOKEN` (System User) |
| 6 | Upgrade Render to **Starter** (~$7/mo) — **client pays** in setup fee; not required for your demo |
| 7 | Re-subscribe webhook on new WABA if number ID changed |

Until this is done, outbound messages only reach numbers on Meta's test recipient list (max 5).

---

## 9. Typical client package

| Included in setup | Upsell later |
|-------------------|--------------|
| Deploy + env + handover doc | Broadcast / template campaigns |
| WhatsApp AI agent + confirmation | Team inbox UI beyond dashboard |
| Admin dashboard + CSV | Voice note transcription |
| Google Sheets sync | Razorpay payment links in chat |
| Lead webhook (website / IndiaMART) | Custom CRM integrations |
| 30-day bugfix (your terms) | Ongoing retainer |

**Pricing path (0 case studies):** first client ₹15k–25k setup → testimonial → raise price. Don't quote premium until you have live client proof.

---

## 10. Verify everything works

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

**Live demo (admin):** https://lead-agent-to63.onrender.com/admin/login  
**API health:** https://lead-agent-to63.onrender.com/health
