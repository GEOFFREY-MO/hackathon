import sqlite3

try:
    # Connect to the SQLite database
    conn = sqlite3.connect('smartretail.db')
    cursor = conn.cursor()

    # Get the schema of the product table
    cursor.execute("PRAGMA table_info(product);")
    columns = cursor.fetchall()

    # Print the schema
    print("Schema of the product table:")
    for column in columns:
        print(column)

except sqlite3.Error as e:
    print(f"An error occurred: {e}")

finally:
    # Close the connection
    if 'conn' in locals():
        conn.close() 