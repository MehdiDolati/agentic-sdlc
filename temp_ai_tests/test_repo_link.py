import sqlite3

conn = sqlite3.connect('docs/plans/plans.db')
cursor = conn.cursor()

# Get a test project
cursor.execute("SELECT id, title FROM projects LIMIT 1")
project = cursor.fetchone()

if project:
    project_id = project[0]
    print(f"Test project: {project[1]} ({project_id})")
    
    # Update it with a repository
    cursor.execute("SELECT id, name FROM repositories LIMIT 1")
    repo = cursor.fetchone()
    
    if repo:
        repo_id = repo[0]
        print(f"Using repository: {repo[1]} ({repo_id})")
        
        cursor.execute("UPDATE projects SET repository_id = ? WHERE id = ?", (repo_id, project_id))
        conn.commit()
        
        # Verify
        cursor.execute("SELECT title, repository_id FROM projects WHERE id = ?", (project_id,))
        result = cursor.fetchone()
        print(f"Updated project: {result[0]} -> repository_id: {result[1]}")
        print(f"Type check: repository_id is {type(result[1])}")
    else:
        print("No repositories found to test with")
else:
    print("No projects found")

conn.close()
