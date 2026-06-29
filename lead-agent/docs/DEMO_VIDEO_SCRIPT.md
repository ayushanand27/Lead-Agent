# LeadAgent — OBS Demo Script (English)

> **How to use:** Turn on OBS screen recording. Read exactly what’s under **SAY**. Do what’s under **SCREEN** / **ACTION**.  
> Duration: ~3–4 min · Upload to Google Drive → post link on LinkedIn / X · Repo stays private.

---

## Before you record (5 min)

| # | Task |
|---|------|
| 1 | Open WhatsApp Web — chat with your business number ready |
| 2 | Admin: `https://lead-agent-to63.onrender.com/admin/login` |
| 3 | Google Sheet (LeadAgent Backup) in another tab |
| 4 | Keep 0–2 test leads for a clean demo |
| 5 | Silence phone notifications |
| 6 | OBS: Window or Display capture (WhatsApp + browser) |
| 7 | Mic check — say one line, listen back |

**Tip:** Keep this script on a second screen. Don’t read from paper on camera.

---

## LinkedIn / X caption (after upload)

```
WhatsApp leads don’t fail because teams don’t care.
They fail because follow-up is manual.

I built LeadAgent — a WhatsApp bot that manages leads like a team member.

• Chat to add / search / update leads
• Voice notes supported
• Admin dashboard + Google Sheets sync
• Daily morning summary

3-min demo: [VIDEO_LINK]

Repo is private. DM me if you want to explore this.
```

---

## VIDEO SCRIPT — start recording here

---

### SCENE 0 — Hook (15 sec)

**SCREEN:** Empty WhatsApp chat or landing page `https://lead-agent-to63.onrender.com/`

**SAY:**

> "If you run leads on WhatsApp — real estate, coaching, trading, any SMB — you know this problem: leads come in, but follow-up gets missed. Notes stay in chat, Excel is separate, and nobody knows who still needs a call.  
> I built **LeadAgent** for that — a WhatsApp bot that manages your leads, like a team member."

---

### SCENE 1 — WhatsApp: first chat (45 sec)

**SCREEN:** WhatsApp Web — your business chat

**ACTION 1:** Type → `Hi`

**SAY:**

> "First I send a simple **Hi**. The bot replies instantly with what it can do — list leads, search, add leads, stale follow-ups — in Hindi or English, whatever’s easier."

*(Pause so viewers can read the cheat-sheet reply)*

**ACTION 2:** Type → `list all my leads`

**SAY:**

> "Now I say **list all my leads**. The bot pulls everything from the database in one message — name, phone, source, status — all in one place."

---

### SCENE 2 — Add lead + natural language (50 sec)

**ACTION:** Type →
```text
add lead Priya Mittal phone 9876543210 from LinkedIn
```

**SAY:**

> "Adding a lead is just chat. One line — name, phone, source. This one came from **LinkedIn**. It saves instantly and shows up in the list."

*(Wait for reply)*

**ACTION:** Type → `who haven't I contacted in 2 days?`

**SAY:**

> "You can ask in plain language — who haven’t I contacted in two days? The bot understands and shows leads that need follow-up. Nothing important gets missed."

---

### SCENE 3 — Voice note (30 sec) — optional but strong

**SCREEN:** WhatsApp — record a voice note

**ACTION:** Say clearly: *"search Priya"*

**SAY:**

> "You don’t have to type — **voice notes** work too. I say search Priya, it transcribes and finds the lead. Useful when you’re on the move."

*(Skip this scene if voice fails — rest of demo is enough)*

---

### SCENE 4 — Safe confirmation (35 sec)

**ACTION:** Type → `mark Priya Mittal as converted`

**SAY:**

> "For important changes — like marking converted or lost — the bot asks for **confirmation** first. Less risk of accidental updates."

*(Bot asks YES/NO)*

**ACTION:** Type → `NO`

**SAY:**

> "For the demo I’ll say **NO**. In real use, you’d say YES and it updates."

---

### SCENE 5 — Admin dashboard (60 sec)

**SCREEN:** Browser → admin login → dashboard

**SAY:**

> "There’s also an **admin dashboard**. Clean table view — phone numbers masked for privacy."

**ACTION:** Show dashboard

**SAY:**

> "Total leads, stale count, and **conversion rate** at a glance."

**ACTION:** Sidebar → **Leads** — show search / filters

**SAY:**

> "Search, status filter, source filter, CSV export — all here."

**ACTION:** Click **Edit** on a lead (optional save)

**SAY:**

> "Edit status, tags, notes — save once, database updates, and Google Sheets syncs if enabled."

**ACTION:** Sidebar → **Analytics** (~10 sec)

**SAY:**

> "Analytics shows trends — how many leads came in, conversions, and which sources perform best."

---

### SCENE 6 — Google Sheet (25 sec)

**SCREEN:** Google Sheet tab

**SAY:**

> "For teams that live in **spreadsheets** — there’s backup sync. No duplicate rows — same lead updates by ID."

*(Show 1–2 rows)*

---

### SCENE 7 — Webhook + daily summary (25 sec)

**SCREEN:** Settings page or stay on dashboard

**SAY:**

> "Leads from your website or IndiaMART can hit a **webhook** — straight into the system, with optional WhatsApp alerts to owners. And every morning at **9 AM**, an automatic summary of who needs follow-up."

---

### SCENE 8 — Closing + CTA (30 sec)

**SCREEN:** Landing page or dashboard — hold calm

**SAY:**

> "So that’s **LeadAgent** — chat on WhatsApp, view on dashboard, backup in Sheets.  
> AI under the hood, but it feels like normal messaging — no app install, no training.  
> Code is **private**, but if this fits your business, **DM me on LinkedIn or X** — happy to walk through a live demo. Thanks!"

**SCREEN:** Hold 2 seconds → stop OBS.

---

## Action cheat sheet (recording order)

| # | Action |
|---|--------|
| 1 | WhatsApp → `Hi` |
| 2 | `list all my leads` |
| 3 | `add lead Priya Mittal phone 9876543210 from LinkedIn` |
| 4 | `who haven't I contacted in 2 days?` |
| 5 | Voice: "search Priya" *(optional)* |
| 6 | `mark Priya Mittal as converted` → `NO` |
| 7 | Admin → Dashboard |
| 8 | Leads → filter → Edit |
| 9 | Analytics |
| 10 | Google Sheet |
| 11 | Closing + CTA |

---

## OBS settings

| Setting | Value |
|---------|--------|
| Resolution | 1920×1080 or 1280×720 |
| FPS | 30 |
| Format | MP4 |
| Target length | 3–4 min |

**Google Drive:** “Anyone with the link can view” → paste link in post.

---

## If something goes wrong

| Issue | Fix |
|-------|-----|
| Slow bot reply | Wait 3–5 sec — don’t cut, looks natural |
| Typo in chat | Re-record from `Hi` |
| Empty sheet | Admin → “Sync all to Google Sheets” once |
| Voice fails | Skip Scene 3 |
| Render asleep | Open `/health` first, then record |

---

## Optional: clean data before demo

1. Google Sheet — keep header row, delete data rows  
2. Clear test leads in admin if you want a fresh start  
3. Run the script sequence — Priya lead will appear as new
