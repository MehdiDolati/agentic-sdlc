-- Migration: Add interaction tracking with agent and step information
-- This migration adds:
-- 1. An agents table to track available agents (including Supabase)
-- 2. agent_id and step columns to interaction_history for better tracking
-- 3. Foreign key relationship to agents table

-- Create agents table
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    agent_type TEXT NOT NULL UNIQUE,
    agent_name TEXT NOT NULL,
    description TEXT,
    is_builtin BOOLEAN DEFAULT false,  -- true for Supabase, custom agents in project_agents
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Insert built-in agents
INSERT INTO agents (agent_type, agent_name, description, is_builtin) 
VALUES 
    ('supabase', 'Supabase AI', 'Built-in Supabase AI agent for chat', true)
ON CONFLICT (agent_type) DO NOTHING;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(agent_type);

-- Enhance interaction_history table
ALTER TABLE interaction_history 
ADD COLUMN IF NOT EXISTS agent_id INTEGER REFERENCES agents(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS step TEXT,  -- e.g., 'requirements', 'architecture', 'planning', 'development', 'testing'
ADD COLUMN IF NOT EXISTS agent_type TEXT;  -- Denormalized for quick access

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_interaction_history_agent_id ON interaction_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_interaction_history_step ON interaction_history(step);
CREATE INDEX IF NOT EXISTS idx_interaction_history_project_step ON interaction_history(project_id, step);
CREATE INDEX IF NOT EXISTS idx_interaction_history_project_agent ON interaction_history(project_id, agent_id);

-- Add updated_at trigger for agents table
CREATE TRIGGER IF NOT EXISTS update_agents_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
