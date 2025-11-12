import sqlite3

# The backend uses D:/AI/docs/plans/plans.db (based on _repo_root() which returns D:/AI)
db_path = 'D:/AI/docs/plans/plans.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check current columns
cursor.execute("PRAGMA table_info(projects)")
columns = [row[1] for row in cursor.fetchall()]
print(f"Current columns: {columns}")

# Add missing repository-related columns
columns_to_add = [
    ('repository_id', 'TEXT'),
    ('repository_url', 'TEXT'),
    ('repository_owner', 'TEXT'),
    ('repository_name', 'TEXT')
]

for col_name, col_type in columns_to_add:
    if col_name not in columns:
        print(f"Adding {col_name} column...")
        cursor.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type}")
        conn.commit()
        print(f"✓ Added {col_name} column")
    else:
        print(f"✓ {col_name} column already exists")

# Verify the changes
cursor.execute("PRAGMA table_info(projects)")
columns_after = [row[1] for row in cursor.fetchall()]
print(f"\nColumns after migration: {columns_after}")

conn.close()
print("\n✅ Migration complete!")
