import sqlite3

conn = sqlite3.connect('docs/plans/plans.db')
cursor = conn.cursor()

print("Repositories table schema:")
cursor.execute("PRAGMA table_info(repositories)")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

print("\nRepositories data:")
cursor.execute("SELECT * FROM repositories")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"  {row}")
else:
    print("  No repositories found!")

print("\nProjects with repository_id:")
cursor.execute("SELECT id, title, repository_id FROM projects WHERE repository_id IS NOT NULL")
rows = cursor.fetchall()
if rows:
    for row in rows:
        print(f"  Project: {row[0]} - {row[1]} - repo_id: {row[2]}")
else:
    print("  No projects with repository_id set")

conn.close()
