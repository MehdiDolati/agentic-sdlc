import sqlite3

conn = sqlite3.connect('docs/plans/plans.db')
cursor = conn.cursor()

print("project_agents table schema:")
cursor.execute("PRAGMA table_info(project_agents)")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

print("\nSample project_agents data:")
cursor.execute("SELECT id, project_id, agent_template_id, name, type FROM project_agents LIMIT 5")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"  {row}")
else:
    print("  No project_agents found")

print("\nChecking project_id type mismatch:")
cursor.execute("SELECT DISTINCT typeof(project_id) FROM project_agents")
print(f"  project_agents.project_id types: {cursor.fetchall()}")

cursor.execute("SELECT DISTINCT typeof(id) FROM projects")
print(f"  projects.id types: {cursor.fetchall()}")

conn.close()
