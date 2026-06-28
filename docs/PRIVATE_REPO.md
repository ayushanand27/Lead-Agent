# Private / invite-only GitHub setup

Use this after your demo video is recorded and before LinkedIn/X posts.

## 1. Make the repo private

1. Open [github.com/ayushanand27/Lead-Agent/settings](https://github.com/ayushanand27/Lead-Agent/settings)
2. Scroll to **Danger Zone**
3. **Change repository visibility** → **Make private**
4. Type the repo name to confirm

**Effect:** Only you and people you invite can see or clone the code. Everyone else gets 404.

## 2. Invite-only access (collaborators)

1. Same repo → **Settings** → **Collaborators** (or **Manage access**)
2. Click **Add people**
3. Enter their GitHub username or email
4. Choose role:
   - **Read** — view/clone only (clients who paid for source access)
   - **Write** — can push (trusted dev partner)
   - **Admin** — full control (avoid for clients)

They get an email invite — must **Accept** before access works.

## 3. What stays public without the repo

| Public (share on LinkedIn) | Private (invite only) |
|----------------------------|------------------------|
| Live demo: [admin login](https://lead-agent-to63.onrender.com/admin/login) | Source code on GitHub |
| Demo video (upload to LinkedIn/X) | `LICENSE`, docs, migrations |
| Screenshots in your post | `.env` secrets (never in git) |

## 4. Render + Supabase

Making GitHub private does **not** affect:

- https://lead-agent-to63.onrender.com (still live)
- Supabase database
- WhatsApp bot, cron, Sheets sync

Render deploys from GitHub — with a **private** repo you may need to reconnect GitHub on Render (one-time) so deploys keep working.

## 5. LinkedIn post template (no repo link)

```
Built LeadAgent — WhatsApp AI for Indian SMB lead management.

Live demo: lead-agent-to63.onrender.com/admin/login

DM for setup.
```

## 6. Optional: public repo again later

Settings → Danger Zone → **Change visibility** → Public (only if you want open portfolio again).

**License:** Proprietary — see [LICENSE](../LICENSE). Private repo + LICENSE = code not open for copying.
