import sqlite3
import os

db_path = 'docs/plans/plans.db'
print(f'Database path: {os.path.abspath(db_path)}')
print(f'Database exists: {os.path.exists(db_path)}')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = [row[0] for row in cursor.fetchall()]
    print(f'\nTables: {tables}')
    
    # Check repositories table
    if 'repositories' in tables:
        cursor.execute('PRAGMA table_info(repositories)')
        columns = cursor.fetchall()
        print(f'\nRepositories columns:')
        for col in columns:
            print(f'  - {col[1]} ({col[2]})')
        
        cursor.execute('SELECT * FROM repositories')
        repos = cursor.fetchall()
        print(f'\nRepositories data ({len(repos)} rows):')
        for repo in repos:
            print(f'  {repo}')
    else:
        print('\nRepositories table does NOT exist!')
    
    conn.close()
