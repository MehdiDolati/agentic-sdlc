import sqlite3

# Connect to the correct database
conn = sqlite3.connect('docs/plans/plans.db')
cursor = conn.cursor()

print("Applying priority system migration...")

# Check current plans table schema
cursor.execute('PRAGMA table_info(plans)')
columns = cursor.fetchall()
column_names = [col[1] for col in columns]
print(f"Current plans columns: {column_names}")

# Add priority columns if they don't exist
if 'priority' not in column_names:
    print("Adding priority column to plans table...")
    cursor.execute("ALTER TABLE plans ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical'))")

if 'priority_order' not in column_names:
    print("Adding priority_order column to plans table...")
    cursor.execute("ALTER TABLE plans ADD COLUMN priority_order INTEGER")

if 'size_estimate' not in column_names:
    print("Adding size_estimate column to plans table...")
    cursor.execute("ALTER TABLE plans ADD COLUMN size_estimate INTEGER NOT NULL DEFAULT 1")

if 'updated_at' not in column_names:
    print("Adding updated_at column to plans table...")
    cursor.execute("ALTER TABLE plans ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")

# Create features table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS features (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    size_estimate INTEGER NOT NULL DEFAULT 1,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    priority_order INTEGER,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
)
''')

# Create priority_changes table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS priority_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('plan', 'feature')),
    entity_id TEXT NOT NULL,
    old_priority TEXT CHECK (old_priority IN ('low', 'medium', 'high', 'critical')),
    new_priority TEXT NOT NULL CHECK (new_priority IN ('low', 'medium', 'high', 'critical')),
    old_priority_order INTEGER,
    new_priority_order INTEGER,
    changed_by TEXT,
    change_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# Create indexes
cursor.execute("CREATE INDEX IF NOT EXISTS idx_plans_priority ON plans(priority)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_plans_priority_order ON plans(priority_order)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_plan_id ON features(plan_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_priority ON features(priority)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_status ON features(status)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_features_priority_order ON features(priority_order)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority_changes_entity ON priority_changes(entity_type, entity_id)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority_changes_created_at ON priority_changes(created_at)")

# Create triggers
cursor.execute('''
CREATE TRIGGER IF NOT EXISTS update_plans_updated_at
    AFTER UPDATE ON plans
    FOR EACH ROW
    BEGIN
        UPDATE plans SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END
''')

cursor.execute('''
CREATE TRIGGER IF NOT EXISTS update_features_updated_at
    AFTER UPDATE ON features
    FOR EACH ROW
    BEGIN
        UPDATE features SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END
''')

cursor.execute('''
CREATE TRIGGER IF NOT EXISTS track_plan_priority_changes
    AFTER UPDATE ON plans
    FOR EACH ROW
    WHEN OLD.priority != NEW.priority OR (OLD.priority_order IS NOT NEW.priority_order)
    BEGIN
        INSERT INTO priority_changes (entity_type, entity_id, old_priority, new_priority, old_priority_order, new_priority_order)
        VALUES ('plan', NEW.id, OLD.priority, NEW.priority, OLD.priority_order, NEW.priority_order);
    END
''')

cursor.execute('''
CREATE TRIGGER IF NOT EXISTS track_feature_priority_changes
    AFTER UPDATE ON features
    FOR EACH ROW
    WHEN OLD.priority != NEW.priority OR (OLD.priority_order IS NOT NEW.priority_order)
    BEGIN
        INSERT INTO priority_changes (entity_type, entity_id, old_priority, new_priority, old_priority_order, new_priority_order)
        VALUES ('feature', NEW.id, OLD.priority, NEW.priority, OLD.priority_order, NEW.priority_order);
    END
''')

conn.commit()
print("Migration completed successfully!")

# Verify the changes
cursor.execute('PRAGMA table_info(plans)')
columns = cursor.fetchall()
column_names = [col[1] for col in columns]
print(f"Updated plans columns: {column_names}")

cursor.execute("SELECT COUNT(*) FROM features")
feature_count = cursor.fetchone()[0]
print(f"Features table has {feature_count} rows")

cursor.execute("SELECT COUNT(*) FROM priority_changes")
change_count = cursor.fetchone()[0]
print(f"Priority changes table has {change_count} rows")

conn.close()