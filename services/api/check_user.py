import sqlite3

conn = sqlite3.connect('docs/plans/plans.db')
cursor = conn.cursor()

# Check users table
cursor.execute('SELECT * FROM users WHERE email = ?', ('persianmd@yahoo.com',))
user = cursor.fetchone()
print("User found:", user)

if user:
    # Get column names
    cursor.execute('PRAGMA table_info(users)')
    columns = cursor.fetchall()
    print("Columns:", [col[1] for col in columns])

conn.close()