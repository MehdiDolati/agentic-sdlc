import sqlite3

conn = sqlite3.connect('docs/plans/plans.db')
cursor = conn.cursor()

# Check for agent tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%agent%'")
print("Tables with 'agent':", cursor.fetchall())

# Check for project_agents table specifically
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_agents'")
result = cursor.fetchall()
if result:
    print("\nproject_agents table exists")
    cursor.execute("PRAGMA table_info(project_agents)")
    print("Columns:", cursor.fetchall())
else:
    print("\nproject_agents table does NOT exist")

conn.close()
