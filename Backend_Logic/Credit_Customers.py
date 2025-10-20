# credit_customers.py
import sqlite3

DB_NAME = "POS.db"

def fetch_all_credit_customers():
    """Fetch all unpaid credit customers with sale details."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT cc.credit_id, c.customer_id, c.customer_name, c.phone_number,
               cc.credit_amount, cc.status, s.sale_date
        FROM Customer_Credit cc
        JOIN Customers c ON cc.customer_id = c.customer_id
        JOIN Sales s ON cc.sale_id = s.sale_id
        WHERE cc.status = 'Unpaid'
        ORDER BY s.sale_date DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "credit_id": r[0],
            "customer_id": r[1],
            "customer_name": r[2],
            "phone": r[3],
            "credit_amount": r[4],
            "status": r[5],
            "sale_date": r[6],
        }
        for r in rows
    ]


def mark_credit_as_paid(credit_id):
    """Mark a credit record as Paid."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Verify credit exists
    cur.execute("SELECT status FROM Customer_Credit WHERE credit_id=?", (credit_id,))
    record = cur.fetchone()
    if not record:
        conn.close()
        print("❌ Credit record not found.")
        return False

    if record[0] == "Paid":
        conn.close()
        print("⚠️ Already marked as Paid.")
        return False

    cur.execute("""
        UPDATE Customer_Credit
        SET status = 'Paid'
        WHERE credit_id=?
    """, (credit_id,))
    conn.commit()
    conn.close()
    print(f"✅ Credit record {credit_id} marked as Paid.")
    return True


def get_customer_credit_history(customer_id):
    """Fetch full credit history (paid + unpaid) of a customer."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT cc.credit_id, cc.sale_id, cc.credit_amount, cc.status, s.sale_date
        FROM Customer_Credit cc
        JOIN Sales s ON cc.sale_id = s.sale_id
        WHERE cc.credit_id = ?
        ORDER BY s.sale_date DESC
    """, (customer_id,))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "credit_id": r[0],
            "sale_id": r[1],
            "credit_amount": r[2],
            "status": r[3],
            "sale_date": r[4]
        }
        for r in rows
    ]
