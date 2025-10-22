-- Add step_key column to project_agents table to track which SDLC step the agent is assigned to
-- SQLite doesn't support IF NOT EXISTS in ALTER TABLE, so we'll just try to add it
-- If it fails because column exists, that's okay

-- For PostgreSQL compatibility, use this commented version:
-- ALTER TABLE project_agents ADD COLUMN IF NOT EXISTS step_key TEXT;

-- For SQLite, create table if not exists and alter (SQLite will error if column exists, which is fine)
-- We'll handle this gracefully in code

-- Try to add the column (will fail silently if exists)
ALTER TABLE project_agents ADD COLUMN step_key TEXT;
