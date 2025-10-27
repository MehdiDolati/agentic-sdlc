-- Migration: Add priority system for plans and features
-- This migration adds priority fields and priority change tracking

-- Create plans table if it doesn't exist
CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    size_estimate INTEGER NOT NULL DEFAULT 1,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    priority_order INTEGER, -- For custom ordering within same priority level
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Create features table if it doesn't exist
CREATE TABLE IF NOT EXISTS features (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    size_estimate INTEGER NOT NULL DEFAULT 1,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    priority_order INTEGER, -- For custom ordering within same priority level
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- Create priority_changes table to track priority changes over time
CREATE TABLE IF NOT EXISTS priority_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('plan', 'feature')),
    entity_id TEXT NOT NULL,
    old_priority TEXT CHECK (old_priority IN ('low', 'medium', 'high', 'critical')),
    new_priority TEXT NOT NULL CHECK (new_priority IN ('low', 'medium', 'high', 'critical')),
    old_priority_order INTEGER,
    new_priority_order INTEGER,
    changed_by TEXT, -- User who made the change (if available)
    change_reason TEXT, -- Optional reason for the change
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_plans_project_id ON plans(project_id);
CREATE INDEX IF NOT EXISTS idx_plans_priority ON plans(priority);
CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status);
CREATE INDEX IF NOT EXISTS idx_plans_priority_order ON plans(priority_order);

CREATE INDEX IF NOT EXISTS idx_features_plan_id ON features(plan_id);
CREATE INDEX IF NOT EXISTS idx_features_priority ON features(priority);
CREATE INDEX IF NOT EXISTS idx_features_status ON features(status);
CREATE INDEX IF NOT EXISTS idx_features_priority_order ON features(priority_order);

CREATE INDEX IF NOT EXISTS idx_priority_changes_entity ON priority_changes(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_priority_changes_created_at ON priority_changes(created_at);

-- Create triggers to update updated_at timestamps
CREATE TRIGGER IF NOT EXISTS update_plans_updated_at
    AFTER UPDATE ON plans
    FOR EACH ROW
    BEGIN
        UPDATE plans SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_features_updated_at
    AFTER UPDATE ON features
    FOR EACH ROW
    BEGIN
        UPDATE features SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Create trigger to track priority changes for plans
CREATE TRIGGER IF NOT EXISTS track_plan_priority_changes
    AFTER UPDATE ON plans
    FOR EACH ROW
    WHEN OLD.priority != NEW.priority OR (OLD.priority_order IS NOT NEW.priority_order)
    BEGIN
        INSERT INTO priority_changes (entity_type, entity_id, old_priority, new_priority, old_priority_order, new_priority_order)
        VALUES ('plan', NEW.id, OLD.priority, NEW.priority, OLD.priority_order, NEW.priority_order);
    END;

-- Create trigger to track priority changes for features
CREATE TRIGGER IF NOT EXISTS track_feature_priority_changes
    AFTER UPDATE ON features
    FOR EACH ROW
    WHEN OLD.priority != NEW.priority OR (OLD.priority_order IS NOT NEW.priority_order)
    BEGIN
        INSERT INTO priority_changes (entity_type, entity_id, old_priority, new_priority, old_priority_order, new_priority_order)
        VALUES ('feature', NEW.id, OLD.priority, NEW.priority, OLD.priority_order, NEW.priority_order);
    END;