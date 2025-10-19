from sqlalchemy import create_engine, text
import os

# Create SQLAlchemy engine with local connection parameters
connection_params = {
    'host': '127.0.0.1',  # Use IP address instead of hostname
    'port': '5432',
    'database': 'appdb',
    'user': 'app',
    'password': 'app'
}

DATABASE_URL = f"postgresql://{connection_params['user']}:{connection_params['password']}@{connection_params['host']}:{connection_params['port']}/{connection_params['database']}"
engine = create_engine(DATABASE_URL, echo=True)  # Added echo=True for debugging

# SQL for creating tables and triggers
sql = """
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

-- Create updated_at function if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at trigger for agent_templates
DROP TRIGGER IF EXISTS update_agent_templates_updated_at ON agent_templates;
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
"""

def main():
    try:
        print("Attempting to connect to database...")
        with engine.connect() as connection:
            print("Connected successfully. Executing SQL...")
            connection.execute(text(sql))
            connection.commit()
            print("Database tables and initial data created successfully!")
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Connection parameters:", connection_params)
        raise

if __name__ == "__main__":
    main()