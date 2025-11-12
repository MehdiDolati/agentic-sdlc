#!/usr/bin/env python3
import sys
import sqlite3
from pathlib import Path

# Check plans for specific project
project_id = 'proj-20251029141049-plan-05cd1d'
db_path = Path('docs/plans/plans.db')

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get all plans for this project
    cursor.execute('SELECT id, project_id, status, created_at FROM plans WHERE project_id = ?', (project_id,))
    plans = cursor.fetchall()
    
    print(f'Found {len(plans)} plans for project {project_id}:')
    for plan in plans:
        print(f'  Plan ID: {plan[0]}')
        print(f'  Project ID: {plan[1]}') 
        print(f'  Status: {plan[2]}')
        print(f'  Created: {plan[3]}')
        print('  ---')
    
    # Also check all plans to see what's in the database
    cursor.execute('SELECT COUNT(*) FROM plans')
    total_plans = cursor.fetchone()[0]
    print(f'\nTotal plans in database: {total_plans}')
    
    # Show some recent plans
    cursor.execute('SELECT id, project_id, status FROM plans ORDER BY created_at DESC LIMIT 5')
    recent_plans = cursor.fetchall()
    print('\nRecent plans:')
    for plan in recent_plans:
        print(f'  {plan[0]} | {plan[1]} | {plan[2]}')
        
    conn.close()
else:
    print(f'Database not found at {db_path}')