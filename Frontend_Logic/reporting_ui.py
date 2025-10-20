import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QTableWidget, QTableWidgetItem,
    QDialog, QComboBox, QDateEdit, QGroupBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QHeaderView


DB_NAME = "POS.db"


class ReportingUI(QWidget):
    def __init__(self, submodule=None, parent=None):
        super().__init__(parent)
        self.seller_colors = {}
        
        self.setStyleSheet("""
            QWidget {
                font-family: Segoe UI, Arial;
            }
            QLabel {
                font-size: 10pt;
                color: #2c3e50;
            }
            QPushButton {
                font-size: 10pt;
                padding: 8px 12px;
                border: none;
                border-radius: 4px;
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QTableWidget {
                font-size: 9pt;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
                gridline-color: #ecf0f1;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 6px;
                font-weight: bold;
                border: none;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2c3e50;
            }
            QComboBox, QDateEdit {
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title = QLabel("📊 Sales Reporting & Analytics")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 22px; 
            font-weight: bold; 
            color: #2c3e50;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 6px;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(title)

        # ---- Filters Group ----
        filters_group = QGroupBox("Report Filters")
        filters_layout = QHBoxLayout(filters_group)
        filters_layout.setSpacing(15)

        # Seller filter
        seller_container = QVBoxLayout()
        seller_container.setSpacing(5)
        seller_container.addWidget(QLabel("Seller:"))
        self.seller_filter = QComboBox()
        self.seller_filter.addItem("All Sellers")
        self._load_seller_filter()
        self.seller_filter.currentIndexChanged.connect(self._load_sales)
        seller_container.addWidget(self.seller_filter)

        # Date filters
        date_container = QVBoxLayout()
        date_container.setSpacing(5)
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

        # ---- Actions Group ----
        actions_group = QGroupBox("Report Actions")
        actions_layout = QHBoxLayout(actions_group)
        
        # Report buttons
        btn_report = QPushButton("📄 Generate Sales Report")
        btn_report.setStyleSheet("background-color: #9b59b6;")
        btn_report.clicked.connect(self._generate_report)

        btn_stock_report = QPushButton("📦 Stock Purchase Report")
        btn_stock_report.setStyleSheet("background-color: #e67e22;")
        btn_stock_report.clicked.connect(self._generate_stock_report)

        # Total label
        self.total_label = QLabel("Total Sales: 0.00")
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 12pt; 
            color: #27ae60;
            background-color: #e8f6f3;
            padding: 8px 12px;
            border-radius: 4px;
        """)

        actions_layout.addWidget(btn_report)
        actions_layout.addWidget(btn_stock_report)
        actions_layout.addWidget(self.total_label)

        main_layout.addWidget(actions_group)

        # ---- Sales Table Group ----
        table_group = QGroupBox("Sales Data")
        table_layout = QVBoxLayout(table_group)
        
        self.sales_table = QTableWidget()
        self.sales_table.setColumnCount(4)
        self.sales_table.setHorizontalHeaderLabels(["Sale ID", "Date", "Net Amount", "Seller"])
        self.sales_table.cellDoubleClicked.connect(self._show_sale_items)
        
        # Set fixed column sizing to prevent shrinking
        header = self.sales_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Sale ID - auto size
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Date - auto size
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Net Amount - auto size
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Seller - stretch to fill space
        
        self.sales_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sales_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.sales_table.setAlternatingRowColors(True)
        self.sales_table.setMinimumHeight(400)

        table_layout.addWidget(self.sales_table)
        main_layout.addWidget(table_group)

        self._load_sales()

    def _load_seller_filter(self):
        """Populate seller dropdown with all users regardless of role."""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT user_id, username, role FROM Users ORDER BY username")
        sellers = cur.fetchall()
        conn.close()
        
        # Store seller info for color coding
        self.seller_info = {}
        for user_id, username, role in sellers:
            self.seller_filter.addItem(username)
            self.seller_info[username] = {'user_id': user_id, 'role': role}

    def _get_seller_color(self, username):
        """Get consistent color for each seller based on their username."""
        if username not in self.seller_colors:
            # Generate a consistent color based on username hash
            import hashlib
            color_hash = hashlib.md5(username.encode()).hexdigest()[:6]
            # Convert to HSV for better color distribution
            hue = int(color_hash[:2], 16) % 360
            saturation = 150 + (int(color_hash[2:4], 16) % 50)  # 150-200
            value = 200 + (int(color_hash[4:6], 16) % 55)  # 200-255
            self.seller_colors[username] = QColor.fromHsv(hue, saturation, value)
        return self.seller_colors[username]

    def _load_sales(self):
        """Load sales filtered by seller and date range, sorted by seller name."""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        seller = self.seller_filter.currentText()
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")

        query = """
            SELECT s.sale_id, s.sale_date, s.net_amount, u.username AS salesperson
            FROM Sales s
            JOIN Users u ON s.user_id = u.user_id
            WHERE date(s.sale_date) BETWEEN ? AND ?
        """
        params = [start, end]

        if seller != "All Sellers":
            query += " AND u.username = ?"
            params.append(seller)

        # Sort by seller name first, then by sale date (newest first for each seller)
        query += " ORDER BY u.username ASC, s.sale_date DESC"

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        conn.close()

        self.sales_table.setRowCount(len(rows))
        total_sales = 0.0

        for r, (sale_id, date, net, username) in enumerate(rows):
            total_sales += net
            items = [
                QTableWidgetItem(str(sale_id)),
                QTableWidgetItem(date),
                QTableWidgetItem(f"{net:,.2f}"),  # Format with commas
                QTableWidgetItem(username),
            ]
            
            for c, item in enumerate(items):
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                if c == 2:  # Amount column - right align
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.sales_table.setItem(r, c, item)

            # Color coding by seller - each seller gets unique color
            seller_color = self._get_seller_color(username)
            for c in range(4):
                self.sales_table.item(r, c).setBackground(seller_color.lighter(160))
                # Set text color for better contrast on light backgrounds
                self.sales_table.item(r, c).setForeground(QColor("#2c3e50"))

        self.total_label.setText(f"Total Sales: {total_sales:,.2f}")
        
        # Ensure columns maintain proper width
        self.sales_table.resizeColumnsToContents()
        
        # Set minimum widths to prevent excessive shrinking
        self.sales_table.setColumnWidth(0, 80)   # Sale ID
        self.sales_table.setColumnWidth(1, 120)  # Date
        self.sales_table.setColumnWidth(2, 120)  # Net Amount

    def _show_sale_items(self, row, col):
        """Popup with sale items when a sale is clicked."""
        sale_id = self.sales_table.item(row, 0).text()
        sale_date = self.sales_table.item(row, 1).text()
        seller = self.sales_table.item(row, 3).text()

        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            SELECT p.product_name, si.quantity_boxes, si.unit_price, si.total_price
            FROM Sale_Items si
            JOIN Products p ON si.product_id = p.product_id
            WHERE si.sale_id=?
        """, (sale_id,))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            QMessageBox.information(self, "No Items", "No items found for this sale.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Sale Details - #{sale_id}")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout(dialog)

        # Header info
        header_info = QLabel(f"Sale #{sale_id} • {sale_date} • {seller}")
        header_info.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 8px;")
        layout.addWidget(header_info)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Product", "Qty (Boxes)", "Unit Price", "Total"])
        table.setRowCount(len(rows))
        
        # Set proper column resizing for items table
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Product name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Qty
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Unit Price
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Total
        
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)

        total_sale_amount = 0.0
        for r, (name, qty, price, total) in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(name))
            table.setItem(r, 1, QTableWidgetItem(str(qty)))
            table.setItem(r, 2, QTableWidgetItem(f"{price:.2f}"))
            table.setItem(r, 3, QTableWidgetItem(f"{total:.2f}"))
            total_sale_amount += total

        layout.addWidget(table)

        # Footer with total
        footer = QLabel(f"Sale Total: {total_sale_amount:,.2f}")
        footer.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 8px; background-color: #e8f6f3;")
        footer.setAlignment(Qt.AlignRight)
        layout.addWidget(footer)

        dialog.exec_()

    def _ask_date_range(self):
        """Popup dialog to ask for start and end date before generating report."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Date Range for Report")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog)

        # Date inputs
        form_layout = QVBoxLayout()
        
        start_container = QHBoxLayout()
        start_container.addWidget(QLabel("Start Date:"))
        start = QDateEdit()
        start.setCalendarPopup(True)
        start.setDate(QDate.currentDate().addMonths(-1))
        start.setMaximumDate(QDate.currentDate())
        start_container.addWidget(start)
        form_layout.addLayout(start_container)

        end_container = QHBoxLayout()
        end_container.addWidget(QLabel("End Date:"))
        end = QDateEdit()
        end.setCalendarPopup(True)
        end.setDate(QDate.currentDate())
        end.setMaximumDate(QDate.currentDate())
        end_container.addWidget(end)
        form_layout.addLayout(end_container)

        layout.addLayout(form_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("📊 Generate Report")
        btn_ok.setStyleSheet("background-color: #27ae60;")
        btn_ok.clicked.connect(dialog.accept)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("background-color: #95a5a6;")
        btn_cancel.clicked.connect(dialog.reject)

        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        if dialog.exec_() == QDialog.Accepted:
            return start.date().toString("yyyy-MM-dd"), end.date().toString("yyyy-MM-dd")
        return None, None

    def _generate_report(self):
        """Generate Sales Report (PDF) including product-wise summary."""
        start, end = self._ask_date_range()
        if not start or not end:
            return

        seller = self.seller_filter.currentText()

        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()

            # --- Fetch Sale Records ---
            query = """
                SELECT s.sale_id, s.sale_date, s.net_amount, u.username AS salesperson
                FROM Sales s
                JOIN Users u ON s.user_id = u.user_id
                WHERE date(s.sale_date) BETWEEN ? AND ?
            """
            params = [start, end]

            if seller != "All Sellers":
                query += " AND u.username = ?"
                params.append(seller)

            query += " ORDER BY s.sale_date DESC"
            cur.execute(query, tuple(params))
            sales_rows = cur.fetchall()

            if not sales_rows:
                QMessageBox.information(self, "No Data",
                                        f"No sales found for {seller} from {start} → {end}.")
                conn.close()
                return

            # --- Fetch Product Summary ---
            product_query = """
                SELECT p.product_name, SUM(si.quantity_boxes) AS total_qty, SUM(si.total_price) AS total_value
                FROM Sale_Items si
                JOIN Products p ON si.product_id = p.product_id
                JOIN Sales s ON si.sale_id = s.sale_id
                JOIN Users u ON s.user_id = u.user_id
                WHERE date(s.sale_date) BETWEEN ? AND ?
            """
            prod_params = [start, end]

            if seller != "All Sellers":
                product_query += " AND u.username = ?"
                prod_params.append(seller)

            product_query += " GROUP BY p.product_name ORDER BY total_qty DESC"
            cur.execute(product_query, tuple(prod_params))
            product_rows = cur.fetchall()
            conn.close()

            # --- Generate PDF ---
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            filename = f"sales_report_{seller.replace(' ', '_')}_{start}_to_{end}.pdf"
            c = canvas.Canvas(filename, pagesize=A4)
            width, height = A4
            y = height - 40

            # ---- Header ----
            c.setFont("Helvetica-Bold", 14)
            c.drawString(220, y, "Sales Report")
            y -= 25
            c.setFont("Helvetica", 10)
            c.drawString(50, y, f"Date Range: {start} → {end}")
            y -= 15
            c.drawString(50, y, f"Seller: {seller}" if seller != "All Sellers" else "Seller: All")
            y -= 15
            c.drawString(50, y, f"Generated by POS System")
            y -= 20
            c.line(50, y, width - 50, y)
            y -= 20

            # ---- Sales Table ----
            c.setFont("Helvetica-Bold", 9)
            c.drawString(50, y, "Sale ID")
            c.drawString(110, y, "Date")
            c.drawString(220, y, "Seller")
            c.drawString(340, y, "Net Amount")
            y -= 15
            c.line(50, y, width - 50, y)
            y -= 10

            c.setFont("Helvetica", 9)
            total_sales = 0.0
            for sale_id, date, net, username in sales_rows:
                c.drawString(50, y, str(sale_id))
                c.drawString(110, y, date)
                c.drawString(220, y, username[:15])
                c.drawRightString(420, y, f"{net:.2f}")
                y -= 12
                total_sales += net
                if y < 100:
                    c.showPage()
                    c.setFont("Helvetica", 9)
                    y = height - 60

            # ---- Total ----
            y -= 10
            c.line(50, y, width - 50, y)
            y -= 15
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, f"Total Sales: {total_sales:.2f}")
            y -= 25

            # ---- Product Summary ----
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Product Summary")
            y -= 15
            c.line(50, y, width - 50, y)
            y -= 20
            c.setFont("Helvetica-Bold", 9)
            c.drawString(50, y, "Product Name")
            c.drawString(250, y, "Total Qty")
            c.drawString(340, y, "Total Value")
            y -= 15
            c.line(50, y, width - 50, y)
            y -= 10

            c.setFont("Helvetica", 9)
            total_qty_all = 0
            total_value_all = 0.0
            for name, qty, value in product_rows:
                c.drawString(50, y, name[:28])
                c.drawRightString(290, y, str(int(qty)))
                c.drawRightString(420, y, f"{value:.2f}")
                y -= 12
                total_qty_all += qty
                total_value_all += value

                if y < 80:
                    c.showPage()
                    y = height - 60
                    c.setFont("Helvetica", 9)

            # ---- Product Totals ----
            y -= 10
            c.line(50, y, width - 50, y)
            y -= 15
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, f"Total Products Sold: {int(total_qty_all)}")
            c.drawRightString(420, y, f"Total Value: {total_value_all:.2f}")

            # ---- Save File ----
            c.save()
            QMessageBox.information(
                self,
                "Report Generated",
                f"✅ Sales Report with Product Summary saved as {filename}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate sales report:\n{e}")

    def _generate_stock_report(self):
        """Generate a Stock Purchase Report (PDF) after asking date range."""
        start, end = self._ask_date_range()
        if not start or not end:
            return

        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("""
                SELECT p.product_name, sp.quantity_added, sp.purchase_price, 
                    sp.purchase_date, sp.supplier_name, sp.notes,
                    pv.current_stock_boxes
                FROM StockPurchases sp
                JOIN Products p ON sp.product_id = p.product_id
                JOIN Product_Versions pv ON sp.version_id = pv.version_id
                WHERE date(sp.purchase_date) BETWEEN ? AND ?
                ORDER BY sp.purchase_date DESC
            """, (start, end))
            rows = cur.fetchall()
            conn.close()

            if not rows:
                QMessageBox.information(self, "No Data", f"No stock purchases found from {start} → {end}.")
                return

            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            filename = "stock_purchase_report.pdf"
            c = canvas.Canvas(filename, pagesize=A4)
            width, height = A4
            y = height - 40
            c.setFont("Helvetica-Bold", 14)
            c.drawString(200, y, "Stock Purchase Report")
            y -= 25
            c.setFont("Helvetica", 10)
            c.drawString(50, y, f"Date Range: {start} → {end}")
            y -= 15
            c.drawString(50, y, f"Generated by POS System")
            y -= 20
            c.line(50, y, width - 50, y)
            y -= 20

            c.setFont("Helvetica-Bold", 9)
            c.drawString(50, y, "Product")
            c.drawString(150, y, "Qty")
            c.drawString(190, y, "Cost/Box")
            c.drawString(250, y, "Remaining")
            c.drawString(320, y, "Supplier")
            c.drawString(420, y, "Date")
            y -= 15
            c.line(50, y, width - 50, y)
            y -= 10

            c.setFont("Helvetica", 9)
            total_qty = 0
            total_cost = 0

            for product, qty, price, date, supplier, notes, remaining in rows:
                c.drawString(50, y, product[:18])
                c.drawString(150, y, str(qty))
                c.drawString(190, y, f"{price:.2f}")
                c.drawString(250, y, str(remaining))
                c.drawString(320, y, supplier[:15])
                c.drawString(420, y, date)
                y -= 12
                if notes:
                    c.setFont("Helvetica-Oblique", 8)
                    c.drawString(60, y, f"Note: {notes[:70]}")
                    c.setFont("Helvetica", 9)
                    y -= 10

                total_qty += qty
                total_cost += qty * price

                if y < 80:
                    c.showPage()
                    c.setFont("Helvetica", 9)
                    y = height - 60

            y -= 10
            c.line(50, y, width - 50, y)
            y -= 15
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y, f"Total Boxes Purchased: {total_qty}")
            y -= 15
            c.drawString(50, y, f"Total Purchase Cost: {total_cost:.2f}")
            c.save()

            QMessageBox.information(self, "Report Generated",
                                    f"✅ Stock Purchase Report saved as {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate stock report:\n{e}")