-- Create agent_templates table for SQLite
CREATE TABLE IF NOT EXISTS agent_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    config TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, type)
);

-- Insert default agent templates
INSERT OR IGNORE INTO agent_templates (name, type, description, config)
VALUES 
    ('Requirements Agent', 'requirements', 'AI agent for gathering and analyzing project requirements', '{"model": "gpt-4", "temperature": 0.7, "capabilities": ["requirements_gathering", "user_story_generation"]}'),
    ('Architecture Agent', 'architect', 'AI agent for system design and architecture decisions', '{"model": "gpt-4", "temperature": 0.3, "capabilities": ["architecture_design", "tech_stack_selection"]}'),
    ('QA Agent', 'qa', 'AI agent for quality assurance and testing', '{"model": "gpt-4", "temperature": 0.2, "capabilities": ["test_planning", "code_review"]}');