-- Migration: Create repositories table
-- This migration creates the repositories table for storing code repository configurations

-- Create repositories table if it doesn't exist
CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    type TEXT NOT NULL DEFAULT 'git',
    branch TEXT,
    auth_type TEXT,  -- ssh, token, basic, none
    auth_config JSONB,  -- Store encrypted credentials
    owner TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_sync_status TEXT,
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create an index on owner for faster lookups
CREATE INDEX IF NOT EXISTS idx_repositories_owner ON repositories(owner);

-- Create an index on is_active for filtering
CREATE INDEX IF NOT EXISTS idx_repositories_is_active ON repositories(is_active);

-- Create an index on type for filtering  
CREATE INDEX IF NOT EXISTS idx_repositories_type ON repositories(type);

-- Add a trigger to update the updated_at column (PostgreSQL)
CREATE OR REPLACE FUNCTION update_repositories_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS repositories_updated_at_trigger ON repositories;
CREATE TRIGGER repositories_updated_at_trigger
    BEFORE UPDATE ON repositories
    FOR EACH ROW
    EXECUTE FUNCTION update_repositories_updated_at();