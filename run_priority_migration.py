import sqlite3
import os

def run_migration():
    # Read the migration file
    with open('sql/012_add_priority_system.sql', 'r') as f:
        migration_sql = f.read()

    print('Migration SQL loaded')

    # Connect to database and run migration
    conn = sqlite3.connect('notes.db')
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