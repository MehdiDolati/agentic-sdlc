#!/usr/bin/env python3
"""
Comprehensive migration runner script for database initialization and updates.
This script runs all SQL migration files in order.
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

def get_migration_files():
    """Get all SQL migration files in order."""
    sql_dir = project_root / "sql"
    if not sql_dir.exists():
        return []
    
    # Get all .sql files and sort them by name (assumes numbered naming)
    migration_files = sorted([f for f in sql_dir.glob("*.sql") if f.is_file()])
    return migration_files

def run_migrations():
    """Run all database migrations in order."""
    # Get database connection details
    dsn = os.getenv("DATABASE_URL", "postgresql://app:app@db:5432/appdb")
    
    if _is_sqlite(dsn):
        print("[migration] SQLite detected - migrations will be handled by SQLAlchemy schema creation")
        # For SQLite, we could run a simplified version but for now let SQLAlchemy handle it
        return
    
    # For PostgreSQL, run the migrations
    try:
        import psycopg
    except ImportError:
        print("[migration] ERROR: psycopg not available for PostgreSQL migration", file=sys.stderr)
        sys.exit(1)
    
    migration_files = get_migration_files()
    if not migration_files:
        print("[migration] No migration files found")
        return
    
    print(f"[migration] Found {len(migration_files)} migration files")
    
    print("[migration] Connecting to database...")
    try:
        with psycopg.connect(dsn) as conn:
            # Create a migrations tracking table if it doesn't exist
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS migration_history (
                        filename TEXT PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
                conn.commit()
            
            # Run each migration
            for migration_file in migration_files:
                filename = migration_file.name
                
                # Check if this migration has already been applied
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT filename FROM migration_history WHERE filename = %s",
                        (filename,)
                    )
                    if cur.fetchone():
                        print(f"[migration] Skipping {filename} (already applied)")
                        continue
                
                print(f"[migration] Running migration: {filename}")
                
                # Read and execute the migration
                migration_sql = migration_file.read_text()
                
                try:
                    with conn.cursor() as cur:
                        cur.execute(migration_sql)
                        # Record that this migration was applied
                        cur.execute(
                            "INSERT INTO migration_history (filename) VALUES (%s)",
                            (filename,)
                        )
                        conn.commit()
                    print(f"[migration] ✅ {filename} completed successfully")
                except Exception as e:
                    print(f"[migration] ❌ {filename} failed: {e}")
                    conn.rollback()
                    raise
            
            print("[migration] All migrations completed successfully")
            
    except Exception as e:
        print(f"[migration] ERROR: Migration failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()