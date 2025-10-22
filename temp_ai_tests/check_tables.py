import sqlite3

conn = sqlite3.connect('docs/plans/plans.db')
cursor = conn.cursor()

print("All tables:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for row in cursor.fetchall():
    print(f"  - {row[0]}")

print("\nProjects table schema:")
cursor.execute("PRAGMA table_info(projects)")
for row in cursor.fetchall():
    print(f"  {row[1]} ({row[2]})")

print("\nChecking for repositories-related tables:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%repo%'")
repo_tables = cursor.fetchall()
if repo_tables:
    for row in repo_tables:
        print(f"  Found: {row[0]}")
else:
    print("  No repositories table found!")

conn.close()
