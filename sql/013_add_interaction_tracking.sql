-- Migration: Add interaction tracking with agent and step information
-- This migration adds:
-- 1. An agent_types table to track available agents (including Supabase)
-- 2. agent_id and step columns to interaction_history for better tracking
-- 3. Foreign key relationship to agent_types table

-- Create agent_types table
CREATE TABLE IF NOT EXISTS agent_types (id INTEGER PRIMARY KEY AUTOINCREMENT, agent_type TEXT NOT NULL UNIQUE, agent_name TEXT NOT NULL, description TEXT, is_builtin BOOLEAN DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);

-- Insert built-in agents
INSERT OR IGNORE INTO agent_types (agent_type, agent_name, description, is_builtin) VALUES ('supabase', 'Supabase AI', 'Built-in Supabase AI agent for chat', 1);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_agent_types_type ON agent_types(agent_type);

-- Enhance interaction_history table
ALTER TABLE interaction_history ADD COLUMN agent_id INTEGER;
ALTER TABLE interaction_history ADD COLUMN step TEXT;
ALTER TABLE interaction_history ADD COLUMN agent_type TEXT;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_interaction_history_agent_id ON interaction_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_interaction_history_step ON interaction_history(step);
CREATE INDEX IF NOT EXISTS idx_interaction_history_project_step ON interaction_history(project_id, step);
CREATE INDEX IF NOT EXISTS idx_interaction_history_project_agent ON interaction_history(project_id, agent_id);
