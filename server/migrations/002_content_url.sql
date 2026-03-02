-- Migrate content_id (UUID) to content_url (TEXT)
-- Aligns server schema with OpenAttribution spec v0.4
-- See SPECIFICATION.md changelog: "Renamed content_id (UUID) to content_url (URI string)"

-- Rename column
ALTER TABLE events RENAME COLUMN content_id TO content_url;

-- Change type from UUID to TEXT
ALTER TABLE events ALTER COLUMN content_url TYPE TEXT USING content_url::TEXT;

-- Recreate index on the renamed column
DROP INDEX IF EXISTS idx_events_content;
CREATE INDEX idx_events_content ON events(content_url) WHERE content_url IS NOT NULL;
