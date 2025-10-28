-- Migration: Add default Supabase chat agent to agents table
-- This migration inserts a default Supabase chat agent that users can interact with

INSERT OR IGNORE INTO agents (id, name, description, agent_type, config, status, capabilities, owner, is_public, created_at, updated_at)
VALUES (
    'supabase-chat-default',
    'Supabase AI Chat',
    'Default Supabase AI agent for chat interactions',
    'supabase',
    '{"provider": "supabase", "model": "default", "temperature": 0.7, "max_tokens": 1000}',
    'active',
    '{"chat": true, "code": false, "planning": false}',
    'system',
    1,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);