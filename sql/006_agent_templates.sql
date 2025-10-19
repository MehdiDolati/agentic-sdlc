-- Create agent_templates table
CREATE TABLE IF NOT EXISTS agent_templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, type)
);

-- Add updated_at trigger for agent_templates
CREATE TRIGGER update_agent_templates_updated_at
    BEFORE UPDATE ON agent_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default agent templates
INSERT INTO agent_templates (name, type, description, config)
VALUES 
    ('Requirements Agent', 'requirements', 'AI agent for gathering and analyzing project requirements', '{
        "model": "gpt-4",
        "temperature": 0.7,
        "capabilities": ["requirements_gathering", "user_story_generation"]
    }'::jsonb),
    ('Architecture Agent', 'architect', 'AI agent for system design and architecture decisions', '{
        "model": "gpt-4",
        "temperature": 0.3,
        "capabilities": ["architecture_design", "tech_stack_selection"]
    }'::jsonb),
    ('QA Agent', 'qa', 'AI agent for quality assurance and testing', '{
        "model": "gpt-4",
        "temperature": 0.2,
        "capabilities": ["test_planning", "code_review"]
    }'::jsonb)
ON CONFLICT (name, type) DO NOTHING;