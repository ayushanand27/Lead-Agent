-- Persistent pending confirmation actions (survives server restarts)

CREATE TABLE IF NOT EXISTS pending_actions (
    owner_phone TEXT PRIMARY KEY,
    action_json TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE pending_actions ENABLE ROW LEVEL SECURITY;
