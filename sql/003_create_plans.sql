-- Migration: Create plans table
-- This migration creates the plans table for storing development plans

-- Create plans table if it doesn't exist
CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY,
    request TEXT NOT NULL,
    owner TEXT NOT NULL,
    artifacts JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create an index on owner for faster lookups
CREATE INDEX IF NOT EXISTS idx_plans_owner ON plans(owner);

-- Create an index on status for filtering
CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status);

-- Add a trigger to update the updated_at column (PostgreSQL)
CREATE OR REPLACE FUNCTION update_plans_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS plans_updated_at_trigger ON plans;
CREATE TRIGGER plans_updated_at_trigger
    BEFORE UPDATE ON plans
    FOR EACH ROW
    EXECUTE FUNCTION update_plans_updated_at();