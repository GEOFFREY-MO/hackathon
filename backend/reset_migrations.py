import os
import shutil
import sqlite3
from pathlib import Path

def reset_database():
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'smartretail.db')
    print(f"Using database at: {db_path}")

    # Connect to the database
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

def reset_migrations():
    # Remove migrations directory if it exists
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    if os.path.exists(migrations_dir):
        shutil.rmtree(migrations_dir)
        print("Removed existing migrations directory")

    # Create new migrations directory
    os.makedirs(migrations_dir)
    print("Created new migrations directory")

if __name__ == '__main__':
    print("Resetting migrations...")
    reset_migrations()
    
    print("\nResetting database...")
    reset_database()
    
    print("\nDone! Now run:")
    print("1. cd backend")
    print("2. python -m flask db init")
    print("3. python -m flask db migrate -m 'initial migration'")
    print("4. python -m flask db upgrade")
    print("5. flask run") 