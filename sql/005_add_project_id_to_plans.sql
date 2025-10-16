-- Migration: Add project_id column to plans table
-- This migration adds the project_id column to link plans to projects

-- Add project_id column to plans table if it doesn't exist
DO $$
BEGIN
    -- Check if the column already exists
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'plans' 
        AND column_name = 'project_id'
    ) THEN
        -- Add the column
        ALTER TABLE plans ADD COLUMN project_id TEXT;
        
        -- Create a default project for existing plans
        INSERT INTO projects (id, title, description, owner, status, created_at, updated_at)
        SELECT 
            'default-project',
            'Default Project',
            'Default project for existing plans',
            'system',
            'active',
            NOW(),
            NOW()
        WHERE NOT EXISTS (SELECT 1 FROM projects WHERE id = 'default-project');
        
        -- Update existing plans to reference the default project
        UPDATE plans SET project_id = 'default-project' WHERE project_id IS NULL;
        
        -- Make the column NOT NULL after populating it
        ALTER TABLE plans ALTER COLUMN project_id SET NOT NULL;
        
        -- Add foreign key constraint if projects table exists
        IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'projects') THEN
            ALTER TABLE plans ADD CONSTRAINT fk_plans_project_id 
                FOREIGN KEY (project_id) REFERENCES projects(id);
        END IF;
    END IF;
END $$;
