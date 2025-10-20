import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QSpinBox, QCheckBox, QMessageBox, QFormLayout, QFileDialog,
    QGroupBox, QFrame, QHeaderView, QInputDialog
)
from PyQt5.QtCore import Qt
from Backend_Logic.Sales import create_sale, create_receipt
from session import current_user

DB_NAME = "POS.db"


class SalesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sales Management")
        self.setGeometry(200, 100, 800, 650)
        
        self.setStyleSheet("""
            QWidget {
                font-family: Segoe UI, Arial;
            }
            QLabel {
                font-size: 10pt;
                color: #2c3e50;
            }
            QLineEdit, QComboBox, QSpinBox {
                font-size: 10pt;
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
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
            QCheckBox {
                spacing: 8px;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title = QLabel("💰 Sales Management")
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
        layout.addWidget(title)

        # 🔹 Salesperson Selection
        salesperson_group = QGroupBox("Sales Information")
        salesperson_layout = QFormLayout(salesperson_group)
        salesperson_layout.setLabelAlignment(Qt.AlignRight)
        salesperson_layout.setVerticalSpacing(10)
        
        self.salesperson_dropdown = QComboBox()
        self.load_salespersons()
        salesperson_layout.addRow("Salesperson *:", self.salesperson_dropdown)
        layout.addWidget(salesperson_group)

        # --- Product Selection Group ---
        product_group = QGroupBox("Add Products to Cart")
        product_layout = QVBoxLayout(product_group)
        
        # Product selection row
        selection_layout = QHBoxLayout()
        self.product_dropdown = QComboBox()
        self.product_dropdown.setEditable(True)
        self.product_dropdown.setInsertPolicy(QComboBox.NoInsert)
        self.load_products()
        self.product_dropdown.currentIndexChanged.connect(self.update_price_field)

        self.qty_input = QSpinBox()
        self.qty_input.setMinimum(1)
        self.qty_input.setMaximum(1000)
        self.unit_price_input = QLineEdit()
        self.unit_price_input.setPlaceholderText("Auto-filled from product")

        add_btn = QPushButton("➕ Add to Cart")
        add_btn.setStyleSheet("background-color: #27ae60;")
        add_btn.clicked.connect(self.add_to_cart)

        selection_layout.addWidget(QLabel("Product:"), 1)
        selection_layout.addWidget(self.product_dropdown, 3)
        selection_layout.addWidget(QLabel("Qty (boxes):"), 1)
        selection_layout.addWidget(self.qty_input, 1)
        selection_layout.addWidget(QLabel("Selling Price:"), 1)
        selection_layout.addWidget(self.unit_price_input, 2)
        selection_layout.addWidget(add_btn, 2)

        product_layout.addLayout(selection_layout)
        layout.addWidget(product_group)

        # --- Cart Group ---
        cart_group = QGroupBox("🛒 Shopping Cart")
        cart_layout = QVBoxLayout(cart_group)
        
        self.cart_table = QTableWidget(0, 4)
        self.cart_table.setHorizontalHeaderLabels(["Product", "Qty", "Unit Price", "Total Price"])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cart_table.itemChanged.connect(self.update_price_on_qty_change)
        
        cart_layout.addWidget(self.cart_table)

        # Remove button
        remove_btn = QPushButton("❌ Remove Selected Item")
        remove_btn.setStyleSheet("background-color: #e74c3c;")
        remove_btn.clicked.connect(self.remove_selected_item)
        cart_layout.addWidget(remove_btn)

        layout.addWidget(cart_group)

        # --- Payment Options Group ---
        payment_group = QGroupBox("Payment Options")
        payment_layout = QVBoxLayout(payment_group)
        
        # Discount row
        discount_layout = QHBoxLayout()
        self.discount_input = QLineEdit()
        self.discount_input.setPlaceholderText("0.00")
        discount_layout.addWidget(QLabel("Discount Amount:"))
        discount_layout.addWidget(self.discount_input)
        discount_layout.addStretch()
        
        # Credit checkbox
        self.credit_checkbox = QCheckBox("On Credit Sale")
        self.credit_checkbox.setStyleSheet("color: #e67e22;")
        self.credit_checkbox.stateChanged.connect(self.toggle_credit_fields)
        discount_layout.addWidget(self.credit_checkbox)
        
        payment_layout.addLayout(discount_layout)
        layout.addWidget(payment_group)

        # --- Customer Details (hidden unless credit) ---
        self.customer_group = QGroupBox("Customer Information (For Credit Sales)")
        customer_form = QFormLayout(self.customer_group)
        customer_form.setLabelAlignment(Qt.AlignRight)
        customer_form.setVerticalSpacing(10)
        
        self.customer_name = QLineEdit()
        self.customer_phone = QLineEdit()
        self.customer_address = QLineEdit()
        
        self.customer_name.setPlaceholderText("Required for credit sales")
        self.customer_phone.setPlaceholderText("Optional")
        self.customer_address.setPlaceholderText("Optional")
        
        customer_form.addRow("Customer Name *:", self.customer_name)
        customer_form.addRow("Phone:", self.customer_phone)
        customer_form.addRow("Address:", self.customer_address)
        
        self.customer_group.setVisible(False)
        layout.addWidget(self.customer_group)

        # --- Submit button ---
        submit_container = QHBoxLayout()
        submit_btn = QPushButton("✅ Complete Sale & Generate Receipt")
        submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                font-size: 12pt;
                padding: 12px 20px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        submit_btn.clicked.connect(self.complete_sale)
        submit_container.addWidget(submit_btn)
        submit_container.setAlignment(Qt.AlignCenter)
        layout.addLayout(submit_container)

        layout.addStretch()
        self.setLayout(layout)

    def update_price_on_qty_change(self, item):
        """When quantity changes, recalculate total selling price for that row."""
        row = item.row()
        col = item.column()

        # Ensure we only react to quantity column edits
        if col != 1:
            return

        try:
            qty = int(item.text())
            if qty <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Quantity", "Quantity must be a positive integer.")
            self.cart_table.blockSignals(True)
            # revert to 1 if invalid
            self.cart_table.setItem(row, 1, QTableWidgetItem("1"))
            self.cart_table.blockSignals(False)
            qty = 1

        # Find product and its unit price
        product_name = self.cart_table.item(row, 0).text()
        unit_price_item = self.cart_table.item(row, 2)
        if unit_price_item:
            try:
                unit_price = float(unit_price_item.text())
                new_total = unit_price * qty
                self.cart_table.blockSignals(True)
                self.cart_table.setItem(row, 3, QTableWidgetItem(f"{new_total:.2f}"))
                self.cart_table.blockSignals(False)
            except ValueError:
                pass

    # ----------------- Helpers -----------------
    def load_salespersons(self):
        """Load all salespersons (users) from DB"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT user_id, username FROM Users")
        users = cur.fetchall()
        conn.close()

        self.salesperson_dropdown.clear()
        for uid, uname in users:
            self.salesperson_dropdown.addItem(uname, uid)

        # Default select current user
        index = self.salesperson_dropdown.findData(current_user["user_id"])
        if index >= 0:
            self.salesperson_dropdown.setCurrentIndex(index)

    def load_products(self):
        """Fetch products with their latest version's selling price"""
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                p.product_id, 
                p.product_name,
                v.box_selling_price
            FROM Products p
            JOIN Product_Versions v 
                ON v.product_id = p.product_id
            WHERE v.version_id = (
                SELECT MAX(version_id) 
                FROM Product_Versions 
                WHERE product_id = p.product_id
            )
            ORDER BY p.product_name
        """)

        self.products = cur.fetchall()
        conn.close()

        self.product_dropdown.clear()
        self.product_dropdown.addItem("", -1)
        for pid, name, price in self.products:
            display_text = f"{name} - ${price:.2f}" if price else name
            self.product_dropdown.addItem(display_text, pid)

    def update_price_field(self):
        """Auto-fill selling price when product selected"""
        index = self.product_dropdown.currentIndex()
        if index <= 0:
            self.unit_price_input.clear()
            return
        product_id = self.product_dropdown.itemData(index)
        for pid, name, price in self.products:
            if pid == product_id:
                self.unit_price_input.setText(f"{price:.2f}")
                break

    def remove_selected_item(self):
        selected = self.cart_table.currentRow()
        if selected >= 0:
            self.cart_table.removeRow(selected)
        else:
            QMessageBox.warning(self, "No Selection", "Please select an item to remove.")

    def add_to_cart(self):
        index = self.product_dropdown.currentIndex()
        if index <= 0:
            QMessageBox.warning(self, "Error", "Please select a valid product")
            return

        product_name = self.product_dropdown.currentText().split(' - ')[0]  # Remove price from display
        product_id = self.product_dropdown.currentData()
        qty = self.qty_input.value()

        try:
            unit_price = float(self.unit_price_input.text())
        except ValueError:
            QMessageBox.warning(self, "Error", "Enter a valid selling price")
            return

        total_price = unit_price * qty

        row = self.cart_table.rowCount()
        self.cart_table.insertRow(row)
        
        # Product name
        self.cart_table.setItem(row, 0, QTableWidgetItem(product_name))
        
        # Quantity (editable)
        qty_item = QTableWidgetItem(str(qty))
        qty_item.setFlags(qty_item.flags() | Qt.ItemIsEditable)
        self.cart_table.setItem(row, 1, qty_item)
        
        # Unit price
        unit_item = QTableWidgetItem(f"{unit_price:.2f}")
        unit_item.setFlags(unit_item.flags() & ~Qt.ItemIsEditable)  # Not editable
        self.cart_table.setItem(row, 2, unit_item)
        
        # Total price
        total_item = QTableWidgetItem(f"{total_price:.2f}")
        total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)  # Not editable
        self.cart_table.setItem(row, 3, total_item)

        # ✅ Clear product selection and fields automatically
        self.product_dropdown.setCurrentIndex(0)
        self.product_dropdown.lineEdit().clear()
        self.qty_input.setValue(1)
        self.unit_price_input.clear()

    def toggle_credit_fields(self, state):
        self.customer_group.setVisible(state == Qt.Checked)

    def complete_sale(self):
        """Finalize sale, update DB, and auto-generate receipt with customer name."""
        if self.cart_table.rowCount() == 0:
            QMessageBox.warning(self, "Empty Cart", "Please add items to the cart before completing sale.")
            return

        salesperson_id = self.salesperson_dropdown.currentData()
        items = []

        for row in range(self.cart_table.rowCount()):
            product_name = self.cart_table.item(row, 0).text()
            product_id = next((pid for pid, name, _ in self.products if name == product_name), None)
            qty = int(self.cart_table.item(row, 1).text())
            unit_price = float(self.cart_table.item(row, 2).text())
            if product_id:
                items.append((product_id, qty, unit_price))

        try:
            discount = float(self.discount_input.text()) if self.discount_input.text() else 0
        except ValueError:
            discount = 0

        on_credit = self.credit_checkbox.isChecked()
        customer = None

        result = create_sale(salesperson_id, items, customer, discount, on_credit)
        if result:
            sale_id = result["sale_id"]

            # --- Ask customer name directly ---
            customer_name, ok = QInputDialog.getText(
                self,
                "Customer Name",
                "Enter Customer Name for Receipt:",
            )

            if not ok or not customer_name.strip():
                customer_name = "Unknown"

            # Sanitize filename
            safe_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
            filename = f"receipt_{sale_id}_{safe_name}.pdf"

            # --- Auto-generate receipt ---
            create_receipt(sale_id, filename)

            # --- Optional small info notice ---
            QMessageBox.information(self, "Sale Completed", f"Receipt generated: {filename}")

            # --- Clear form ---
            self.cart_table.setRowCount(0)
            self.discount_input.clear()
            self.credit_checkbox.setChecked(False)
            self.customer_name.clear()
            self.customer_phone.clear()
            self.customer_address.clear()

        else:
            QMessageBox.critical(self, "Error", "Failed to complete sale")
