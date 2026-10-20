import sqlite3
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QTableWidget, QTableWidgetItem,
    QDialog, QComboBox, QDateEdit, QGroupBox, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
from Backend_Logic.Sales import create_receipt as generate_sale_receipt

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

DB_NAME = "POS.db"

# ==========================================
#  REPORTING UI CLASS
# ==========================================

class ReportingUI(QWidget):
    def __init__(self, submodule=None, parent=None):
        super().__init__(parent)
        self.seller_colors = {}
        
        self.setStyleSheet("""
            QWidget { font-family: Segoe UI, Arial; }
            QLabel { font-size: 10pt; color: #2c3e50; }
            QPushButton {
                font-size: 10pt; padding: 8px 12px; border: none;
                border-radius: 4px; background-color: #3498db; color: white; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QTableWidget {
                font-size: 9pt; border: 1px solid #bdc3c7;
                border-radius: 4px; background-color: white; gridline-color: #ecf0f1;
            }
            QHeaderView::section {
                background-color: #34495e; color: white; padding: 6px; font-weight: bold; border: none;
            }
            QGroupBox {
                font-weight: bold; font-size: 11pt; border: 1px solid #bdc3c7;
                border-radius: 6px; margin-top: 10px; padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #2c3e50; }
            QComboBox, QDateEdit { padding: 6px; border: 1px solid #bdc3c7; border-radius: 4px; background-color: white; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title = QLabel("📊 Sales Reporting & Analytics")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50; padding: 10px; background-color: #ecf0f1; border-radius: 6px;")
        main_layout.addWidget(title)

        # ---- Filters Group ----
        filters_group = QGroupBox("Report Filters")
        filters_layout = QHBoxLayout(filters_group)
        filters_layout.setSpacing(15)

        # Seller filter
        seller_container = QVBoxLayout()
        seller_container.addWidget(QLabel("Seller:"))
        self.seller_filter = QComboBox()
        self.seller_filter.addItem("All Sellers")
        self._load_seller_filter()
        self.seller_filter.currentIndexChanged.connect(self._load_sales)
        seller_container.addWidget(self.seller_filter)

        # Date filters
        date_container = QVBoxLayout()
        date_container.addWidget(QLabel("Date Range:"))
        date_range_layout = QHBoxLayout()
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1)) 
        self.start_date.setMaximumDate(QDate.currentDate())
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setMaximumDate(QDate.currentDate())

        self.start_date.dateChanged.connect(self._load_sales)
        self.end_date.dateChanged.connect(self._load_sales)

        date_range_layout.addWidget(self.start_date)
        date_range_layout.addWidget(QLabel("to"))
        date_range_layout.addWidget(self.end_date)
        date_container.addLayout(date_range_layout)

        filters_layout.addLayout(seller_container)
        filters_layout.addLayout(date_container)
        filters_layout.addStretch()

        main_layout.addWidget(filters_group)

        # ---- Top Stats Group ----
        stats_group = QGroupBox("Period Summary")
        stats_layout = QHBoxLayout(stats_group)

        # Revenue & Profit Labels
        self.total_revenue_label = QLabel("Total Revenue: 0.00")
        self.total_revenue_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: #2980b9; background-color: #eaf2f8; padding: 10px; border-radius: 4px; border: 1px solid #a9cce3;")
        
        self.total_profit_label = QLabel("Total Profit: 0.00")
        self.total_profit_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: #27ae60; background-color: #e8f6f3; padding: 10px; border-radius: 4px; border: 1px solid #a3e4d7;")

        stats_layout.addWidget(self.total_revenue_label)
        stats_layout.addWidget(self.total_profit_label)
        stats_layout.addStretch()
        
        # Reports Buttons
        btn_report = QPushButton("📄 Sales PDF")
        btn_report.clicked.connect(self._generate_report)
        
        btn_stock_report = QPushButton("📦 Stock PDF")
        btn_stock_report.clicked.connect(self._generate_stock_report)
        
        # NEW: Receipt Button
        btn_receipt = QPushButton("🖨️ Print Receipt")
        btn_receipt.setStyleSheet("background-color: #8e44ad; color: white;") # Purple to distinguish
        btn_receipt.clicked.connect(self._print_selected_receipt)

        stats_layout.addWidget(btn_report)
        stats_layout.addWidget(btn_stock_report)
        stats_layout.addWidget(btn_receipt)

        main_layout.addWidget(stats_group)

        # ---- Sales Table Group ----
        table_group = QGroupBox("Sales Data")
        table_layout = QVBoxLayout(table_group)
        
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(5) 
        self.sales_table.setHorizontalHeaderLabels(["Sale ID", "Date", "Net Amount", "Total Profit", "Seller"])
        self.sales_table.cellDoubleClicked.connect(self._show_sale_items)
        
        header = self.sales_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        self.sales_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sales_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sales_table.setSelectionMode(QAbstractItemView.SingleSelection) # Only one row at a time
        self.sales_table.setAlternatingRowColors(True)
        
        table_layout.addWidget(self.sales_table)
        main_layout.addWidget(table_group)

        self._load_sales()

    def _load_seller_filter(self):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT user_id, username, role FROM Users ORDER BY username")
        sellers = cur.fetchall()
        conn.close()
        
        self.seller_info = {}
        for user_id, username, role in sellers:
            self.seller_filter.addItem(username)
            self.seller_info[username] = {'user_id': user_id, 'role': role}

    def _get_seller_color(self, username):
        if username not in self.seller_colors:
            import hashlib
            color_hash = hashlib.md5(username.encode()).hexdigest()[:6]
            hue = int(color_hash[:2], 16) % 360
            saturation = 100 + (int(color_hash[2:4], 16) % 50)
            value = 220 + (int(color_hash[4:6], 16) % 35)
            self.seller_colors[username] = QColor.fromHsv(hue, saturation, value)
        return self.seller_colors[username]

    def _load_sales(self):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        seller = self.seller_filter.currentText()
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")

        query = """
            SELECT s.sale_id, s.sale_date, s.net_amount, u.username, 
                   COALESCE(SUM(si.profit), 0) as sale_profit
            FROM Sales s
            JOIN Users u ON s.user_id = u.user_id
            LEFT JOIN Sale_Items si ON s.sale_id = si.sale_id
            WHERE date(s.sale_date) BETWEEN ? AND ?
        """
        params = [start, end]

        if seller != "All Sellers":
            query += " AND u.username = ?"
            params.append(seller)

        query += " GROUP BY s.sale_id ORDER BY s.sale_date DESC"

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()

        self.sales_table.setRowCount(len(rows))
        
        grand_total_revenue = 0.0
        grand_total_profit = 0.0

        for r, (sale_id, date, net, username, profit) in enumerate(rows):
            grand_total_revenue += net
            grand_total_profit += profit

            items = [
                QTableWidgetItem(str(sale_id)),
                QTableWidgetItem(date),
                QTableWidgetItem(f"{net:,.2f}"),
                QTableWidgetItem(f"{profit:,.2f}"),
                QTableWidgetItem(username),
            ]
            
            seller_color = self._get_seller_color(username)

            for c, item in enumerate(items):
                item.setBackground(seller_color)
                if c in [2, 3]: 
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    if c == 3:
                        item.setForeground(QColor("#1e8449") if profit > 0 else QColor("#c0392b"))
                
                self.sales_table.setItem(r, c, item)

        self.total_revenue_label.setText(f"Total Revenue: {grand_total_revenue:,.2f}")
        self.total_profit_label.setText(f"Total Profit: {grand_total_profit:,.2f}")
        
        self.sales_table.resizeColumnsToContents()

    # ==========================================
    #  NEW: RECEIPT PRINTING HANDLER
    # ==========================================
    def _print_selected_receipt(self):
        """Gets selected row, fetches customer name, and generates receipt."""
        selected_rows = self.sales_table.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select a sale transaction from the table first.")
            return

        # Get Sale ID from the first column of the selected row
        row_index = selected_rows[0].row()
        sale_id = self.sales_table.item(row_index, 0).text()

        # We need to fetch the Customer Name specifically for this receipt
        # (It's not in the main table to keep the UI clean)
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("""
                SELECT c.customer_name 
                FROM Sales s
                LEFT JOIN Customers c ON s.customer_id = c.customer_id
                WHERE s.sale_id = ?
            """, (sale_id,))
            result = cur.fetchone()
            conn.close()
            
            # If result is None or name is None, default to "Walk-in"
            customer_name = result[0] if result and result[0] else "Walk-in Customer"

            # Generate filename with timestamp to avoid overwriting
            filename = f"receipt_{sale_id}.pdf"
            
            # Call the function we imported/defined above
            success = generate_sale_receipt(sale_id, filename, customer_name)
            
            if success:
                QMessageBox.information(self, "Receipt Generated", f"✅ Receipt saved as:\n{filename}")
                # Optional: Automatically open the file
                # import os
                # os.startfile(filename) 
            else:
                QMessageBox.warning(self, "Error", "Could not generate receipt.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Database error while fetching receipt details:\n{e}")

    def _show_sale_items(self, row, col):
        sale_id = self.sales_table.item(row, 0).text()
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            SELECT p.product_name, si.quantity_boxes, 
                   si.unit_cost, si.unit_price, si.profit
            FROM Sale_Items si
            JOIN Products p ON si.product_id = p.product_id
            WHERE si.sale_id=?
        """, (sale_id,))
        rows = cur.fetchall()
        conn.close()

        if not rows: return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Profit Analysis - Sale #{sale_id}")
        dialog.setMinimumSize(700, 400)
        layout = QVBoxLayout(dialog)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Product", "Qty", "Box Cost", "Box Sold At", "Total Profit"])
        table.setRowCount(len(rows))
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        total_sale_profit = 0.0

        for r, (name, qty, cost, price, profit) in enumerate(rows):
            total_sale_profit += profit
            table.setItem(r, 0, QTableWidgetItem(name))
            table.setItem(r, 1, QTableWidgetItem(str(qty)))
            table.setItem(r, 2, QTableWidgetItem(f"{cost:,.2f}"))
            table.setItem(r, 3, QTableWidgetItem(f"{price:,.2f}"))
            
            profit_item = QTableWidgetItem(f"{profit:,.2f}")
            profit_item.setForeground(QColor("green") if profit >= 0 else QColor("red"))
            table.setItem(r, 4, profit_item)

        layout.addWidget(table)
        
        footer_lbl = QLabel(f"Total Profit for this Sale: {total_sale_profit:,.2f}")
        footer_lbl.setStyleSheet("font-size: 12pt; font-weight: bold; color: green; margin-top: 10px;")
        footer_lbl.setAlignment(Qt.AlignRight)
        layout.addWidget(footer_lbl)

        dialog.exec_()

    def _ask_date_range(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Date Range")
        layout = QVBoxLayout(dialog)
        
        start = QDateEdit()
        start.setCalendarPopup(True)
        start.setDate(QDate.currentDate().addMonths(-1))
        
        end = QDateEdit()
        end.setCalendarPopup(True)
        end.setDate(QDate.currentDate())
        
        layout.addWidget(QLabel("Start Date:"))
        layout.addWidget(start)
        layout.addWidget(QLabel("End Date:"))
        layout.addWidget(end)
        
        btn = QPushButton("Generate")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        
        if dialog.exec_() == QDialog.Accepted:
            return start.date().toString("yyyy-MM-dd"), end.date().toString("yyyy-MM-dd")
        return None, None

    def _fetch_filtered_sales_rows(self):
        seller = self.seller_filter.currentText()
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        query = """
            SELECT s.sale_id, s.sale_date, s.net_amount, u.username,
                   COALESCE(SUM(si.profit), 0) as sale_profit
            FROM Sales s
            JOIN Users u ON s.user_id = u.user_id
            LEFT JOIN Sale_Items si ON s.sale_id = si.sale_id
            WHERE date(s.sale_date) BETWEEN ? AND ?
        """
        params = [start, end]

        if seller != "All Sellers":
            query += " AND u.username = ?"
            params.append(seller)

        query += " GROUP BY s.sale_id ORDER BY s.sale_date DESC"

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()

        return rows

    def _generate_report(self):
        start_qdate = self.start_date.date()
        end_qdate = self.end_date.date()

        if start_qdate > end_qdate:
            QMessageBox.warning(self, "Invalid Date Range", "Start date cannot be after end date.")
            return

        rows = self._fetch_filtered_sales_rows()
        if not rows:
            QMessageBox.warning(self, "No Data", "No sales found for the selected filters/date range.")
            return

        start = start_qdate.toString("yyyy-MM-dd")
        end = end_qdate.toString("yyyy-MM-dd")
        seller = self.seller_filter.currentText()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Sales_Report_{start}_to_{end}_{timestamp}.pdf"

        try:
            doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
            styles = getSampleStyleSheet()
            title_style = styles["Title"]
            normal = styles["Normal"]

            total_revenue = sum(float(r[2] or 0) for r in rows)
            total_profit = sum(float(r[4] or 0) for r in rows)

            elements = [
                Paragraph("Sales Performance Report", title_style),
                Spacer(1, 8),
                Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal),
                Paragraph(f"Date Range: {start} to {end}", normal),
                Paragraph(f"Seller Filter: {seller}", normal),
                Paragraph(f"Total Bills: {len(rows)}", normal),
                Paragraph(f"Total Revenue: {total_revenue:,.2f}", normal),
                Paragraph(f"Total Profit: {total_profit:,.2f}", normal),
                Spacer(1, 12),
            ]

            table_data = [["Sale ID", "Date", "Net Amount", "Profit", "Seller"]]
            for sale_id, sale_date, net_amount, username, profit in rows:
                table_data.append([
                    str(sale_id),
                    str(sale_date),
                    f"{float(net_amount or 0):,.2f}",
                    f"{float(profit or 0):,.2f}",
                    str(username),
                ])

            table = Table(table_data, colWidths=[60, 150, 100, 90, 120], repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (1, -1), "CENTER"),
                ("ALIGN", (2, 1), (3, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]))

            elements.append(table)
            doc.build(elements)

            QMessageBox.information(self, "Report Generated", f"✅ Sales report generated successfully.\n\nFile: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Failed to generate sales report:\n{e}")

    def _generate_stock_report(self):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                COALESCE(p.product_code, ''),
                COALESCE(SUM(v.current_stock_boxes), 0) AS total_stock,
                COALESCE(MAX(v.box_cost_price), 0) AS latest_cost,
                COALESCE(MAX(v.box_selling_price), 0) AS latest_selling
            FROM Products p
            LEFT JOIN Product_Versions v ON v.product_id = p.product_id
            GROUP BY p.product_id, p.product_name, p.product_code
            ORDER BY p.product_name COLLATE NOCASE
        """
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            QMessageBox.warning(self, "No Data", "No products/stock records found.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Stock_Report_{timestamp}.pdf"

        try:
            doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
            styles = getSampleStyleSheet()
            elements = [
                Paragraph("Current Stock Report", styles["Title"]),
                Spacer(1, 8),
                Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]),
                Paragraph(f"Total Products: {len(rows)}", styles["Normal"]),
                Spacer(1, 12),
            ]

            table_data = [["Product ID", "Code", "Product", "Stock (Boxes)", "Cost", "Selling", "Status"]]
            for product_id, name, code, stock, cost, selling in rows:
                status = "LOW" if float(stock or 0) < 20 else "OK"
                table_data.append([
                    str(product_id),
                    str(code),
                    str(name),
                    f"{float(stock or 0):,.0f}",
                    f"{float(cost or 0):,.2f}",
                    f"{float(selling or 0):,.2f}",
                    status,
                ])

            table = Table(table_data, colWidths=[55, 70, 165, 75, 65, 65, 45], repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (1, -1), "CENTER"),
                ("ALIGN", (3, 1), (5, -1), "RIGHT"),
                ("ALIGN", (6, 1), (6, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ]))

            for index, (_, _, _, stock, _, _) in enumerate(rows, start=1):
                if float(stock or 0) < 20:
                    table.setStyle(TableStyle([
                        ("TEXTCOLOR", (6, index), (6, index), colors.red),
                        ("FONTNAME", (6, index), (6, index), "Helvetica-Bold"),
                    ]))

            elements.append(table)
            doc.build(elements)

            QMessageBox.information(self, "Stock Report Generated", f"✅ Stock report generated successfully.\n\nFile: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Report Error", f"Failed to generate stock report:\n{e}")