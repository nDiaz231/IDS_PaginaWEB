ALTER TABLE books ADD COLUMN resource_type TEXT NOT NULL DEFAULT 'book' CHECK(resource_type IN ('book','utility'));
UPDATE metadata SET value='4' WHERE key='schema_version';
