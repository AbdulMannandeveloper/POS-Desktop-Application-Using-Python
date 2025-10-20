# reporting.py
import sqlite3
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

DB_NAME = "POS.db"


# ------------------ ANALYTICS FUNCTIONS ------------------

def get_remaining_stock():
    """Return remaining stock of each product across versions."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT p.product_id, p.product_name, SUM(v.current_stock_boxes)
        FROM Products p
        JOIN Product_Versions v ON p.product_id = v.product_id
        GROUP BY p.product_id, p.product_name
    """)
    rows = cur.fetchall()
    conn.close()
    return [{"product_id": r[0], "product_name": r[1], "stock": r[2] or 0} for r in rows]


def get_sales_summary(period="day"):
    """
    Return sales analytics for given period (day/week/month/year).
    Includes totals, profit, discounts, and per-product + per-salesman breakdown.
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    now = datetime.now()
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=now.weekday())  # Monday start
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError("Invalid period. Use: day, week, month, year.")

    # ---------- Sales Totals ----------
    cur.execute("""
        SELECT SUM(total_amount), SUM(discount_applied), SUM(net_amount)
        FROM Sales
        WHERE sale_date >= ?
    """, (start_date,))
    totals = cur.fetchone()
    total_sales = totals[0] or 0
    total_discounts = totals[1] or 0
    total_net = totals[2] or 0

    # ---------- Profit ----------
    cur.execute("""
        SELECT SUM(si.profit)
        FROM Sale_Items si
        JOIN Sales s ON si.sale_id = s.sale_id
        WHERE s.sale_date >= ?
    """, (start_date,))
    total_profit = cur.fetchone()[0] or 0

    # ---------- Per-Product Breakdown ----------
    cur.execute("""
        SELECT p.product_name, SUM(si.quantity_boxes), SUM(si.profit)
        FROM Sale_Items si
        JOIN Products p ON si.product_id = p.product_id
        JOIN Sales s ON si.sale_id = s.sale_id
        WHERE s.sale_date >= ?
        GROUP BY p.product_name
    """, (start_date,))
    product_rows = cur.fetchall()

    # ---------- Per-Salesman Breakdown ----------
    cur.execute("""
        SELECT u.username, COUNT(s.sale_id), SUM(s.net_amount), SUM(si.profit)
        FROM Sales s
        JOIN Users u ON s.user_id = u.user_id
        JOIN Sale_Items si ON si.sale_id = s.sale_id
        WHERE s.sale_date >= ?
        GROUP BY u.username
    """, (start_date,))
    salesman_rows = cur.fetchall()

    conn.close()

    return {
        "period": period,
        "total_sales": total_sales,
        "discounts": total_discounts,
        "net_revenue": total_net,
        "profit": total_profit,
        "items_sold": [
            {"product_name": r[0], "quantity": r[1] or 0, "profit": r[2] or 0}
            for r in product_rows
        ],
        "salesmen": [
            {"salesman": r[0], "sales_count": r[1] or 0, "net_revenue": r[2] or 0, "profit": r[3] or 0}
            for r in salesman_rows
        ]
    }


# ------------------ REPORT PDF ------------------

def generate_report(filename="report.pdf"):
    """Generate a detailed A4 report including stock, sales, and salesman analytics."""
    stock = get_remaining_stock()
    summary_day = get_sales_summary("day")
    summary_week = get_sales_summary("week")
    summary_month = get_sales_summary("month")
    summary_year = get_sales_summary("year")

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    y = height - 40

    def draw_header(title):
        nonlocal y
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, title)
        y -= 25

    def draw_line(text):
        nonlocal y
        c.setFont("Helvetica", 10)
        c.drawString(60, y, text)
        y -= 15
        if y < 80:
            c.showPage()
            y = height - 40

    # ---------- Report Title ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, "POS System Report")
    y -= 40

    # ---------- Remaining Stock ----------
    draw_header("Remaining Stock")
    for s in stock:
        draw_line(f"{s['product_name']}: {s['stock']} boxes")

    # ---------- Daily Sales Summary ----------
    draw_header("Daily Sales Summary")
    draw_line(f"Total Sales: {summary_day['total_sales']}")
    draw_line(f"Net Revenue: {summary_day['net_revenue']}")
    draw_line(f"Profit: {summary_day['profit']}")
    draw_line("Items Sold:")
    for item in summary_day["items_sold"]:
        draw_line(f"   {item['product_name']} - {item['quantity']} boxes")

    # ---------- Daily Sales by Salesman ----------
    draw_line("Sales by Salesman:")
    for sm in summary_day["salesmen"]:
        draw_line(f"   {sm['salesman']}: {sm['sales_count']} sales, "
                  f"Revenue {sm['net_revenue']:.2f}, Profit {sm['profit']:.2f}")

    # ---------- Weekly, Monthly, Yearly Totals ----------
    for label, data in [("Weekly", summary_week), ("Monthly", summary_month), ("Yearly", summary_year)]:
        draw_header(f"{label} Summary")
        draw_line(f"Total Sales: {data['total_sales']}")
        draw_line(f"Net Revenue: {data['net_revenue']}")
        draw_line(f"Profit: {data['profit']}")

    # ---------- Weekly Product Breakdown Table ----------
    draw_header("Weekly Sales Breakdown (by Product)")
    data = [["Product", "Quantity (Boxes)", "Profit"]]
    for item in summary_week["items_sold"]:
        data.append([item['product_name'], str(item['quantity']), f"{item['profit']:.2f}"])

    table = Table(data, colWidths=[200, 120, 120])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))
    table.wrapOn(c, width, height)
    table_height = len(data) * 18
    if y - table_height < 50:
        c.showPage()
        y = height - 40
    table.drawOn(c, 60, y - table_height)
    y -= (table_height + 30)

    # ---------- Weekly Sales by Salesman Table ----------
    draw_header("Weekly Sales Breakdown (by Salesman)")
    sm_data = [["Salesman", "Sales Count", "Revenue", "Profit"]]
    for sm in summary_week["salesmen"]:
        sm_data.append([
            sm["salesman"], str(sm["sales_count"]),
            f"{sm['net_revenue']:.2f}", f"{sm['profit']:.2f}"
        ])

    sm_table = Table(sm_data, colWidths=[180, 100, 100, 100])
    sm_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightcoral),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))
    sm_table.wrapOn(c, width, height)
    sm_height = len(sm_data) * 18
    if y - sm_height < 50:
        c.showPage()
        y = height - 40
    sm_table.drawOn(c, 60, y - sm_height)

    c.save()
    print(f"✅ Report saved as {filename}")
