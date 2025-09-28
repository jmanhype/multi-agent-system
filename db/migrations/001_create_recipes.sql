-- Recipe storage schema for DataAgent pattern reuse
-- Supports SQLite and PostgreSQL

CREATE TABLE IF NOT EXISTS recipes (
    recipe_id TEXT PRIMARY KEY,
    schema_fingerprint TEXT NOT NULL,
    intent_template TEXT NOT NULL,
    intent_embedding BLOB NOT NULL,
    plan_structure TEXT NOT NULL,
    tool_argument_templates TEXT NOT NULL,
    success_count INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    last_used_at TEXT NOT NULL
);

-- Index for fast lookup by schema fingerprint
CREATE INDEX IF NOT EXISTS idx_schema_fp 
ON recipes(schema_fingerprint);

-- Index for recency-based retrieval (DESC for most recent first)
CREATE INDEX IF NOT EXISTS idx_last_used 
ON recipes(last_used_at DESC);