# IndiaMART & JustDial → LeadAgent (Zapier / Make — free tier)

Connect marketplace enquiries to LeadAgent without code.

---

## Prerequisites

On Render:

```
LEAD_WEBHOOK_SECRET=your-random-secret
BUSINESS_OWNER_PHONES=917073245149
NOTIFY_OWNERS_ON_WEBHOOK=true
```

Test: `GET https://your-app.onrender.com/api/leads/health`

---

## Option A — Zapier (easiest)

1. [zapier.com](https://zapier.com) → **Create Zap**
2. **Trigger:** IndiaMART Lead (or Webhooks by Zapier / Google Forms / Typeform)
3. **Action:** Webhooks by Zapier → **POST**
4. URL:
   ```
   https://lead-agent-to63.onrender.com/api/leads
   ```
5. Headers:
   | Key | Value |
   |-----|--------|
   | `Content-Type` | `application/json` |
   | `X-Lead-Webhook-Secret` | your `LEAD_WEBHOOK_SECRET` |
6. Body (JSON):
   ```json
   {
     "name": "{{buyer_name}}",
     "phone": "{{buyer_phone}}",
     "source": "IndiaMART",
     "notes": "{{product}} — {{city}}",
     "tags": "indiamart, inbound",
     "consent_source": "indiamart_lead"
   }
   ```
7. Test → check dashboard + Google Sheet + WhatsApp alert

---

## Option B — Make.com (free tier)

Same as Zapier:
- Module: **HTTP → Make a request**
- Method: `POST`
- URL + headers as above
- Body type: JSON

---

## Option C — Manual curl (testing)

```bash
curl -X POST "https://lead-agent-to63.onrender.com/api/leads" \
  -H "Content-Type: application/json" \
  -H "X-Lead-Webhook-Secret: YOUR_SECRET" \
  -d '{
    "name": "Buyer Name",
    "phone": "919876543210",
    "source": "IndiaMART",
    "notes": "Enquiry for 2BHK",
    "tags": "indiamart, delhi"
  }'
```

---

## JustDial / website form

Use **Webhooks by Zapier** or **Make HTTP** with the same endpoint. Map form fields to `name`, `phone`, `source`, `notes`.

---

## Field reference

| Field | Required | Example |
|-------|----------|---------|
| `name` | Yes | `Ramesh Patel` |
| `phone` | Yes | `919876543210` |
| `source` | No | `IndiaMART` |
| `notes` | No | Product / city |
| `tags` | No | `indiamart, hot` |
| `consent_source` | No | `indiamart_form` |
| `owner_phone` | No | Defaults to first `BUSINESS_OWNER_PHONES` |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 403 Forbidden | Wrong `X-Lead-Webhook-Secret` |
| 400 no owner | Set `BUSINESS_OWNER_PHONES` on Render |
| No WhatsApp alert | `NOTIFY_OWNERS_ON_WEBHOOK=true` |
| Sheet duplicate | Update Apps Script to upsert by `id` (see CLIENT_SETUP.md §3) |
