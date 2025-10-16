#!/usr/bin/env python3
"""
Comprehensive SQLite migration script for all database tables.
This script handles the local SQLite database migration for all required tables.

Security Notes:
- Uses parameterized queries where possible to prevent SQL injection
- Validates table and column names before use in PRAGMA statements
- PRAGMA statements cannot use parameterized queries but input validation prevents injection
"""

import sqlite3
import os
from pathlib import Path

def validate_identifier(identifier, identifier_type="identifier"):
    """Validate SQL identifiers (table names, column names) to prevent injection."""
    if not identifier:
        raise ValueError(f"Empty {identifier_type} not allowed")
    
    # Allow alphanumeric characters, underscores, and hyphens
    if not identifier.replace('_', '').replace('-', '').isalnum():
        raise ValueError(f"Invalid {identifier_type}: {identifier}. Only alphanumeric, underscore, and hyphen characters allowed.")
    
    # Ensure it doesn't start with a number
    if identifier[0].isdigit():
        raise ValueError(f"Invalid {identifier_type}: {identifier}. Cannot start with a number.")
    
    return True

def table_exists(cursor, table_name):
    """Check if a table exists in the database."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

import re
from typing import List

def _parse_columns_from_create_table_sql(create_sql: str) -> List[str]:
    """
    Extract column names from a CREATE TABLE ... (...) SQL string.

    This is a lightweight parser:
    - finds the outer parentheses block,
    - splits top-level comma-separated column/constraint entries,
    - returns the first token of each column-definition entry as the column name.
    It ignores table-level constraints (CHECK, PRIMARY KEY(...) with no leading column name).
    """
    if not create_sql:
        return []

    # find the first opening '(' that starts the column list and the matching closing ')'
    m = re.search(r'\((.*)\)\s*$', create_sql.strip(), re.S)
    if not m:
        return []

    inner = m.group(1).strip()

    # split at top-level commas (ignore commas inside parentheses)
    cols: List[str] = []
    buf = []
    paren = 0
    for ch in inner:
        if ch == '(':
            paren += 1
        elif ch == ')':
            paren -= 1
        if ch == ',' and paren == 0:
            item = ''.join(buf).strip()
            if item:
                cols.append(item)
            buf = []
        else:
            buf.append(ch)
    # leftover
    last = ''.join(buf).strip()
    if last:
        cols.append(last)

    # for each column definition, take the first token as the column name (skip constraints)
    col_names = []
    for item in cols:
        # skip entries that start with constraint keywords
        if re.match(r'^\s*(CONSTRAINT|PRIMARY|UNIQUE|CHECK|FOREIGN)\b', item, re.I):
            continue
        # column name is the first word (possibly quoted)
        item = item.lstrip()
        # handle quoted identifiers: "name", 'name', [name], or `name`
        q = item[0]
        if q in ('"', "'", '`', '['):
            # find matching quote/bracket
            if q == '[':
                closing = ']'
            else:
                closing = q
            # column name is up to the closing quote/bracket
            try:
                end = item.index(closing, 1)
                col = item[1:end]
            except ValueError:
                # malformed quoting - fallback
                parts = item.split()
                col = parts[0]
        else:
            # unquoted: first token
            parts = item.split(None, 1)
            col = parts[0]
        col_names.append(col)
    return col_names

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table using parameterized sqlite_master lookup."""
    # Validate table name to be conservative (defense-in-depth)
    validate_identifier(table_name, "table name")

    # Use a parameterized query against sqlite_master to avoid formatting SQL with user input
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name = ?", (table_name,))
    row = cursor.fetchone()
    if not row:
        return False

    create_sql = row[0]
    columns = _parse_columns_from_create_table_sql(create_sql)
    return column_name in columns

def migrate_sqlite_database():
    """Migrate the local SQLite database to include all required tables."""
    
    # Path to the SQLite database
    db_path = Path("docs/plans/plans.db")
    
    if not db_path.exists():
        print(f"[migration] SQLite database not found at {db_path}")
        return
    
    print(f"[migration] Found SQLite database at {db_path}")
    
    # Connect to the database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 1. Create projects table if it doesn't exist
        if not table_exists(cursor, 'projects'):
            print("[migration] Creating projects table...")
            cursor.execute("""
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    owner TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("[migration] ✅ Projects table created")
        else:
            print("[migration] Projects table already exists")
        
        # 2. Create notes table if it doesn't exist
        if not table_exists(cursor, 'notes'):
            print("[migration] Creating notes table...")
            cursor.execute("""
                CREATE TABLE notes (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("[migration] ✅ Notes table created")
        else:
            print("[migration] Notes table already exists")
        
        # 3. Create repositories table if it doesn't exist
        if not table_exists(cursor, 'repositories'):
            print("[migration] Creating repositories table...")
            cursor.execute("""
                CREATE TABLE repositories (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    description TEXT,
                    type TEXT NOT NULL DEFAULT 'git',
                    branch TEXT,
                    auth_type TEXT,
                    auth_config TEXT,  -- JSON as TEXT for SQLite
                    owner TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,  -- BOOLEAN as INTEGER for SQLite
                    last_sync_status TEXT,
                    last_sync_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create indexes for repositories
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_repositories_owner ON repositories(owner)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_repositories_is_active ON repositories(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_repositories_type ON repositories(type)")
            print("[migration] ✅ Repositories table created")
        else:
            print("[migration] Repositories table already exists")
        
        # 4. Handle plans table and project_id column
        if table_exists(cursor, 'plans'):
            if not column_exists(cursor, 'plans', 'project_id'):
                print("[migration] Adding project_id column to plans table...")
                cursor.execute("ALTER TABLE plans ADD COLUMN project_id TEXT")
                
                # Create default project
                cursor.execute("""
                    INSERT OR IGNORE INTO projects (id, title, description, owner, status)
                    VALUES ('default-project', 'Default Project', 'Default project for existing plans', 'system', 'active')
                """)
                
                # Update existing plans to reference the default project
                cursor.execute("UPDATE plans SET project_id = 'default-project' WHERE project_id IS NULL")
                print("[migration] ✅ project_id column added to plans table")
            else:
                print("[migration] project_id column already exists in plans table")
        else:
            print("[migration] Plans table doesn't exist - will be created by application")
        
        # 5. Create agents table if it doesn't exist
        if not table_exists(cursor, 'agents'):
            print("[migration] Creating agents table...")
            cursor.execute("""
                CREATE TABLE agents (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    agent_type TEXT NOT NULL,
                    config TEXT NOT NULL,  -- JSON as TEXT for SQLite
                    status TEXT NOT NULL DEFAULT 'inactive',
                    last_heartbeat TIMESTAMP,
                    capabilities TEXT,  -- JSON as TEXT for SQLite
                    owner TEXT NOT NULL,
                    is_public INTEGER NOT NULL DEFAULT 0,  -- BOOLEAN as INTEGER for SQLite
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("[migration] ✅ Agents table created")
        else:
            print("[migration] Agents table already exists")
        
        # 6. Create agent_runs table if it doesn't exist
        if not table_exists(cursor, 'agent_runs'):
            print("[migration] Creating agent_runs table...")
            cursor.execute("""
                CREATE TABLE agent_runs (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    project_id TEXT,
                    plan_id TEXT,
                    status TEXT NOT NULL DEFAULT 'queued',
                    input_data TEXT,  -- JSON as TEXT for SQLite
                    output_data TEXT,  -- JSON as TEXT for SQLite
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("[migration] ✅ Agent runs table created")
        else:
            print("[migration] Agent runs table already exists")
        
        # Commit all changes
        conn.commit()
        print("[migration] SQLite migration completed successfully")
        
        # Verify the migration
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"[migration] Available tables: {', '.join(sorted(tables))}")
        
        if table_exists(cursor, 'plans') and column_exists(cursor, 'plans', 'project_id'):
            print("[migration] ✅ All migrations completed successfully")
        else:
            print("[migration] ⚠️  Some migrations may not have completed")
            
    except Exception as e:
        print(f"[migration] ERROR: Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_sqlite_database()
