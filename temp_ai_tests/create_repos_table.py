#!/usr/bin/env python3
"""Create the repositories table in SQLite database."""
import sqlite3
from pathlib import Path

db_path = Path("D:/AI/agentic-sdlc/docs/plans/plans.db")

# SQLite-compatible version of the SQL
sql = """
CREATE TABLE IF NOT EXISTS repositories (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    api_url TEXT,
    description TEXT,
    type TEXT NOT NULL DEFAULT 'git',
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

CREATE INDEX IF NOT EXISTS idx_repositories_owner ON repositories(owner);
CREATE INDEX IF NOT EXISTS idx_repositories_is_active ON repositories(is_active);
CREATE INDEX IF NOT EXISTS idx_repositories_type ON repositories(type);
"""

print(f"Creating repositories table in {db_path}")
conn = sqlite3.connect(str(db_path))
try:
    conn.executescript(sql)
    conn.commit()
    print("✓ Table created successfully")
    
    # Verify
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='repositories'")
    if cursor.fetchone():
        print("✓ Table 'repositories' exists")
    else:
        print("✗ Table creation failed")
finally:
    conn.close()
