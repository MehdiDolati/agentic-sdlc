#!/usr/bin/env python3
"""
Automatic SQLite migration system for the Agentic SDLC application.
This script automatically runs all pending database migrations on startup.
"""

import sqlite3
import sqlite3
import os
import sys
import hashlib
from pathlib import Path
from typing import List, Tuple

# Add the project root to the Python path
project_root = Path(__file__).parent.parent  # Go up to agentic-sdlc root
sys.path.insert(0, str(project_root))

def get_database_path() -> Path:
    """Get the correct database path using the same logic as the main application."""
    try:
        from services.api.core import shared
        return shared._plans_db_path()
    except ImportError:
        # Fallback if shared module is not available
        return Path("docs/plans/plans.db")

def get_migration_files() -> List[Path]:
    """Get all SQL migration files in order, excluding the initial schema."""
    sql_dir = project_root / "sql"
    if not sql_dir.exists():
        return []

    # Get all .sql files and sort them by name (assumes numbered naming)
    migration_files = sorted([f for f in sql_dir.glob("*.sql") if f.is_file()])

    # Skip 001_init.sql as it's handled by SQLAlchemy schema creation
    migration_files = [f for f in migration_files if not f.name.startswith("001_")]

    return migration_files

def get_migration_hash(content: str) -> str:
    """Get SHA256 hash of migration content for tracking."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def create_migrations_table(cursor):
    """Create the migrations tracking table if it doesn't exist."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            hash TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def get_applied_migrations(cursor) -> set:
    """Get set of applied migration versions."""
    cursor.execute("SELECT version FROM schema_migrations")
    return {row[0] for row in cursor.fetchall()}

def apply_migration(cursor, migration_file: Path):
    """Apply a single migration file."""
    print(f"[migration] Applying {migration_file.name}...")

    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Skip migrations with PostgreSQL-specific syntax that can't be easily converted
    if any(pattern in sql_content.upper() for pattern in [
        'DO $$', 'INFORMATION_SCHEMA', 'LANGUAGE PLPGSQL',
        'CREATE OR REPLACE FUNCTION', '$$ LANGUAGE'
    ]):
        print(f"[migration] Skipping complex PostgreSQL migration: {migration_file.name}")
        # Still record it as applied to avoid re-attempting
        migration_hash = get_migration_hash(sql_content)
        cursor.execute(
            "INSERT INTO schema_migrations (version, name, hash) VALUES (?, ?, ?)",
            (migration_file.stem, migration_file.name, migration_hash)
        )
        print(f"[migration] ✅ Skipped {migration_file.name}")
        return

    migration_hash = get_migration_hash(sql_content)

    # Split SQL into statements and execute them
    # Handle both ; and $$ separators for PostgreSQL functions
    statements = []
    current_statement = ""
    in_function = False

    for line in sql_content.split('\n'):
        line = line.strip()
        if not line or line.startswith('--'):
            continue

        current_statement += line + '\n'

        # Check for PostgreSQL function boundaries
        if line.startswith('CREATE OR REPLACE FUNCTION') or line.startswith('CREATE FUNCTION'):
            in_function = True
        elif line == '$$ LANGUAGE plpgsql;' or line == '$$;':
            in_function = False
            # Skip PostgreSQL functions entirely for SQLite
            current_statement = ""
            continue

        if line.endswith(';') and not in_function:
            statements.append(current_statement.strip())
            current_statement = ""

    # Add any remaining statement
    if current_statement.strip():
        statements.append(current_statement.strip())

    for stmt in statements:
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--'):
            # Skip PostgreSQL-specific statements
            if any(keyword in stmt.upper() for keyword in [
                'LANGUAGE PLPGSQL', 'RETURNS TRIGGER', 'CREATE TRIGGER',
                'DROP TRIGGER', 'CREATE OR REPLACE FUNCTION'
            ]):
                print(f"[migration] Skipping PostgreSQL-specific statement")
                continue

            # Convert PostgreSQL-specific types to SQLite equivalents
            stmt = stmt.replace('JSONB', 'TEXT')  # SQLite stores JSON as TEXT
            stmt = stmt.replace('TIMESTAMPTZ', 'TIMESTAMP')
            stmt = stmt.replace('TIMESTAMP WITH TIME ZONE', 'TIMESTAMP')
            stmt = stmt.replace('NOW()', 'CURRENT_TIMESTAMP')
            stmt = stmt.replace('SERIAL PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT')
            stmt = stmt.replace('SERIAL', 'INTEGER')
            stmt = stmt.replace("'{}'::jsonb", "'{}'")
            stmt = stmt.replace("'::jsonb", "'")  # Remove jsonb casting from string literals
            stmt = stmt.replace('ON CONFLICT', '-- ON CONFLICT')  # Comment out conflict resolution
            stmt = stmt.replace('DO NOTHING', '-- DO NOTHING')  # Comment out conflict resolution
            stmt = stmt.replace('DEFAULT CURRENT_TIMESTAMP', 'DEFAULT CURRENT_TIMESTAMP')
            # Remove PostgreSQL-specific syntax
            stmt = stmt.replace('CREATE TRIGGER', '-- CREATE TRIGGER')  # Comment out triggers
            stmt = stmt.replace('EXECUTE FUNCTION', '-- EXECUTE FUNCTION')  # Comment out function calls

            try:
                cursor.execute(stmt)
            except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
                error_msg = str(e)
                # Skip "table already exists" errors - the schema is already set up
                if "already exists" in error_msg:
                    print(f"[migration] Table already exists, skipping: {stmt.split()[2] if len(stmt.split()) > 2 else 'unknown'}")
                    continue
                # Skip "duplicate column" errors for ALTER TABLE
                elif "duplicate column name" in error_msg or "no such column" in error_msg:
                    print(f"[migration] Column operation skipped (already applied or not applicable)")
                    continue
                # Skip constraint violations for INSERT statements
                elif "UNIQUE constraint failed" in error_msg or "constraint failed" in error_msg:
                    print(f"[migration] Constraint violation, data already exists")
                    continue

    # Record the migration as applied
    cursor.execute(
        "INSERT INTO schema_migrations (version, name, hash) VALUES (?, ?, ?)",
        (migration_file.stem, migration_file.name, migration_hash)
    )

    print(f"[migration] ✅ Applied {migration_file.name}")

def run_pending_migrations():
    """Run all pending database migrations."""
    db_path = get_database_path()

    # Ensure the database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[migration] Using database: {db_path}")

    # Connect to the database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Create migrations tracking table
        create_migrations_table(cursor)

        # Get applied migrations
        applied = get_applied_migrations(cursor)

        # Get all migration files
        migration_files = get_migration_files()

        if not migration_files:
            print("[migration] No migration files found")
            return

        print(f"[migration] Found {len(migration_files)} migration files")

        # Apply pending migrations
        applied_count = 0
        for migration_file in migration_files:
            version = migration_file.stem
            if version not in applied:
                apply_migration(cursor, migration_file)
                applied_count += 1
            else:
                print(f"[migration] Skipping {migration_file.name} (already applied)")

        if applied_count == 0:
            print("[migration] No pending migrations")
        else:
            print(f"[migration] Applied {applied_count} migrations")

        # Commit all changes
        conn.commit()

    except Exception as e:
        print(f"[migration] ERROR: Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main entry point."""
    try:
        run_pending_migrations()
        print("[migration] Migration check completed successfully")
    except Exception as e:
        print(f"[migration] FATAL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()