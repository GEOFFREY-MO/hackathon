import sqlite3

conn = sqlite3.connect('smartretail.db')
cursor = conn.cursor()

print('All tables:')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for t in tables:
    print(t[0])

if any(t[0] == 'product' for t in tables):
    print('\nProduct table schema:')
    cursor.execute("PRAGMA table_info(product)")
    for row in cursor.fetchall():
        print(row)
else:
    print('\nNo product table found!')

conn.close() 