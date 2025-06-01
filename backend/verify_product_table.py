import sqlite3

def verify_product_table():
    try:
        # Connect to the database
        conn = sqlite3.connect('smartretail.db')
        cursor = conn.cursor()
        
        # Check if product table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product'")
        if cursor.fetchone():
            print("Product table exists!")
            
            # Get table schema
            cursor.execute("PRAGMA table_info(product)")
            columns = cursor.fetchall()
            print("\nTable schema:")
            for col in columns:
                print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}")
        else:
            print("Product table does not exist!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    verify_product_table() 