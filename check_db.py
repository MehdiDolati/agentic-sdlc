import sqlite3

conn = sqlite3.connect('docs/plans/plans.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables in database:')
for table in tables:
    print(f'  {table[0]}')

# Check interaction_history table
if ('interaction_history',) in tables:
    print('\nINTERACTION_HISTORY table details:')

    cursor.execute('PRAGMA table_info(interaction_history)')
    columns = cursor.fetchall()
    print(f'  Columns: {[col[1] for col in columns]}')

    cursor.execute('SELECT COUNT(*) FROM interaction_history')
    count = cursor.fetchone()[0]
    print(f'  Row count: {count}')

# Check agents table
if ('agents',) in tables:
    print('\nAGENTS table details:')

    cursor.execute('PRAGMA table_info(agents)')
    columns = cursor.fetchall()
    print(f'  Columns: {[col[1] for col in columns]}')

    cursor.execute('SELECT COUNT(*) FROM agents')
    count = cursor.fetchone()[0]
    print(f'  Row count: {count}')

    if count > 0:
        cursor.execute('SELECT * FROM agents')
        rows = cursor.fetchall()
        print(f'  Sample data: {rows}')

conn.close()