import sqlite3

conn = sqlite3.connect('notes.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables in database:')
for table in tables:
    print(f'  {table[0]}')

# Check priority system tables
priority_tables = ['plans', 'features', 'priority_changes']
for table in priority_tables:
    if (table,) in tables:
        print(f'\n{table.upper()} table details:')

        # Get table schema
        cursor.execute(f'PRAGMA table_info({table})')
        columns = cursor.fetchall()
        print(f'  Columns: {[col[1] for col in columns]}')

        # Check row count
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
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