import sqlite3
import os

db_path = 'docs/plans/plans.db'
if os.path.exists(db_path):
    print(f"Database exists at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables: {tables}")
    
    # Check if projects table exists
    if 'projects' in tables:
        cursor.execute('SELECT COUNT(*) FROM projects')
        count = cursor.fetchone()[0]
        print(f"Projects count: {count}")
        
        # Get first few projects
        cursor.execute('SELECT id, title, owner FROM projects LIMIT 5')
        projects = cursor.fetchall()
        print("Sample projects:")
        for project in projects:
            print(f"  ID: {project[0]}, Title: {project[1]}, Owner: {project[2]}")
            
        # Check for u_af75c8 projects
        cursor.execute('SELECT COUNT(*) FROM projects WHERE owner = ?', ('u_af75c8',))
        user_count = cursor.fetchone()[0]
        print(f"Projects owned by u_af75c8: {user_count}")
    else:
        print("Projects table does not exist")
    
    conn.close()
else:
    print(f"Database does not exist at: {db_path}")