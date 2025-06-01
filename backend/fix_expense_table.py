import sqlite3
import os

# Get the absolute path to the database file
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'smartretail.db')

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Drop the existing table
cursor.execute('DROP TABLE IF EXISTS expense')

# Create the table with the correct schema
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

# Commit the changes
conn.commit()

# Verify the schema
cursor.execute('PRAGMA table_info(expense)')
print("New expense table schema:")
for column in cursor.fetchall():
    print(column)

# Close the connection
conn.close()

print("\nExpense table has been recreated with the correct schema.") 