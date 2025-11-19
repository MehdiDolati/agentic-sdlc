-- Migration: Add use_supabase_llm field to projects table
-- This field determines whether to use Supabase LLM or custom agents from project_agents table
-- If true, use Supabase LLM for all generation tasks. If false, use agents from project_agents table.

-- Note: SQLite doesn't support COMMENT ON COLUMN, so the comment is in the migration file

ALTER TABLE projects 
ADD COLUMN use_supabase_llm INTEGER NOT NULL DEFAULT 1;
