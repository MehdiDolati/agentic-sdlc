-- Migration: Add api_url column to repositories table
-- Date: 2025-10-16

ALTER TABLE repositories ADD COLUMN api_url VARCHAR NULL;

-- Update description
COMMENT ON COLUMN repositories.api_url IS 'API endpoint URL for the repository service';