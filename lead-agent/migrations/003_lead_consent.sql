-- Lead consent metadata (DPDP / audit trail for webhook captures)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS consent_source TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS consent_at TIMESTAMPTZ;
