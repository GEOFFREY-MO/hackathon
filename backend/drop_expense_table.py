import sqlite3

conn = sqlite3.connect('smartretail.db')
cursor = conn.cursor()

# Drop the expense table if it exists
cursor.execute('DROP TABLE IF EXISTS expense')
conn.commit()
print('Expense table dropped successfully.')

conn.close() 