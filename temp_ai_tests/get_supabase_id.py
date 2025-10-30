import sqlite3
conn = sqlite3.connect('docs/plans/plans.db')
cur = conn.cursor()
cur.execute('SELECT id, agent_type FROM agent_types WHERE agent_type = "supabase"')
row = cur.fetchone()
print('Supabase agent ID:', row[0] if row else 'Not found')
conn.close()