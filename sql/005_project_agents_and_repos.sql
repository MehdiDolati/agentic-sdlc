-- Create repositories table if not exists
CREATE TABLE IF NOT EXISTS repositories (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    owner TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(owner, name)
);

-- Add repository relation to projects table
ALTER TABLE projects 
ADD COLUMN IF NOT EXISTS repository_id INTEGER REFERENCES repositories(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS repository_url TEXT,
ADD COLUMN IF NOT EXISTS repository_owner TEXT,
ADD COLUMN IF NOT EXISTS repository_name TEXT;

-- Create project_agents table
CREATE TABLE IF NOT EXISTS project_agents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_type TEXT NOT NULL, -- e.g., 'qa', 'dev', 'architect', etc.
    agent_name TEXT NOT NULL,
    agent_description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, agent_type)
);

-- Add updated_at trigger for project_agents
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_project_agents_updated_at
    BEFORE UPDATE ON project_agents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_project_agents_project_id ON project_agents(project_id);
CREATE INDEX IF NOT EXISTS idx_projects_repository ON projects(repository_owner, repository_name);