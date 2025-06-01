import sqlite3

conn = sqlite3.connect('smartretail.db')
cursor = conn.cursor()

# Create the expense table
cursor.execute('''
CREATE TABLE IF NOT EXISTS expense (
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

# Print the schema to a file
cursor.execute('PRAGMA table_info(expense)')
columns = cursor.fetchall()
with open('expense_table_schema.txt', 'w') as f:
    f.write('Expense table schema:\n')
    for col in columns:
        f.write(str(col) + '\n')

conn.close() 