import sqlite3
from datetime import datetime
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

DB_NAME = "POS.db"


# ------------------ INTERNAL HELPERS ------------------

def _ensure_credit_columns(cur):
    cur.execute("PRAGMA table_info(Customer_Credit)")
    cols = {row[1] for row in cur.fetchall()}

    if "amount_paid" not in cols:
        cur.execute("ALTER TABLE Customer_Credit ADD COLUMN amount_paid REAL DEFAULT 0")


def _find_or_create_customer(cur, customer, on_credit):
    customer_id = None

    if on_credit or customer:
        if customer and customer.get("name"):
            cur.execute(
                "SELECT customer_id FROM Customers WHERE customer_name=? LIMIT 1",
                (customer["name"],),
            )
            row = cur.fetchone()

            if row:
                customer_id = row[0]
            else:
                cur.execute(
                    """
                    INSERT INTO Customers (customer_name, phone_number, address)
                    VALUES (?, ?, ?)
                """,
                    (customer["name"], customer.get("phone"), customer.get("address")),
                )
                customer_id = cur.lastrowid
        elif on_credit:
            raise ValueError("Credit sale requires customer details.")

    return customer_id


def _replace_credit_for_sale(cur, sale_id, customer_id, net_amount, on_credit, amount_paid_now):
    _ensure_credit_columns(cur)

    cur.execute("SELECT credit_id FROM Customer_Credit WHERE sale_id=?", (sale_id,))
    old_credit_ids = [r[0] for r in cur.fetchall()]

    if old_credit_ids:
        for credit_id in old_credit_ids:
            cur.execute("DELETE FROM Credit_Payment_History WHERE credit_id=?", (credit_id,))
        cur.execute("DELETE FROM Customer_Credit WHERE sale_id=?", (sale_id,))

    if not on_credit:
        return

    if not customer_id:
        raise ValueError("Credit sale requires customer details.")

    if amount_paid_now < 0:
        raise ValueError("Paid amount cannot be negative.")

    if amount_paid_now > net_amount:
        raise ValueError("Paid amount cannot exceed net amount.")

    status = "Paid" if amount_paid_now >= net_amount else ("Unpaid" if amount_paid_now == 0 else "Partial")

    cur.execute(
        """
        INSERT INTO Customer_Credit (customer_id, sale_id, credit_amount, amount_paid, status)
        VALUES (?, ?, ?, ?, ?)
    """,
        (customer_id, sale_id, net_amount, amount_paid_now, status),
    )


def _insert_sale_items_and_deduct_stock(cur, sale_id, items):
    total_amount = 0.0

    for product_id, quantity_boxes, unit_price_input in items:
        remaining_qty = int(quantity_boxes)

        cur.execute(
            """
            SELECT version_id, current_stock_boxes, box_cost_price
            FROM Product_Versions
            WHERE product_id=?
            ORDER BY valid_from ASC
        """,
            (product_id,),
        )
        versions = cur.fetchall()

        if not versions:
            raise ValueError(f"No product versions found for Product ID {product_id}")

        for version_id, stock_boxes, box_cost_price in versions:
            if remaining_qty == 0:
                break
            if stock_boxes <= 0:
                continue

            qty_to_deduct = min(stock_boxes, remaining_qty)

            cur.execute(
                """
                UPDATE Product_Versions
                SET current_stock_boxes = current_stock_boxes - ?
                WHERE version_id=?
            """,
                (qty_to_deduct, version_id),
            )

            unit_cost = box_cost_price
            total_cost = round(unit_cost * qty_to_deduct, 2)
            unit_price = float(unit_price_input)
            total_price = round(unit_price * qty_to_deduct, 2)
            profit = round(total_price - total_cost, 2)

            cur.execute(
                """
                INSERT INTO Sale_Items
                (sale_id, product_id, version_id, quantity_boxes,
                 unit_price, total_price, unit_cost, total_cost, profit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    sale_id,
                    product_id,
                    version_id,
                    qty_to_deduct,
                    unit_price,
                    total_price,
                    unit_cost,
                    total_cost,
                    profit,
                ),
            )

            total_amount += total_price
            remaining_qty -= qty_to_deduct

        if remaining_qty > 0:
            raise ValueError(f"Not enough stock for Product ID {product_id}")

    return round(total_amount, 2)


# ------------------ SALES LOGIC ------------------

def create_sale(user_id, items, customer=None, discount=0, on_credit=False, amount_paid_now=0):
    """Create a new sale with optional partial-credit flow."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    try:
        customer_id = _find_or_create_customer(cur, customer, on_credit)

        cur.execute(
            """
            INSERT INTO Sales (user_id, customer_id, discount_applied, total_amount, net_amount)
            VALUES (?, ?, 0, 0, 0)
        """,
            (user_id, customer_id),
        )
        sale_id = cur.lastrowid

        total_amount = _insert_sale_items_and_deduct_stock(cur, sale_id, items)
        net_amount = round(total_amount - float(discount), 2)

        if net_amount < 0:
            raise ValueError("Discount cannot exceed total amount")

        cur.execute(
            """
            UPDATE Sales
            SET total_amount=?, discount_applied=?, net_amount=?
            WHERE sale_id=?
        """,
            (total_amount, discount, net_amount, sale_id),
        )

        _replace_credit_for_sale(cur, sale_id, customer_id, net_amount, on_credit, float(amount_paid_now))

        conn.commit()
        return {"sale_id": sale_id, "total": total_amount, "net": net_amount, "paid_now": amount_paid_now}

    except Exception as e:
        conn.rollback()
        print("❌ Error creating sale:", e)
        return None
    finally:
        conn.close()


def fetch_sale_for_edit(sale_id):
    """Fetch an existing bill so UI can open it in edit mode."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT s.sale_id, s.user_id, s.customer_id, s.discount_applied, s.net_amount,
                   c.customer_name, c.phone_number, c.address
            FROM Sales s
            LEFT JOIN Customers c ON s.customer_id = c.customer_id
            WHERE s.sale_id=?
        """,
            (sale_id,),
        )
        sale = cur.fetchone()

        if not sale:
            return None

        cur.execute(
            """
            SELECT si.product_id, p.product_name, si.quantity_boxes, si.unit_price
            FROM Sale_Items si
            JOIN Products p ON p.product_id = si.product_id
            WHERE si.sale_id=?
            ORDER BY si.sale_item_id ASC
        """,
            (sale_id,),
        )
        items = cur.fetchall()

        amount_paid = sale[4]
        status = "Paid"
        cur.execute("SELECT amount_paid, status FROM Customer_Credit WHERE sale_id=? LIMIT 1", (sale_id,))
        credit = cur.fetchone()
        if credit:
            amount_paid = credit[0] if credit[0] is not None else 0
            status = credit[1] or "Unpaid"

        return {
            "sale_id": sale[0],
            "user_id": sale[1],
            "customer_id": sale[2],
            "discount": sale[3] or 0,
            "net_amount": sale[4] or 0,
            "customer": {
                "name": sale[5] or "",
                "phone": sale[6] or "",
                "address": sale[7] or "",
            },
            "items": [
                {
                    "product_id": row[0],
                    "product_name": row[1],
                    "qty": row[2],
                    "unit_price": row[3],
                }
                for row in items
            ],
            "on_credit": status in ("Unpaid", "Partial"),
            "amount_paid_now": amount_paid or 0,
        }
    finally:
        conn.close()


def update_sale(sale_id, user_id, items, customer=None, discount=0, on_credit=False, amount_paid_now=0):
    """Update an existing sale after restoring old stock and replacing bill lines."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    try:
        cur.execute("SELECT sale_id FROM Sales WHERE sale_id=?", (sale_id,))
        if not cur.fetchone():
            raise ValueError(f"Sale ID {sale_id} not found")

        customer_id = _find_or_create_customer(cur, customer, on_credit)

        cur.execute("SELECT version_id, quantity_boxes FROM Sale_Items WHERE sale_id=?", (sale_id,))
        old_lines = cur.fetchall()

        for version_id, qty in old_lines:
            cur.execute(
                """
                UPDATE Product_Versions
                SET current_stock_boxes = current_stock_boxes + ?
                WHERE version_id=?
            """,
                (qty, version_id),
            )

        cur.execute("DELETE FROM Sale_Items WHERE sale_id=?", (sale_id,))

        total_amount = _insert_sale_items_and_deduct_stock(cur, sale_id, items)
        net_amount = round(total_amount - float(discount), 2)

        if net_amount < 0:
            raise ValueError("Discount cannot exceed total amount")

        _replace_credit_for_sale(cur, sale_id, customer_id, net_amount, on_credit, float(amount_paid_now))

        cur.execute(
            """
            UPDATE Sales
            SET user_id=?, customer_id=?, total_amount=?, discount_applied=?, net_amount=?
            WHERE sale_id=?
        """,
            (user_id, customer_id, total_amount, discount, net_amount, sale_id),
        )

        conn.commit()
        return {"sale_id": sale_id, "total": total_amount, "net": net_amount, "paid_now": amount_paid_now}

    except Exception as e:
        conn.rollback()
        print("❌ Error updating sale:", e)
        return None
    finally:
        conn.close()


# ------------------ RECEIPT GENERATION ------------------

def create_receipt(sale_id, filename="receipt.pdf", customer_name="Walk-in Customer"):
    if not isinstance(sale_id, (int, float, str)):
        return False

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT S.sale_id, S.sale_date, U.username,
               S.total_amount, S.discount_applied, S.net_amount
        FROM Sales S
        JOIN Users U ON S.user_id = U.user_id
        WHERE S.sale_id=?
    """,
        (sale_id,),
    )
    sale = cur.fetchone()

    if not sale:
        conn.close()
        return False

    cur.execute("SELECT amount_paid FROM Customer_Credit WHERE sale_id=?", (sale_id,))
    credit_info = cur.fetchone()
    paid_now = credit_info[0] if credit_info else sale[5]
    remaining_balance = sale[5] - paid_now

    cur.execute(
        """
        SELECT P.product_name, SI.quantity_boxes, SI.unit_price, SI.total_price
        FROM Sale_Items SI
        JOIN Products P ON SI.product_id = P.product_id
        WHERE SI.sale_id=?
    """,
        (sale_id,),
    )
    items = cur.fetchall()
    conn.close()

    width = 80 * mm
    base_height = 120
    per_item_height = 8
    dynamic_height = max(base_height + len(items) * per_item_height, 140)

    doc = SimpleDocTemplate(
        filename,
        pagesize=(width, dynamic_height * mm),
        leftMargin=4,
        rightMargin=4,
        topMargin=4,
        bottomMargin=6,
    )

    getSampleStyleSheet()
    normal = ParagraphStyle("normal", fontName="Helvetica", fontSize=8, leading=9)
    bold = ParagraphStyle("bold", fontName="Helvetica-Bold", fontSize=9, leading=10)

    elements = []
    elements.append(Paragraph("<b>UK TRADERS</b>", bold))
    elements.append(Paragraph("Wholesale & Retail Supplier", normal))
    elements.append(Spacer(1, 6))

    now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")
    elements.append(Paragraph(f"Sale ID: {sale[0]}", normal))
    elements.append(Paragraph(f"Date: {now_str}", normal))
    elements.append(Paragraph(f"Customer: {customer_name}", normal))
    elements.append(Paragraph(f"Salesman: {sale[2]}", normal))
    elements.append(Spacer(1, 4))

    table_data = [["Item", "Qty", "Rate", "Total"]]
    for name, qty, unit_price, total in items:
        item_para = Paragraph(name, normal)
        table_data.append([item_para, f"{qty}", f"{unit_price:.0f}", f"{total:.0f}"])

    table = Table(table_data, colWidths=[width * 0.50, width * 0.12, width * 0.18, width * 0.20])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 6))

    totals_data = [["Subtotal:", f"{sale[3]:.0f}"]]
    if sale[4] > 0:
        totals_data.append(["Discount:", f"-{sale[4]:.0f}"])

    totals_data.append(["Net Total:", f"{sale[5]:.0f}"])

    if remaining_balance > 0:
        totals_data.append(["Paid Now:", f"{paid_now:.0f}"])
        totals_data.append(["Balance Due:", f"{remaining_balance:.0f}"])

    totals_table = Table(totals_data, colWidths=[width - 25, 20])
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("FONT", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elements.append(totals_table)
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<i>Thank you for shopping with us!</i>", normal))

    try:
        doc.build(elements)
        print(f"🧾 Receipt saved to {filename}")
        return True
    except Exception as e:
        print(f"❌ Receipt generation error: {e}")
        return False
