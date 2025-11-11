-- Migration: Add navigation history tracking for back button functionality
-- SQLite-compatible version

-- Create navigation_history table
CREATE TABLE IF NOT EXISTS navigation_history (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    project_id TEXT,
    from_page TEXT NOT NULL,
    to_page TEXT NOT NULL,
    navigation_type TEXT NOT NULL DEFAULT 'continue',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_navigation_history_user_project ON navigation_history(user_id, project_id);
CREATE INDEX IF NOT EXISTS idx_navigation_history_created_at ON navigation_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_navigation_history_from_page ON navigation_history(from_page);