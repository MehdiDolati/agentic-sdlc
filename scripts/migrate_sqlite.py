#!/usr/bin/env python3
"""
SQLite migration script to add project_id column to plans table.
This script handles the local SQLite database migration.
"""

import sqlite3
import os
from pathlib import Path

def migrate_sqlite_database():
    """Migrate the local SQLite database to add project_id column."""
    
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
        # Check if project_id column already exists
        cursor.execute("PRAGMA table_info(plans)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'project_id' in columns:
            print("[migration] project_id column already exists in plans table")
            return
        
        print("[migration] Adding project_id column to plans table...")
        
        # Check if projects table exists, create it if not
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        if not cursor.fetchone():
            print("[migration] Creating projects table...")
            cursor.execute("""
                CREATE TABLE projects (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Add project_id column to plans table
        cursor.execute("ALTER TABLE plans ADD COLUMN project_id TEXT")
        
        # Create default project
        cursor.execute("""
            INSERT OR IGNORE INTO projects (id, title, description, owner, status)
            VALUES ('default-project', 'Default Project', 'Default project for existing plans', 'system', 'active')
        """)
        
        # Update existing plans to reference the default project
        cursor.execute("UPDATE plans SET project_id = 'default-project' WHERE project_id IS NULL")
        
        # Commit the changes
        conn.commit()
        print("[migration] SQLite migration completed successfully")
        
        # Verify the migration
        cursor.execute("PRAGMA table_info(plans)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"[migration] Plans table columns: {columns}")
        
        # Check if project_id was added
        if 'project_id' in columns:
            print("[migration] ✅ project_id column successfully added")
        else:
            print("[migration] ❌ project_id column was not added")
            
    except Exception as e:
        print(f"[migration] ERROR: Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_sqlite_database()
