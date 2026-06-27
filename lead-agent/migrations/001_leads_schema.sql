-- LeadAgent schema for Supabase Postgres
-- Run via Supabase SQL editor or: supabase db push / apply_migration

CREATE TABLE IF NOT EXISTS leads (
    id BIGSERIAL PRIMARY KEY,
    owner_phone TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    last_contacted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_owner_phone ON leads (owner_phone);
CREATE INDEX IF NOT EXISTS idx_leads_owner_status ON leads (owner_phone, status);

CREATE TABLE IF NOT EXISTS action_log (
    id BIGSERIAL PRIMARY KEY,
    owner_phone TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_log_owner_phone ON action_log (owner_phone);

-- Block public API access; app connects with DATABASE_URL (postgres role).
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_log ENABLE ROW LEVEL SECURITY;
