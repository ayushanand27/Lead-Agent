# LeadAgent — Complete Client Demo Brief (Hinglish)

> Ye file phone pe Claude me paste karne ke liye hai. Demo ke time koi bhi doubt aaye to isme se dhundh lena. Sab kuch simple Hindi + English mix me likha hai.

---

## 0. Ek line me kya hai

**LeadAgent ek WhatsApp-based AI lead manager hai. Business owner WhatsApp pe normal chat ki tarah message karta hai (Hindi ya English), aur bot leads ko add, search, update, follow-up sab karta hai. Saath me ek admin dashboard aur Google Sheets backup bhi hai.**

Live link: `https://lead-agent-to63.onrender.com`
Admin login: `https://lead-agent-to63.onrender.com/admin/login`

---

## 1. Problem kya solve karta hai (client ko yahi bolna)

Zyada tar chhote business (real estate, coaching, trading, shops) WhatsApp pe hi leads handle karte hain. Problem:

- Leads chat me kho jaati hain
- Follow-up manually yaad rakhna padta hai
- Excel raat ko update karo
- Kisko call karna baaki hai — koi track nahi
- 2 partner ho to dono ka data alag-alag

**LeadAgent isko fix karta hai** — jaise ek employee ko WhatsApp pe bolte ho "Ramesh ko follow up karo", waise hi bot ko bolo. Bot sab yaad rakhta hai, organize karta hai, aur subah summary bhejta hai.

---

## 2. Maine (Ayush) is project me kya-kya banaya — full journey

Ye section client ko itna detail me nahi bolna, par tumhe pata hona chahiye taaki koi bhi technical sawaal aaye to answer de sako.

### Phase 1 — Core bot
- **FastAPI** backend banaya jo Meta WhatsApp ka webhook receive karta hai
- **Groq AI** (`openai/gpt-oss-120b`) ka agent loop — jo message samajh ke sahi "tool" call karta hai
- **MCP server** — 11 typed tools (4 read + 7 write, incl. `delete_lead`) jise AI use karta hai
- Owner WhatsApp pe message bheje → HMAC signature verify → AI process kare → reply wapas WhatsApp pe

### Phase 2 — Database + persistence
- Shuru me SQLite tha, par redeploy pe data udd jata tha
- **Supabase Postgres** pe shift kiya — ab leads permanent rehte hain
- RLS (Row Level Security), parameterized SQL — sab secure

### Phase 3 — Multi-owner
- `BUSINESS_OWNER_PHONES` — do partner same lead pool share karte hain
- Har query me `owner_phone` scope — ek business ka data doosre ko nahi dikhta

### Phase 4 — Admin dashboard
- Dark theme dashboard `/admin`
- Login (phone + password, bcrypt secured)
- Leads table, search, filter (status + source)
- Edit lead (status, notes, tags)
- CSV export
- Activity log (audit trail)
- Settings page

### Phase 5 — Integrations
- **Google Sheets sync** — har lead sheet me bhi jaati hai (upsert by ID, duplicate nahi)
- **Website/IndiaMART webhook** — `POST /api/leads` se lead aa sakti hai, owner ko WhatsApp alert
- **Daily cron** — subah 9 baje dono owner ko stale-lead summary

### Phase 6 — Free-tier polish (recent)
- **Landing page** `/` — health status ke saath
- **Analytics page** — Chart.js graphs (leads over time, by status, by source, conversion rate) — colorful
- **Voice notes** — WhatsApp pe voice bhejo, Groq Whisper transcribe karta hai
- **Phone masking** — dashboard me numbers half-hidden (privacy)
- **Greeting cheat sheet** — `Hi` bhejo to commands ki list aati hai
- **Fast paths** — common commands (list, search, add, mark) AI ko skip karke seedha DB se — fast + reliable

### Phase 7 — Reliability fixes (jo demo se pehle kiye)
- Search case-insensitive banaya (Postgres ILIKE) + Hindi→English romanize
- Google Sheets timeout fix — background sync, request block nahi hoti
- CI/CD test fix (GitHub Actions green)
- Cron cold-start hardening — DB wake ka wait + retry

**Total: 44 automated tests pass. GitHub Actions CI green. Live on Render.**

---

## 3. Tech stack (agar client/koi technical pooche)

| Layer | Kya use kiya |
|-------|--------------|
| Backend | Python 3.11 + FastAPI |
| AI | Groq API — `openai/gpt-oss-120b` (tool calling) |
| Voice | Groq Whisper (`whisper-large-v3-turbo`) |
| Protocol | MCP (Model Context Protocol) — 10 tools |
| WhatsApp | Meta WhatsApp Cloud API (official) |
| Database | Supabase Postgres (production) |
| Charts | Chart.js |
| Hosting | Render.com |
| Cron | cron-job.org (daily summary) |
| Uptime | UptimeRobot (keep-alive ping) |
| CI/CD | GitHub Actions |

**Sab free tier pe chal raha hai abhi.** Client paid ho to Render Starter ($7/mo) se aur fast + no sleep.

---

## 4. DEMO FLOW — step by step kya dikhana hai

> Demo se 5 min pehle: `/health` browser me kholo (server wake ho), admin login kar lo, Google Sheet ek tab me kholo. Phone silent.

### Part A — WhatsApp bot (sabse important, 2 min)

1. **`Hi` bhejo**
   - Bot turant commands ki list bhejta hai
   - Bolo: "Dekho, bot batata hai kya kar sakta hai — Hindi ya English dono chalega"

2. **`list all my leads`**
   - Saari leads ek message me — naam, phone, source, status
   - Bolo: "Sab ek jagah, koi Excel nahi kholna padta"

3. **`add lead Rahul Sharma phone 9876543210 from website`**
   - Lead turant add ho jaati hai
   - Bolo: "Ek line me lead add — bot samajh gaya naam, phone, source"

4. **`2 din se contact nahi hua kaun?`** (Hindi me poochna)
   - Bot stale leads dikhata hai
   - Bolo: "Ye sabse bada feature — koi lead miss nahi hoti, bot yaad dilata hai"

5. **Voice note** (optional par impressive)
   - Voice me bolo: "search Rahul"
   - Bot transcribe karke result deta hai
   - Bolo: "Type bhi nahi karna — bol do, ho jayega. Field pe kaam karte waqt useful"

6. **`mark Rahul Sharma as converted`** → bot YES/NO maangta hai → **`NO`**
   - Bolo: "Important change pe bot pehle confirmation maangta hai — galti se update nahi hota"

### Part B — Admin dashboard (1.5 min)

7. **Dashboard** — total leads, stale count, conversion rate cards
8. **Leads page** — search, filter, edit dikhao
9. **Edit lead** — status/tags change karke save
10. **Analytics** — colorful charts (leads over time, status, source)

### Part C — Google Sheet (30 sec)

11. Sheet kholo — same lead wahan bhi dikhegi
    - Bolo: "Jo Sheet me kaam karna pasand karte hain, unke liye auto-backup"

### Part D — Closing

12. Bolo: "WhatsApp pe baat karo, dashboard me dekho, sheet me backup. AI hai par use karna normal chat jaisa. Koi app install nahi, koi training nahi."

---

## 5. Client kya-kya pooch sakta hai (Q&A — ratlo ye)

**Q: Ye kis business ke liye hai?**
A: Koi bhi jo WhatsApp pe leads handle karta hai — real estate, coaching, trading, clinic, shop. Industry ke hisaab se AI ka behaviour bhi set kar sakte hain (real_estate, coaching, etc.)

**Q: Kya ye WATI/AiSensy jaisa hai?**
A: Nahi. Wo bulk broadcast/marketing tools hain. LeadAgent ek AI employee hai jo aapke leads manage karta hai — follow-up, status, summary. Alag use-case. Chahe to dono saath chal sakte hain.

**Q: Data safe hai?**
A: Haan — har business ka data alag (owner isolation), database me RLS, WhatsApp signature verify, passwords encrypted, audit log har change ka. Industry-standard security.

**Q: Kitne log use kar sakte hain?**
A: Multiple owner/partner same lead pool share kar sakte hain. Abhi 2 owner setup hai, badha sakte hain.

**Q: Hindi me chalega?**
A: Haan, bot us hi language me reply karta hai jisme aap likhte ho. Hindi, English, ya mix.

**Q: Setup kitna time lagega?**
A: Aapke WhatsApp business number + basic details se 1-2 din me live. Website/IndiaMART integration bhi ho sakta hai.

**Q: Kitna kharcha aayega? (pricing)**
A: (Ye tum decide karo — suggestion neeche) Hosting + WhatsApp API ka monthly cost + mera setup/maintenance charge.

**Q: Agar bot galat samajh gaya to?**
A: Important actions (message bhejna, converted mark karna) pe bot pehle YES maangta hai. Aur dashboard se manually bhi edit kar sakte ho.

**Q: Voice sach me kaam karta hai?**
A: Haan — Groq Whisper se. Live dikha dunga. (Agar network slow ho to type karke dikha dena)

**Q: Purane leads import ho sakte hain?**
A: Haan — CSV/Sheet se ya webhook se bulk aa sakte hain.

**Q: Agar internet/server down ho?**
A: Health monitoring hai (UptimeRobot). Server auto-wake hota hai. Paid plan pe hamesha on rehta hai.

---

## 6. Honest limitations (agar poocha to seedha bolna — trust banta hai)

- Abhi **Meta test number** pe hai (demo). Real customer ke liye WhatsApp Business verification chahiye — 2-3 din ka process, main karwa dunga.
- Free hosting pe pehla message thoda slow (server wake) — paid pe fast.
- Ye marketing/broadcast tool nahi — lead management tool hai.
- Bulk template blast nahi (WATI ye karta hai, ye nahi).

**In cheezon ko problem ki tarah mat batao — "ye demo setup hai, production me X kar denge" aise frame karo.**

---

## 7. Pricing suggestion (tumhare liye — client ko soch ke bolna)

Ye sirf idea hai, tum apne hisaab se:

| Item | Range |
|------|-------|
| One-time setup | ₹5,000 – ₹15,000 |
| Monthly (hosting + maintenance) | ₹1,500 – ₹4,000/mo |
| Custom features | Alag se |

Client ke budget dekh ke adjust karo. Pehle client pe kam charge karke case study/testimonial le lo.

**Bol sakte ho:** "Setup ek baar ka, phir monthly small maintenance. Hosting cost included. Aap sirf leads pe focus karo, tech main dekhta hoon."

---

## 8. Agar demo ke time kuch fail ho jaye (backup plan)

| Problem | Kya karna |
|---------|-----------|
| WhatsApp reply slow | "Server wake ho raha hai, free tier hai" bolo, 5-10 sec wait |
| Voice fail | Type karke same command dikha do — skip gracefully |
| Bot "not found" bole | Exact naam try karo, ya dashboard se dikha do |
| Sheet update na dikhe | 10 sec baad refresh, ya "background me ho raha hai" |
| Server bilkul down | `/health` kholo pehle, phir 30 sec wait, phir demo |

**Golden rule:** Ghabrana mat. Slow ho to "cloud processing + free tier" bol do — honest lagta hai, koi bura nahi maanta.

---

## 9. Ek chhota script agar client ke saamne bolna ho (30 sec pitch)

> "Sir, aap WhatsApp pe leads handle karte ho na? Problem ye hai ki follow-up miss ho jaata hai, sab chat me bikhra rehta hai. Maine ek AI bot banaya hai — aap use WhatsApp pe waise hi bolte ho jaise apne staff ko. 'Ye lead add karo', 'kisko call karna baaki hai', 'inko follow up bhejo' — bot sab karta hai. Saath me ek dashboard aur Sheet backup bhi. Main abhi live dikhata hoon."

---

## 10. Key links (demo ke time handy)

- Live app: `https://lead-agent-to63.onrender.com`
- Admin: `https://lead-agent-to63.onrender.com/admin/login`
- Health: `https://lead-agent-to63.onrender.com/health`
- Analytics: `https://lead-agent-to63.onrender.com/admin/analytics`

---

## 11. Demo commands — copy ready list

```
Hi
list all my leads
add lead Rahul Sharma phone 9876543210 from website
2 din se contact nahi hua kaun?
search Rahul
mark Rahul Sharma as converted
NO
```

Voice note: "search Rahul"

---

**Confidence rakho bhai. Product solid hai, 44 tests pass, live chal raha hai. Client ko value dikhao, tech ke deep me mat jaao jab tak wo na pooche. Paise aayenge, Cursor Pro le lena. All the best!**
