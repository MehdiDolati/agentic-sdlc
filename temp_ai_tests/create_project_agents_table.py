import sqlite3
from datetime import datetime

conn = sqlite3.connect('docs/plans/plans.db')
cursor = conn.cursor()

# Create project_agents table
cursor.execute("""
CREATE TABLE IF NOT EXISTS project_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    agent_template_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    config TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_template_id) REFERENCES agent_templates(id) ON DELETE CASCADE
)
""")

conn.commit()
print("project_agents table created successfully")

# Verify
cursor.execute("PRAGMA table_info(project_agents)")
print("\nColumns in project_agents:")
for col in cursor.fetchall():
    print(f"  {col}")

conn.close()
