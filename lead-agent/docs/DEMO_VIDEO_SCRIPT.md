# LeadAgent — Demo Script / Website Flow

Ye file public rakh sakte ho. Isme sirf product ka simple flow explain hai, koi secret ya sensitive info nahi.

Language intentionally easy Hindi + English me rakhi gayi hai, taaki tech aur non-tech dono samajh saken.

## Website flow in simple words

LeadAgent ka basic flow bahut simple hai:

1. User WhatsApp pe bot ko message karta hai
2. Bot message samajh ke database se lead data read ya update karta hai
3. Same data dashboard me table form me dikh jaata hai
4. Agar Google Sheets sync on hai, to sheet bhi update hoti hai
5. Daily summary cron se WhatsApp pe aa sakti hai

Short version:

`WhatsApp -> backend -> database -> dashboard / sheet -> back to WhatsApp`

---

## Short explanation for README / website

> LeadAgent ek WhatsApp-based lead management product hai.  
> Aap bot ko normal chat ki tarah message karte ho, aur bot leads ko list, search, update, aur manage karta hai.  
> Same data dashboard me table form me dikhta hai, aur optionally Google Sheets me bhi sync hota hai.  
> Isse leads manually track karna easy ho jaata hai.

---

## Full demo voice script

Approx duration: 2.5 to 3 minutes  
Record order: WhatsApp -> Admin Dashboard -> Google Sheet -> optional health page

## Opening

> "Hi, maine LeadAgent build kiya hai. Ye ek WhatsApp-based lead management product hai.  
> Simple idea ye hai ki agar aap leads WhatsApp pe handle karte ho, to unhe manually yaad rakhna ya alag Excel maintain karna mushkil hota hai.  
> LeadAgent me aap bot ko message karte ho, aur bot leads ko manage karta hai.  
> Saath me ek dashboard bhi hai jahan sab data clean table form me dikh jaata hai."

---

## Part 1 — WhatsApp bot

### 1. Start with hi

**Type:** `hi`

> "Sabse pehle normal hi bhejte hain. Bot turant reply karta hai, so conversation natural lagti hai."

### 2. List all leads

**Type:** `list all my leads`

> "Ab bot database se saari leads nikaal ke ek hi message me dikhata hai.  
> Yahan name, phone, source, aur status sab ek jagah mil jaata hai."

### 3. Add a new lead

**Type:**
```text
add lead Rahul Sharma phone 9876543210 from website
```

> "Ab main chat se hi ek naya lead add kar raha hoon.  
> Name, phone, aur source ek single message me diya, aur lead database me save ho jaayegi."

### 4. Check stale leads

**Type:** `2 din se contact nahi hua kaun?`

> "Ab bot batata hai ki kaun si leads pe follow-up pending hai.  
> Isse koi important lead miss nahi hoti."

### 5. Safe confirmation

**Type:** `mark Rahul Sharma as converted`

> "Agar main koi important status change karta hoon, jaise converted ya lost, to bot pehle confirmation maangta hai.  
> Isse galat update hone ka risk kam ho jaata hai."

**Type:** `NO`

> "Main abhi NO bol raha hoon, taaki demo safe rahe."

---

## Part 2 — Admin dashboard

**Open:** `https://lead-agent-to63.onrender.com/admin/login`

> "WhatsApp ke alawa ek admin dashboard bhi hai.  
> Yahan login karke lead data aur clearly dekh sakte ho."

### Dashboard page

> "Dashboard pe total leads, stale leads, aur important summary ek glance me milti hai."

### Leads page

> "Leads page me poori table hoti hai.  
> Search kar sakte ho, filter laga sakte ho, aur CSV export bhi kar sakte ho."

### Edit lead

> "Edit button pe click karke lead ka status, tags, aur notes update kar sakte ho.  
> Save karte hi data database me update ho jaata hai."

---

## Part 3 — Google Sheet

**Open:** LeadAgent Backup sheet

> "Agar Google Sheets sync enabled hai, to same lead yahan bhi update hoti hai.  
> Nayi duplicate row nahi banti, same lead update hoti hai."

> "Jo log spreadsheet me kaam karna pasand karte hain, unke liye ye useful backup hai."

---

## Part 4 — How it works behind the scenes

> "Backend me FastAPI server hai, database Supabase Postgres hai, aur AI Groq use karta hai taaki messages samajh sake.  
> WhatsApp integration official Meta API se connected hai.  
> Isliye chat, dashboard, aur sheet — teeno same data pe kaam karte hain."

---

## Closing

> "To overall LeadAgent ka flow simple hai:  
> WhatsApp pe bot se baat karo, dashboard me leads dekho, aur sheet me backup rakho.  
> Ye product lead management ko simple aur organized bana deta hai."

---

## Quick action sequence for recording

| Step | Action |
|------|--------|
| 1 | Open WhatsApp and type `hi` |
| 2 | Type `list all my leads` |
| 3 | Type `add lead Rahul Sharma phone 9876543210 from website` |
| 4 | Type `2 din se contact nahi hua kaun?` |
| 5 | Type `mark Rahul Sharma as converted` then `NO` |
| 6 | Open admin dashboard |
| 7 | Show Leads table and Edit screen |
| 8 | Open Google Sheet |
| 9 | Optional: open `/health` |

---

## Google Sheet cleanup reminder

1. Open **LeadAgent Backup**
2. Row 1 headers rehne do
3. Rows 2 onward delete
4. Fresh demo start karo
