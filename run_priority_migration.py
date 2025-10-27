import sqlite3
import os
import sys
from pathlib import Path

# Add the project root to the Python path to import shared utilities
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def get_database_path():
    """Get the correct database path using the same logic as the main application."""
    # Import the shared utilities
    try:
        from services.api.core import shared
        return shared._plans_db_path()
    except ImportError:
        # Fallback if shared module is not available
        return Path("docs/plans/plans.db")

def run_migration():
    # Get the correct database path
    db_path = get_database_path()
    
    print(f"Using database path: {db_path}")
    
    # Read the migration file
    migration_file = Path('sql/012_add_priority_system.sql')
    if not migration_file.exists():
        print(f"Error: Migration file not found: {migration_file}")
        return
        
    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    print('Migration SQL loaded')

    # Connect to database and run migration
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Split the SQL into individual statements
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip() and not stmt.startswith('--')]

        for i, stmt in enumerate(statements):
            if stmt:
                print(f'Executing statement {i+1}: {stmt[:50]}...')
                cursor.execute(stmt)

        conn.commit()
        print('Migration completed successfully!')

        # Check tables after migration
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print('Tables after migration:')
        for table in tables:
            print(f'  {table[0]}')

    except Exception as e:
        print(f'Error during migration: {e}')
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()