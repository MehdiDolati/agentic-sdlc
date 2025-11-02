import sqlite3
from pathlib import Path

db_path = Path('docs/plans/plans.db')
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print('Tables:', tables)
    conn.close()
else:
    print('Database does not exist')