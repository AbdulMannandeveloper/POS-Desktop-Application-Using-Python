# Backend_Logic/Credit_Customers.py
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

DB_NAME = "POS.db"

def fetch_all_credit_customers():
    """
    Fetch all unpaid or partial credit records.
    Returns list of tuples: (credit_id, customer_name, phone, total_amount, amount_paid, remaining, sale_id)
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    # We filter out 'Paid' status to only show active debts
    cur.execute("""
        SELECT 
            cc.credit_id,
            c.customer_name,
            c.phone_number,
            cc.credit_amount,
            cc.amount_paid,
            (cc.credit_amount - cc.amount_paid) as remaining,
            cc.sale_id,
            cc.status
        FROM Customer_Credit cc
        JOIN Customers c ON cc.customer_id = c.customer_id
        WHERE cc.status IN ('Unpaid', 'Partial')
        ORDER BY remaining DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def process_credit_payment(credit_id, pay_amount):
    """
    Process a payment: Update amount_paid, update status, log history.
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    try:
        # 1. Get current details
        cur.execute("SELECT credit_amount, amount_paid FROM Customer_Credit WHERE credit_id=?", (credit_id,))
        row = cur.fetchone()
        if not row:
            return False, "Record not found"
            
        total_debt, currently_paid = row
        remaining = total_debt - currently_paid
        
        if pay_amount > remaining:
            return False, f"Amount exceeds remaining balance ({remaining})"

        # 2. Update Master Record
        new_paid = currently_paid + pay_amount
        new_status = "Paid" if new_paid >= total_debt else "Partial"
        
        cur.execute("""
            UPDATE Customer_Credit 
            SET amount_paid = ?, status = ? 
            WHERE credit_id = ?
        """, (new_paid, new_status, credit_id))

        # 3. Log History
        cur.execute("""
            INSERT INTO Credit_Payment_History (credit_id, amount_paid_now)
            VALUES (?, ?)
        """, (credit_id, pay_amount))

        conn.commit()
        
        # 4. Generate Receipt Filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"Payment_Receipt_{credit_id}_{timestamp}.pdf"
        
        # 5. Generate Receipt
        generate_payment_receipt(filename, credit_id, pay_amount, remaining - pay_amount)
        
        return True, filename
        
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def generate_payment_receipt(filename, credit_id, paid_now, remaining_after):
    """Generate a small PDF receipt for the debt payment."""
    c = canvas.Canvas(filename, pagesize=portrait((80*mm, 120*mm))) # Small thermal size
    y = 110 * mm
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.customer_name, cc.sale_id 
        FROM Customer_Credit cc 
        JOIN Customers c ON cc.customer_id = c.customer_id 
        WHERE cc.credit_id=?
    """, (credit_id,))
    res = cursor.fetchone()
    conn.close()
    
    cust_name, sale_id = res if res else ("Unknown", "N/A")

    # Header
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(40*mm, y, "DEBT PAYMENT RECEIPT")
    y -= 10
    
    c.setFont("Helvetica", 8)
    c.drawString(5*mm, y, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 5
    c.drawString(5*mm, y, f"Customer: {cust_name}")
    y -= 5
    c.drawString(5*mm, y, f"Original Sale ID: {sale_id}")
    y -= 8
    c.line(2*mm, y, 78*mm, y)
    y -= 10
    
    # Details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(5*mm, y, f"Paid Now:  {paid_now:.0f}")
    y -= 10
    c.setFont("Helvetica", 9)
    c.drawString(5*mm, y, f"Remaining Balance: {remaining_after:.0f}")
    
    y -= 15
    c.line(2*mm, y, 78*mm, y)
    y -= 10
    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(40*mm, y, "Thank you for your payment!")
    
    c.save()



