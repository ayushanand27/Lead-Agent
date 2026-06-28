# LeadAgent — Demo video script (voice)

Easy Hindi + English. Not industry-specific. ~3 minutes.  
Record order: WhatsApp → Admin → Google Sheet → (optional) health link.

**Before recording:** Wake Render (`/health`), clear test data, sheet rows 2+ deleted.

---

## OPEN (0:00 – 0:20)

**[Screen: WhatsApp chat with Lead Agent]**

> "Hi, maine LeadAgent banaya hai. Simple idea hai — jo bhi leads tum WhatsApp pe handle karte ho, unko manually yaad rakhne ki zarurat nahi. Tum bot ko message karte ho, woh leads manage karta hai. Aur ek chhota sa dashboard bhi hai jahan table mein sab dikhta hai."

---

## PART 1 — WhatsApp bot (0:20 – 1:30)

### Say hi

**Type:** `hi`

> "Pehle normal hi bhejte hain. Bot turant reply karta hai — jaise team member ho."

**[Wait for reply]**

---

### List leads

**Type:** `list all my leads`

> "Ab likhte hain — list all my leads. Matlab database se saari leads nikal ke list bhej dega — naam, phone, source, status. Koi app open karne ki zarurat nahi."

**[Scroll the list slowly]**

---

### Add a new lead

**Type:**
```
add lead Rahul Sharma phone 9876543210 from website
```

> "Naya lead bhi yahi se add ho sakta hai. Naam, phone, source — ek message mein. Lead save ho jati hai."

**[Wait for confirmation]**

---

### Stale / follow-up

**Type:** `2 din se contact nahi hua kaun?`

> "Yeh useful hai — kaun se leads ko tumne do din se contact nahi kiya. Follow-up miss nahi hoga."

**[Show reply]**

---

### Safe confirmation

**Type:** `mark Rahul Sharma as converted`

> "Jab status converted ya lost karte ho, bot pehle YES maangta hai. Galati se kuch change nahi hoga. Main ab NO bolunga demo ke liye."

**Type:** `NO` *(if prompted)*

> "Yeh safety feature hai — important changes se pehle confirm."

---

## PART 2 — Admin dashboard (1:30 – 2:20)

**[Open: lead-agent-to63.onrender.com/admin/login → login]**

> "WhatsApp ke alawa ek web dashboard hai. Phone number aur password se login."

**[Dashboard home — stats]**

> "Yahan total leads, kitne stale hain, converted — ek nazar mein."

**[Click Leads]**

> "Leads page pe poori table — search, filter, export CSV."

**[Click Edit on one lead]**

> "Edit pe click — status change, tags daalo, notes likho. Save karte hi database update aur Google Sheet bhi sync ho sakti hai."

**[Change status to warm, add tag `demo`, Save]**

> "Main status warm kar diya, tag demo — save."

**[Back to leads list]**

---

## PART 3 — Google Sheet (2:20 – 2:45)

**[Open LeadAgent Backup sheet]**

> "Har lead ki backup Google Sheet mein bhi jaati hai. Same lead update hoti hai — duplicate row nahi banegi agar pehle se hai."

**[Point at columns: name, phone, status, tags]**

> "Excel comfortable ho to yahan se bhi dekh sakte ho."

---

## PART 4 — How it works (short, optional) (2:45 – 3:15)

**[Optional: README or architecture — skip if non-tech audience]**

> "Backend pe FastAPI server hai, database Supabase Postgres, AI Groq se — jo message samajh ke sahi action leta hai. WhatsApp Meta ke official API se connected hai. Subah 9 baje automatic summary bhi ja sakta hai cron se."

**[Optional: /health in browser]**

> "Yeh live deployed hai — sirf demo nahi."

---

## CLOSE (3:15 – 3:30)

> "LeadAgent — WhatsApp pe leads manage karo, dashboard se control karo, sheet mein backup. Link description mein hai, khud try karo. Questions ho to message karo."

**[END]**

---

## Quick type cheat sheet

| Step | Message |
|------|---------|
| 1 | `hi` |
| 2 | `list all my leads` |
| 3 | `add lead Rahul Sharma phone 9876543210 from website` |
| 4 | `2 din se contact nahi hua kaun?` |
| 5 | `mark Rahul Sharma as converted` → `NO` |
| 6 | Admin → Edit → Save |
| 7 | Show Google Sheet |

---

## Google Sheet — clear old rows (manual)

1. Open **LeadAgent Backup** sheet  
2. Row 1 = headers (mat chhedo)  
3. Rows 2 se neeche select → Delete  
4. Save — fresh demo ke liye

Supabase + dashboard already cleared via admin reset (June 2026).
