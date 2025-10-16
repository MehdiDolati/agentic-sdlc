-- idempotent-ish create for Postgres
CREATE TABLE IF NOT EXISTS notes (
  id TEXT PRIMARY KEY,
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
