-- Lead tags (comma-separated labels)
ALTER TABLE leads ADD COLUMN IF NOT EXISTS tags TEXT;
