# LeadAgent — Client command guide (Hindi + English)

Give this to your client after setup.

---

## WhatsApp pe kya likhein

### Leads dekhna

| English | Hindi |
|---------|-------|
| `list all my leads` | `saare leads dikhao` |
| `who haven't I contacted in 2 days?` | `2 din se contact nahi hua kaun?` |
| `search Ramesh` | `Ramesh dhundho` |
| `details for lead 3` | `lead 3 ki details` |

### Lead add karna

```
add lead Priya Sharma phone 9876543210 from IndiaMART
```

```
naya lead Amit phone 9199887766 source website
```

### Status change

```
mark Ramesh as warm
```
```
Priya ko converted mark karo
```

**Important:** `converted` aur `lost` pe system **YES** maangega.

### Notes aur tags

```
add note to Ramesh: called twice, no answer
```
```
add tags site-visit, urgent to Ramesh
```

### Follow-up bhejna

```
send follow up to Priya
```

Bot draft dikhayega → **YES** likho → message jayega.

---

## Safety rules

| Aap likho | Matlab |
|-----------|--------|
| `YES` / `haan` / `confirm` | Pending action approve |
| `NO` / `nahi` / `cancel` | Pending action cancel |

---

## Admin dashboard

URL: `https://your-app.onrender.com/admin`

- **Leads** — search, filter, **Edit**, CSV export
- **Sync all to Google Sheets** — one-time backfill
- **Activity** — audit log (kisne kya kiya)
- **Settings** — integrations status

---

## Naya lead aane par (website / IndiaMART)

Jab webhook se lead aata hai:
1. Database me save
2. Google Sheet update (same `id` row update — no duplicates)
3. Owner ko WhatsApp alert (agar enabled)

---

## 2 partners / 2 phones

`BUSINESS_OWNER_PHONES=phone1,phone2` — dono same leads dekhenge aur manage kar sakte hain.

---

## Support

Setup issues → contact your LeadAgent administrator.  
Meta test number = demo only. Production number alag setup hota hai (paid tier).
