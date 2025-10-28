import sqlite3
conn = sqlite3.connect('docs/plans/plans.db')
cur = conn.cursor()
cur.execute('SELECT id FROM agents WHERE agent_type = "supabase" AND name = "Supabase AI Chat"')
row = cur.fetchone()
print('Supabase agent ID:', row[0] if row else 'Not found')
conn.close()