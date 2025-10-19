#!/usr/bin/env python3
"""
Add is_public column to repositories table
"""
import sqlite3
from pathlib import Path

def add_is_public_column():
    db_path = Path("docs/plans/plans.db")
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    print(f"Connecting to database at {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(repositories)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_public' in columns:
            print("Column 'is_public' already exists")
            return
        
        # Add the column
        print("Adding is_public column to repositories table...")
        cursor.execute("ALTER TABLE repositories ADD COLUMN is_public BOOLEAN DEFAULT 0")
        conn.commit()
        print("✅ Column is_public added successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_is_public_column()
