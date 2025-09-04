-- Create notes table if it does not exist
CREATE TABLE IF NOT EXISTS notes (
  id TEXT PRIMARY KEY,
  data JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
