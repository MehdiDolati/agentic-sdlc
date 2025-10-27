import sqlite3

conn = sqlite3.connect('notes.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables in database:')
for table in tables:
    print(f'  {table[0]}')

# Check priority system tables
allowed_tables = {
    'plans': 'plans',
    'features': 'features',
    'priority_changes': 'priority_changes'
}

for table_key, table_name in allowed_tables.items():
    if (table_key,) in tables:
        print(f'\n{table_key.upper()} table details:')

        # Get table schema - use direct table name from whitelist
        cursor.execute('PRAGMA table_info({})'.format(table_name))
        columns = cursor.fetchall()
        print(f'  Columns: {[col[1] for col in columns]}')

        # Check row count - use direct table name from whitelist
        cursor.execute('SELECT COUNT(*) FROM {}'.format(table_name))
        count = cursor.fetchone()[0]
        print(f'  Row count: {count}')

        # Show sample data if any
        if count > 0:
            if table == 'plans':
                cursor.execute("SELECT id, name, priority, priority_order, status FROM plans LIMIT 3")
            elif table == 'features':
                cursor.execute("SELECT id, name, priority, priority_order, status FROM features LIMIT 3")
            elif table == 'priority_changes':
                cursor.execute("SELECT entity_type, entity_id, old_priority, new_priority, change_reason FROM priority_changes LIMIT 3")

            rows = cursor.fetchall()
            print(f'  Sample data: {rows}')

conn.close()