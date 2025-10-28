import sqlite3
conn = sqlite3.connect('docs/plans/plans.db')
cur = conn.cursor()
cur.execute('PRAGMA table_info(interaction_history)')
print('interaction_history columns:')
for row in cur.fetchall():
    print(f'  {row[1]}')
conn.close()