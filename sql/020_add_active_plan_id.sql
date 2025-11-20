-- Migration: Add active_plan_id to projects table
-- This migration adds a field to track which plan is currently active for a project

-- Add active_plan_id column to projects table
ALTER TABLE projects 
ADD COLUMN active_plan_id TEXT REFERENCES plans(id);

-- Create an index for faster active plan lookups
CREATE INDEX IF NOT EXISTS idx_projects_active_plan_id ON projects(active_plan_id);

-- Create a function to automatically set the active plan when a plan becomes 'in_progress'
CREATE OR REPLACE FUNCTION auto_set_active_plan()
RETURNS TRIGGER AS $$
BEGIN
    -- If a plan status is changed to 'in_progress' or 'planning', make it the active plan
    IF NEW.status IN ('in_progress', 'planning') AND (OLD.status IS NULL OR OLD.status != NEW.status) THEN
        UPDATE projects 
        SET active_plan_id = NEW.id 
        WHERE id = NEW.project_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update active plan
DROP TRIGGER IF EXISTS auto_set_active_plan_trigger ON plans;
CREATE TRIGGER auto_set_active_plan_trigger
    AFTER UPDATE ON plans
    FOR EACH ROW
    EXECUTE FUNCTION auto_set_active_plan();