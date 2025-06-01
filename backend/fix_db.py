import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'smartretail.db')
print(f"Using database at: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Drop and recreate expense table
cursor.execute('DROP TABLE IF EXISTS expense')
cursor.execute('''
CREATE TABLE expense (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_id INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    date DATETIME NOT NULL,
    created_by INTEGER NOT NULL,
    FOREIGN KEY (shop_id) REFERENCES shop(id),
    FOREIGN KEY (created_by) REFERENCES user(id)
)
''')

conn.commit()
print("Expense table recreated successfully")

# Show the schema
cursor.execute('PRAGMA table_info(expense)')
print("\nSchema:")
for row in cursor.fetchall():
    print(row)

conn.close() 