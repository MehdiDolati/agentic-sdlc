#!/usr/bin/env python3
"""
Migration runner script for adding project_id to plans table.
This script can be run to apply the migration to an existing database.
"""

import os
import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def _is_sqlite(url: str) -> bool:
    return bool(url) and url.strip().lower().startswith("sqlite:")

def run_migration():
    """Run the migration to add project_id to plans table."""
    
    # Get database connection details
    dsn = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/appdb")
    
    if _is_sqlite(dsn):
        print("[migration] SQLite detected - migration will be handled by SQLAlchemy schema creation")
        return
    
    # For PostgreSQL, run the migration
    try:
        import psycopg
    except ImportError:
        print("[migration] ERROR: psycopg not available for PostgreSQL migration", file=sys.stderr)
        sys.exit(1)
    
    # Read the migration file
    migration_file = project_root / "sql" / "004_add_project_id_to_plans.sql"
    if not migration_file.exists():
        print(f"[migration] ERROR: Migration file not found: {migration_file}", file=sys.stderr)
        sys.exit(1)
    
    migration_sql = migration_file.read_text()
    
    print("[migration] Connecting to database...")
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                print("[migration] Running migration: Add project_id to plans table")
                cur.execute(migration_sql)
                conn.commit()
                print("[migration] Migration completed successfully")
    except Exception as e:
        print(f"[migration] ERROR: Migration failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
