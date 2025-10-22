-- Fix repository_id column type to match repositories.id (VARCHAR/TEXT)
-- SQLite doesn't support ALTER COLUMN, so we need to:
-- 1. Create new columns with correct type
-- 2. Copy data
-- 3. Drop old column
-- 4. Rename new column

-- Add new repository_id column with correct type
ALTER TABLE projects ADD COLUMN repository_id_new TEXT;

-- Copy any existing data (though there shouldn't be any yet)
UPDATE projects SET repository_id_new = CAST(repository_id AS TEXT) WHERE repository_id IS NOT NULL;

-- Since SQLite doesn't support DROP COLUMN easily, we'll just use the new column
-- and ignore the old one. In production, you'd recreate the table.

-- For now, let's just use a simpler approach: drop the INTEGER column and add TEXT
-- This requires recreating the table in SQLite

-- Backup table
CREATE TABLE projects_backup AS SELECT * FROM projects;

-- Drop original table
DROP TABLE projects;

-- Recreate with correct type
CREATE TABLE projects (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    description VARCHAR,
    owner VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'new',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    repository_id TEXT,
    repository_url TEXT,
    repository_owner TEXT,
    repository_name TEXT
);

-- Restore data
INSERT INTO projects (id, title, description, owner, status, created_at, updated_at, repository_id, repository_url, repository_owner, repository_name)
SELECT id, title, description, owner, status, created_at, updated_at, 
       CAST(repository_id AS TEXT), repository_url, repository_owner, repository_name
FROM projects_backup;

-- Drop backup
DROP TABLE projects_backup;
