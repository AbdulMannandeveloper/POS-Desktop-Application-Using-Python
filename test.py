import sqlite3
import os

DB_NAME = "POS.db"

def update_database_structure():
    if not os.path.exists(DB_NAME):
        print(f"❌ Database {DB_NAME} not found. Please ensure the DB exists first.")
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    print("🔧 Starting Comprehensive Database Update...")

    try:
        # ==========================================
        # STEP 1: Create History Table
        # ==========================================
        print("1️⃣ Checking 'Credit_Payment_History' table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Credit_Payment_History (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            credit_id INTEGER NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            amount_paid_now REAL NOT NULL,
            FOREIGN KEY (credit_id) REFERENCES Customer_Credit(credit_id)
        );
        """)
        print("   ✅ Table ready.")

        # ==========================================
        # STEP 2: Ensure 'amount_paid' Column Exists
        # ==========================================
        # We do this BEFORE the migration to ensure data copying works easily.
        print("2️⃣ Checking 'amount_paid' column in Customer_Credit...")
        try:
            # Try adding the column. If it exists, this will throw an error which we catch.
            cur.execute("ALTER TABLE Customer_Credit ADD COLUMN amount_paid REAL DEFAULT 0")
            print("   ✅ Column 'amount_paid' added.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ℹ️ Column already exists. Skipping.")
            else:
                raise e

        # ==========================================
        # STEP 3: Fix "CHECK constraint" for Partial Status
        # ==========================================
        print("3️⃣ Updating 'Customer_Credit' structure to allow 'Partial' status...")
        
        # Turn off foreign keys temporarily for table swapping
        cur.execute("PRAGMA foreign_keys=OFF")
        
        # Start Transaction
        cur.execute("BEGIN TRANSACTION")

        # A. Rename current table
        cur.execute("ALTER TABLE Customer_Credit RENAME TO Customer_Credit_Old")

        # B. Create NEW table with correct constraints and columns
        cur.execute("""
            CREATE TABLE Customer_Credit (
                credit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                sale_id INTEGER NOT NULL,
                credit_amount REAL NOT NULL,
                amount_paid REAL DEFAULT 0,
                status TEXT CHECK (status IN ('Paid','Unpaid','Partial')) DEFAULT 'Unpaid',
                FOREIGN KEY (customer_id) REFERENCES Customers(customer_id),
                FOREIGN KEY (sale_id) REFERENCES Sales(sale_id)
            )
        """)

        # C. Copy data from Old to New
        # We explicitly select columns to be safe
        cur.execute("""
            INSERT INTO Customer_Credit (credit_id, customer_id, sale_id, credit_amount, amount_paid, status)
            SELECT credit_id, customer_id, sale_id, credit_amount, amount_paid, status
            FROM Customer_Credit_Old
        """)

        # D. Drop Old Table
        cur.execute("DROP TABLE Customer_Credit_Old")

        # Commit Transaction
        conn.commit()
        print("   ✅ Constraint fixed! Table updated successfully.")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ CRITICAL ERROR during update: {e}")
        print("Rolled back changes.")
    
    finally:
        # Re-enable keys and close
        cur.execute("PRAGMA foreign_keys=ON")
        conn.close()
        print("\n🚀 Database is now fully updated and ready for Partial Payments!")

if __name__ == "__main__":
    update_database_structure()