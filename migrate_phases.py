import sqlite3

conn = sqlite3.connect('instance/skillsync.db')
cur = conn.cursor()

existing = [row[1] for row in cur.execute('PRAGMA table_info(milestones)').fetchall()]
print("Existing columns:", existing)

cols = {
    'phase_number': 'INTEGER DEFAULT 1',
    'phase_title': 'VARCHAR(100)',
    'phase_description': 'TEXT',
    'card_type': 'VARCHAR(20) DEFAULT "core"'
}

for col, defn in cols.items():
    if col not in existing:
        cur.execute(f'ALTER TABLE milestones ADD COLUMN {col} {defn}')
        print(f'Added column: {col}')
    else:
        print(f'Already exists: {col}')

conn.commit()
conn.close()
print('Migration complete.')
