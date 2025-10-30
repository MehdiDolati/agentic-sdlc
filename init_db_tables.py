#!/usr/bin/env python3
"""Initialize all database tables."""
import sqlite3
from pathlib import Path

db_path = Path("D:/AI/agentic-sdlc/docs/plans/plans.db")

# SQLite-compatible SQL for all tables
sql = """
-- Agent templates table
CREATE TABLE IF NOT EXISTS agent_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    config TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Repositories table
CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    api_url TEXT,
    description TEXT,
    type TEXT DEFAULT 'git',
    branch TEXT,
    auth_type TEXT,
    auth_config TEXT,
    owner TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    is_public INTEGER NOT NULL DEFAULT 0,
    last_sync_status TEXT,
    last_sync_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Project agents table
CREATE TABLE IF NOT EXISTS project_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    agent_template_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    config TEXT DEFAULT '{}',
    step_key TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_repositories_owner ON repositories(owner);
CREATE INDEX IF NOT EXISTS idx_repositories_is_active ON repositories(is_active);
CREATE INDEX IF NOT EXISTS idx_repositories_type ON repositories(type);
CREATE INDEX IF NOT EXISTS idx_project_agents_project_id ON project_agents(project_id);
CREATE INDEX IF NOT EXISTS idx_project_agents_agent_template_id ON project_agents(agent_template_id);
"""

print(f"Initializing database tables in {db_path}")
conn = sqlite3.connect(str(db_path))
try:
    conn.executescript(sql)
    conn.commit()
    print("✓ All tables created successfully")
    
    # Verify tables
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\n✓ Database tables: {', '.join(tables)}")
    
    # Check for specific tables
    required_tables = ['repositories', 'agent_templates', 'project_agents']
    for table in required_tables:
        if table in tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ✗ {table} - MISSING!")
finally:
    conn.close()

print("\n✓ Database initialization complete!")
