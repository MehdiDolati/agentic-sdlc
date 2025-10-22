-- Add repository columns to projects table (SQLite compatible)
ALTER TABLE projects ADD COLUMN repository_id INTEGER;
ALTER TABLE projects ADD COLUMN repository_url TEXT;
ALTER TABLE projects ADD COLUMN repository_owner TEXT;
ALTER TABLE projects ADD COLUMN repository_name TEXT;
