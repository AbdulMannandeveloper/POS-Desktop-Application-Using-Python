import sqlite3
from session import current_user
from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from datetime import datetime

DB_NAME = "POS.db"

# ------------------ SALES LOGIC ------------------

def create_sale(user_id, items, customer=None, discount=0, on_credit=False):
    """
    Create a sale.
    - items = [(product_id, quantity_boxes, unit_price_input), ...]
    - Deducts stock starting from oldest versions first.
    - Records cost, selling price, and profit per item.
    - If on_credit=True, customer must be provided.
    Returns: {"sale_id": ..., "total": ..., "net": ...}
    """

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    try:
        # ------------------------------
        # 1️⃣ Handle Customer
        # ------------------------------
        customer_id = None
        if on_credit:
            if not customer:
                raise ValueError("Credit sale requires a customer")

            cur.execute("SELECT customer_id FROM Customers WHERE customer_name=? LIMIT 1", 
                        (customer["name"],))
            row = cur.fetchone()

            if row:
                customer_id = row[0]
            else:
                cur.execute("""
                    INSERT INTO Customers (customer_name, phone_number, address)
                    VALUES (?, ?, ?)
                """, (customer["name"], customer.get("phone"), customer.get("address")))
                customer_id = cur.lastrowid

        # ------------------------------
        # 2️⃣ Create Sale Record
        # ------------------------------
        cur.execute("""
            INSERT INTO Sales (user_id, customer_id, discount_applied, total_amount, net_amount)
            VALUES (?, ?, 0, 0, 0)
        """, (user_id, customer_id))
        sale_id = cur.lastrowid

        total_amount = 0.0

        # ------------------------------
        # 3️⃣ Process Each Product Item
        # ------------------------------
        for product_id, quantity_boxes, unit_price_input in items:
            remaining_qty = quantity_boxes

            # Fetch product versions (FIFO)
            cur.execute("""
                SELECT version_id, current_stock_boxes, box_cost_price
                FROM Product_Versions
                WHERE product_id=?
                ORDER BY valid_from ASC
            """, (product_id,))
            versions = cur.fetchall()

            if not versions:
                raise ValueError(f"No product versions found for Product ID {product_id}")

            for version_id, stock_boxes, box_cost_price in versions:
                if remaining_qty == 0:
                    break
                if stock_boxes <= 0:
                    continue

                qty_to_deduct = min(stock_boxes, remaining_qty)

                # Defensive: prevent negative stock
                if stock_boxes < qty_to_deduct:
                    raise ValueError(f"Stock underflow for Product Version {version_id}")

                # Deduct stock
                cur.execute("""
                    UPDATE Product_Versions
                    SET current_stock_boxes = current_stock_boxes - ?
                    WHERE version_id=?
                """, (qty_to_deduct, version_id))

                # Calculate financials
                unit_cost = box_cost_price
                total_cost = round(unit_cost * qty_to_deduct, 2)

                unit_price = unit_price_input
                total_price = round(unit_price * qty_to_deduct, 2)

                profit = round(total_price - total_cost, 2)

                # Insert into Sale_Items
                cur.execute("""
                    INSERT INTO Sale_Items
                    (sale_id, product_id, version_id, quantity_boxes,
                     unit_price, total_price, unit_cost, total_cost, profit)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sale_id, product_id, version_id,
                    qty_to_deduct, unit_price, total_price,
                    unit_cost, total_cost, profit
                ))

                total_amount += total_price
                remaining_qty -= qty_to_deduct

            if remaining_qty > 0:
                raise ValueError(f"Not enough stock for Product ID {product_id}")

        # ------------------------------
        # 4️⃣ Finalize Sale
        # ------------------------------
        total_amount = round(total_amount, 2)
        net_amount = round(total_amount - discount, 2)

        cur.execute("""
            UPDATE Sales
            SET total_amount=?, discount_applied=?, net_amount=?
            WHERE sale_id=?
        """, (total_amount, discount, net_amount, sale_id))

        # ------------------------------
        # 5️⃣ Handle Credit Sale
        # ------------------------------
        if on_credit:
            cur.execute("""
                INSERT INTO Customer_Credit (customer_id, sale_id, credit_amount, status)
                VALUES (?, ?, ?, 'Unpaid')
            """, (customer_id, sale_id, net_amount))

        # ------------------------------
        # 6️⃣ Commit
        # ------------------------------
        conn.commit()
        print(f"✅ Sale {sale_id} created successfully.")
        return {"sale_id": sale_id, "total": total_amount, "net": net_amount}

    except Exception as e:
        conn.rollback()
        print("❌ Error creating sale:", e)
        return None

    finally:
        conn.close()

# ------------------ RECEIPT GENERATION ------------------

def create_receipt(sale_id, filename="receipt.pdf"):
    if not isinstance(sale_id, (int, float, str)):
        print(f"❌ Invalid sale_id type: {type(sale_id)}")
        return
    try:
        sale_id = int(sale_id)
    except Exception:
        print(f"❌ Could not convert sale_id to int: {sale_id}")
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT S.sale_id, S.sale_date, U.username AS salesman,
               S.total_amount, S.discount_applied, S.net_amount
        FROM Sales S
        JOIN Users U ON S.user_id = U.user_id
        WHERE S.sale_id=?
    """, (sale_id,))
    sale = cur.fetchone()

    cur.execute("""
        SELECT P.product_name, SI.quantity_boxes, SI.unit_price, SI.total_price
        FROM Sale_Items SI
        JOIN Products P ON SI.product_id = P.product_id
        WHERE SI.sale_id=?
    """, (sale_id,))
    items = cur.fetchall()
    conn.close()

    if not sale:
        print("❌ Sale not found.")
        return

    # --- Dynamic height calculation ---
    base_height = 90  # header, footer, totals, etc.
    item_height = 18  # each item takes 18 units
    height = (base_height + len(items) * item_height) * 1.8
    width = 58 * mm

    c = canvas.Canvas(filename, pagesize=(width, height))
    y = height - 15

    # --- Header ---
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2, y, "UK TRADERS")
    y -= 10
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, y, "Wholesale & Retail Supplier")
    y -= 20

    # --- Sale Info ---
    c.setFont("Helvetica", 8)
    c.drawString(5, y, f"Sale ID: {sale[0]}")
    y -= 10
    c.drawString(5, y, f"Date: {sale[1]}")
    y -= 10
    c.drawString(5, y, f"Salesman: {sale[2]}")
    y -= 10
    c.drawString(5, y, "-" * 30)
    y -= 10

    # --- Items Header ---
    c.setFont("Helvetica-Bold", 8)
    c.drawString(5, y, "Item")
    c.drawRightString(width - 5, y, "Total")
    y -= 8
    c.setFont("Helvetica", 8)
    c.drawString(5, y, "-" * 30)
    y -= 10

    # --- Items List ---
    for name, qty, unit_price, total in items:
        c.drawString(5, y, f"{name[:16]} x{qty}")
        c.drawRightString(width - 5, y, f"{total:.2f}")
        y -= 10
        c.setFont("Helvetica-Oblique", 7)
        c.drawString(8, y, f"@ {unit_price:.2f} each")
        c.setFont("Helvetica", 8)
        y -= 8

    # --- Divider ---
    c.drawString(5, y, "-" * 30)
    y -= 12

    # --- Totals ---
    c.setFont("Helvetica-Bold", 8)
    c.drawString(5, y, f"Subtotal:")
    c.drawRightString(width - 5, y, f"{sale[3]:.2f}")
    y -= 10
    if sale[4] > 0:
        c.drawString(5, y, f"Discount:")
        c.drawRightString(width - 5, y, f"{sale[4]:.2f}")
        y -= 10
    c.drawString(5, y, f"Net Total:")
    c.drawRightString(width - 5, y, f"{sale[5]:.2f}")
    y -= 20

    # --- Footer ---
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, y, "Thank you for shopping with us!")
    y -= 10
    c.drawCentredString(width / 2, y, datetime.now().strftime("%d-%b-%Y %I:%M %p"))

    c.save()
    print(f"🧾 Receipt saved to {filename}")