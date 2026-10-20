import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QSpinBox, QCheckBox, QMessageBox, QFormLayout, QInputDialog,
    QGroupBox, QHeaderView, QCompleter, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt
from Backend_Logic.Sales import create_sale, create_receipt, fetch_sale_for_edit, update_sale
from session import current_user

DB_NAME = "POS.db"

# --- CUSTOM SEARCHABLE COMBOBOX ---
class SearchableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        
        self.comp = QCompleter(self)
        self.comp.setCompletionMode(QCompleter.PopupCompletion)
        self.comp.setFilterMode(Qt.MatchContains)
        self.comp.setCaseSensitivity(Qt.CaseInsensitive)
        
        self.setCompleter(self.comp)

    def addItem(self, text, userData=None):
        super().addItem(text, userData)
        self.comp.setModel(self.model())

# --- MAIN SALES WINDOW ---
class SalesWindow(QWidget):
    
    # 1. STATIC VARIABLE FOR PERSISTENCE
    # This dictionary sits outside __init__, so it survives when the page changes.
    saved_state = {
        "cart": [],            # List of (Product Name, Qty, Unit Price, Total)
        "customer_name": "",
        "customer_phone": "",
        "customer_address": "",
        "discount": "",
        "paid_now": "",
        "is_credit": False,
        "salesperson_idx": -1
    }

    def __init__(self):
        super().__init__()
        self.editing_sale_id = None
        self.setWindowTitle("Sales Management")
        self.setGeometry(200, 100, 900, 750) 
        
        self.setStyleSheet("""
            QWidget { font-family: Segoe UI, Arial; }
            QLabel { font-size: 10pt; color: #2c3e50; }
            QLineEdit, QComboBox, QSpinBox {
                font-size: 10pt; padding: 6px; border: 1px solid #bdc3c7; border-radius: 4px; background-color: white;
            }
            QPushButton {
                font-size: 10pt; padding: 8px 12px; border: none; border-radius: 4px;
                background-color: #3498db; color: white; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QTableWidget { font-size: 9pt; border: 1px solid #bdc3c7; background-color: white; }
            QHeaderView::section { background-color: #34495e; color: white; padding: 6px; font-weight: bold; border: none; }
            QGroupBox { font-weight: bold; font-size: 11pt; border: 1px solid #bdc3c7; border-radius: 6px; margin-top: 10px; padding-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #2c3e50; }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title = QLabel("💰 Sales Management")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50; padding: 10px; background-color: #ecf0f1; border-radius: 6px; margin-bottom: 5px;")
        layout.addWidget(title)

        # 🔹 Salesperson Selection
        salesperson_group = QGroupBox("Sales Information")
        salesperson_layout = QFormLayout(salesperson_group)
        self.salesperson_dropdown = QComboBox()
        self.load_salespersons()
        # Save state when changed
        self.salesperson_dropdown.currentIndexChanged.connect(self.save_state) 
        salesperson_layout.addRow("Salesperson *:", self.salesperson_dropdown)

        self.edit_bill_btn = QPushButton("✏️ Edit Existing Bill")
        self.edit_bill_btn.setStyleSheet("background-color: #f39c12;")
        self.edit_bill_btn.clicked.connect(self.start_edit_bill)
        salesperson_layout.addRow("", self.edit_bill_btn)
        layout.addWidget(salesperson_group)

        # --- Product Selection Group ---
        product_group = QGroupBox("Add Products to Cart")
        product_layout = QVBoxLayout(product_group)
        
        selection_layout = QHBoxLayout()
        
        self.product_dropdown = SearchableComboBox() 
        self.load_products()
        self.product_dropdown.currentIndexChanged.connect(self.update_price_field)

        self.qty_input = QSpinBox()
        self.qty_input.setMinimum(1)
        self.qty_input.setMaximum(9999) 
        
        self.unit_price_input = QLineEdit()
        self.unit_price_input.setPlaceholderText("Auto-filled")

        add_btn = QPushButton("➕ Add to Cart")
        add_btn.setStyleSheet("background-color: #27ae60;")
        add_btn.clicked.connect(self.add_to_cart)

        selection_layout.addWidget(QLabel("Product:"), 1)
        selection_layout.addWidget(self.product_dropdown, 3)
        selection_layout.addWidget(QLabel("Qty:"), 1)
        selection_layout.addWidget(self.qty_input, 1)
        selection_layout.addWidget(QLabel("Price:"), 1)
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
        self.cart_table.itemChanged.connect(self.update_price_on_qty_change) # This handles totals and saving
        
        cart_layout.addWidget(self.cart_table)

        # 2. GRAND TOTAL DISPLAY
        self.total_display_label = QLabel("Grand Total: 0.00")
        self.total_display_label.setAlignment(Qt.AlignRight)
        self.total_display_label.setStyleSheet("font-size: 18pt; font-weight: bold; color: #c0392b; padding: 10px;")
        cart_layout.addWidget(self.total_display_label)

        remove_btn = QPushButton("❌ Remove Selected Item")
        remove_btn.setStyleSheet("background-color: #e74c3c;")
        remove_btn.clicked.connect(self.remove_selected_item)
        cart_layout.addWidget(remove_btn)
        layout.addWidget(cart_group)

        # --- Payment Options Group ---
        payment_group = QGroupBox("Payment Options")
        payment_layout = QVBoxLayout(payment_group)
        
        row1 = QHBoxLayout()
        self.discount_input = QLineEdit()
        self.discount_input.setPlaceholderText("0.00")
        self.discount_input.textChanged.connect(self.calculate_grand_total) # Recalc and Save on type
        
        self.credit_checkbox = QCheckBox("On Credit / Partial Payment")
        self.credit_checkbox.setStyleSheet("color: #e67e22; font-weight: bold;")
        self.credit_checkbox.stateChanged.connect(self.toggle_credit_fields)
        self.credit_checkbox.stateChanged.connect(self.save_state)
        
        row1.addWidget(QLabel("Discount Amount:"))
        row1.addWidget(self.discount_input)
        row1.addStretch()
        row1.addWidget(self.credit_checkbox)
        payment_layout.addLayout(row1)
        
        self.credit_details_widget = QWidget()
        credit_form = QFormLayout(self.credit_details_widget)
        credit_form.setLabelAlignment(Qt.AlignRight)
        
        self.customer_name = QLineEdit()
        self.customer_name.textChanged.connect(self.save_state)
        
        self.customer_phone = QLineEdit()
        self.customer_phone.textChanged.connect(self.save_state)
        
        self.customer_address = QLineEdit()
        self.customer_address.textChanged.connect(self.save_state)
        
        self.paid_now_input = QLineEdit()
        self.paid_now_input.setPlaceholderText("Amount paying right now (0 for full credit)")
        self.paid_now_input.textChanged.connect(self.save_state)
        
        credit_form.addRow("Customer Name *:", self.customer_name)
        credit_form.addRow("Phone:", self.customer_phone)
        credit_form.addRow("Address:", self.customer_address)
        credit_form.addRow("Paid Now (Cash):", self.paid_now_input)
        
        self.credit_details_widget.setVisible(False)
        payment_layout.addWidget(self.credit_details_widget)
        
        layout.addWidget(payment_group)

        # --- Submit button ---
        submit_container = QHBoxLayout()
        submit_btn = QPushButton("✅ Complete Sale")
        submit_btn.setStyleSheet("background-color: #9b59b6; font-size: 12pt; padding: 12px 20px;")
        submit_btn.clicked.connect(self.complete_sale)
        self.submit_btn = submit_btn
        submit_container.addWidget(submit_btn)
        submit_container.setAlignment(Qt.AlignCenter)
        layout.addLayout(submit_container)

        layout.addStretch()

        # Put the page in a scroll area so it scrolls instead of growing past the screen
        content = QWidget()
        content.setLayout(layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # RESTORE DATA ON LOAD
        self.restore_state()

    # ----------------- Persistence Logic -----------------

    def save_state(self):
        """Saves the current UI state to the static class variable."""
        cart_data = []
        for row in range(self.cart_table.rowCount()):
            p_name = self.cart_table.item(row, 0).text()
            qty = self.cart_table.item(row, 1).text()
            price = self.cart_table.item(row, 2).text()
            total = self.cart_table.item(row, 3).text()
            pid = self.cart_table.item(row, 0).data(Qt.UserRole)
            cart_data.append((pid, p_name, qty, price, total))

        SalesWindow.saved_state = {
            "cart": cart_data,
            "customer_name": self.customer_name.text(),
            "customer_phone": self.customer_phone.text(),
            "customer_address": self.customer_address.text(),
            "discount": self.discount_input.text(),
            "paid_now": self.paid_now_input.text(),
            "is_credit": self.credit_checkbox.isChecked(),
            "salesperson_idx": self.salesperson_dropdown.currentIndex()
        }

    def restore_state(self):
        """Restores data from the static variable to the UI."""
        state = SalesWindow.saved_state
        
        # Restore Cart
        self.cart_table.blockSignals(True) # Prevent triggering calculations during load
        self.cart_table.setRowCount(0)
        for r_idx, row_data in enumerate(state["cart"]):
            if len(row_data) == 5:
                pid, p_name, qty, price, total = row_data
            else:
                pid = None
                p_name, qty, price, total = row_data

            self.cart_table.insertRow(r_idx)
            name_item = QTableWidgetItem(p_name)
            name_item.setData(Qt.UserRole, pid)
            self.cart_table.setItem(r_idx, 0, name_item)
            
            qty_item = QTableWidgetItem(str(qty))
            qty_item.setFlags(qty_item.flags() | Qt.ItemIsEditable)
            self.cart_table.setItem(r_idx, 1, qty_item)
            
            unit_item = QTableWidgetItem(str(price))
            unit_item.setFlags(unit_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(r_idx, 2, unit_item)
            
            total_item = QTableWidgetItem(str(total))
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(r_idx, 3, total_item)
        self.cart_table.blockSignals(False)

        # Restore Inputs
        self.customer_name.setText(state["customer_name"])
        self.customer_phone.setText(state["customer_phone"])
        self.customer_address.setText(state["customer_address"])
        self.discount_input.setText(state["discount"])
        self.paid_now_input.setText(state["paid_now"])
        self.credit_checkbox.setChecked(state["is_credit"])
        
        if state["salesperson_idx"] != -1:
            self.salesperson_dropdown.setCurrentIndex(state["salesperson_idx"])

        self.calculate_grand_total() # Update the total label

    def clear_saved_state(self):
        """Clears the static variable after a successful sale."""
        SalesWindow.saved_state = {
            "cart": [], "customer_name": "", "customer_phone": "", 
            "customer_address": "", "discount": "", "paid_now": "", 
            "is_credit": False, "salesperson_idx": -1
        }
        self.editing_sale_id = None
        self.submit_btn.setText("✅ Complete Sale")
        # Also clear UI
        self.cart_table.setRowCount(0)
        self.discount_input.clear()
        self.credit_checkbox.setChecked(False)
        self.customer_name.clear()
        self.customer_phone.clear()
        self.customer_address.clear()
        self.paid_now_input.clear()
        self.calculate_grand_total()

    # ----------------- Calculation Logic -----------------

    def calculate_grand_total(self):
        """Calculates table sum, subtracts discount, updates Label."""
        table_total = 0.0
        for row in range(self.cart_table.rowCount()):
            try:
                # SAFETY CHECK: Get the item first, check if it exists
                item = self.cart_table.item(row, 3) 
                if item is not None and item.text(): # Only proceed if item exists and has text
                    row_total = float(item.text())
                    table_total += row_total
            except ValueError:
                pass
        
        try:
            discount = float(self.discount_input.text()) if self.discount_input.text() else 0.0
        except ValueError:
            discount = 0.0
            
        grand_total = max(0, table_total - discount)
        self.total_display_label.setText(f"Grand Total: {grand_total:,.2f}")
        
        # Save state safely
        self.save_state()

    # ----------------- Existing Logic with Minor Updates -----------------

    def toggle_credit_fields(self, state):
        self.credit_details_widget.setVisible(state == Qt.Checked)

    def start_edit_bill(self):
        sale_id, ok = QInputDialog.getInt(self, "Edit Bill", "Enter Sale ID to edit:", min=1)
        if not ok:
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Edit",
            f"Load bill #{sale_id} into the current screen for editing?\nCurrent cart data will be replaced.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        data = fetch_sale_for_edit(sale_id)
        if not data:
            QMessageBox.warning(self, "Not Found", f"No bill found with Sale ID {sale_id}.")
            return

        self.load_sale_into_form(data)

    def load_sale_into_form(self, sale_data):
        self.editing_sale_id = sale_data["sale_id"]
        self.submit_btn.setText("💾 Update Bill & Reprint")

        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(0)

        for item in sale_data["items"]:
            row = self.cart_table.rowCount()
            self.cart_table.insertRow(row)

            name_item = QTableWidgetItem(item["product_name"])
            name_item.setData(Qt.UserRole, item["product_id"])
            self.cart_table.setItem(row, 0, name_item)

            qty_item = QTableWidgetItem(str(item["qty"]))
            qty_item.setFlags(qty_item.flags() | Qt.ItemIsEditable)
            self.cart_table.setItem(row, 1, qty_item)

            unit_item = QTableWidgetItem(f"{float(item['unit_price']):.2f}")
            unit_item.setFlags(unit_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 2, unit_item)

            total_item = QTableWidgetItem(f"{float(item['unit_price']) * int(item['qty']):.2f}")
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 3, total_item)

        self.cart_table.blockSignals(False)

        self.discount_input.setText(str(sale_data.get("discount", 0)))
        self.credit_checkbox.setChecked(bool(sale_data.get("on_credit", False)))
        self.customer_name.setText(sale_data["customer"].get("name", ""))
        self.customer_phone.setText(sale_data["customer"].get("phone", ""))
        self.customer_address.setText(sale_data["customer"].get("address", ""))
        self.paid_now_input.setText(str(sale_data.get("amount_paid_now", 0)))

        idx = self.salesperson_dropdown.findData(sale_data.get("user_id"))
        if idx >= 0:
            self.salesperson_dropdown.setCurrentIndex(idx)

        self.calculate_grand_total()
        self.save_state()

    def load_salespersons(self):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT user_id, username FROM Users")
        users = cur.fetchall()
        conn.close()
        self.salesperson_dropdown.clear()
        for uid, uname in users:
            self.salesperson_dropdown.addItem(uname, uid)
        
        # Auto-select current user if found (Only if not restoring state)
        if self.salesperson_dropdown.currentIndex() == -1:
            try:
                index = self.salesperson_dropdown.findData(current_user["user_id"])
                if index >= 0: self.salesperson_dropdown.setCurrentIndex(index)
            except: pass

    def load_products(self):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            SELECT p.product_id, p.product_name, v.box_selling_price, 
                   (SELECT SUM(current_stock_boxes) FROM Product_Versions WHERE product_id = p.product_id) as total_stock
            FROM Products p
            JOIN Product_Versions v ON v.product_id = p.product_id
            WHERE v.version_id = (SELECT MAX(version_id) FROM Product_Versions WHERE product_id = p.product_id)
            ORDER BY p.product_name
        """)
        self.products = cur.fetchall()
        conn.close()
        
        self.product_dropdown.clear()
        self.product_dropdown.addItem("", -1)
        for pid, name, price, stock in self.products:
            stock_val = stock if stock else 0
            display_text = f"{name} - {price:.2f} (Stock: {stock_val})" if price else name
            self.product_dropdown.addItem(display_text, pid)

    def update_price_field(self):
        index = self.product_dropdown.currentIndex()
        if index <= 0:
            self.unit_price_input.clear()
            return

        product_id = self.product_dropdown.itemData(index)
        for pid, name, price, stock in self.products:
            if pid == product_id:
                self.unit_price_input.setText(f"{price:.2f}")
                stock_val = stock if stock else 0
                self.qty_input.setMaximum(max(1, stock_val)) 
                break

    def remove_selected_item(self):
        selected = self.cart_table.currentRow()
        if selected >= 0: 
            self.cart_table.removeRow(selected)
            self.calculate_grand_total() # Recalculate

    def add_to_cart(self):
        text = self.product_dropdown.currentText()
        
        # Find product in list
        found_product = None
        for pid, name, price, stock in self.products:
            stock_val = stock if stock else 0
            display = f"{name} - {price:.2f} (Stock: {stock_val})" if price else name
            if display == text:
                found_product = (pid, name, price, stock_val)
                break
        
        if not found_product:
            return

        pid, product_name, price, stock = found_product
        
        try: 
            qty_to_add = int(self.qty_input.value())
            unit_price = float(self.unit_price_input.text())
        except: 
            return

        # --- STOCK VALIDATION ---
        if stock <= 0:
             QMessageBox.critical(self, "Out of Stock", f"Sorry, '{product_name}' is currently out of stock.")
             return

        # Check existing quantity in cart
        current_cart_qty = 0
        existing_row = -1
        
        for r in range(self.cart_table.rowCount()):
            if self.cart_table.item(r, 0).text() == product_name:
                current_cart_qty += int(self.cart_table.item(r, 1).text())
                existing_row = r

        if (current_cart_qty + qty_to_add) > stock:
            QMessageBox.warning(self, "Stock Limit", 
                                f"Insufficient stock!\nAvailable: {stock}\nAlready in Cart: {current_cart_qty}\nCannot add {qty_to_add} more.")
            return
        # ------------------------

        total = unit_price * qty_to_add

        # If item exists, update quantity
        if existing_row != -1:
            new_qty = current_cart_qty + qty_to_add
            new_total = new_qty * unit_price
            
            self.cart_table.blockSignals(True) # Block signals during update
            self.cart_table.item(existing_row, 1).setText(str(new_qty))
            self.cart_table.item(existing_row, 3).setText(f"{new_total:.2f}")
            self.cart_table.blockSignals(False)
        else:
            # Add new row
            # CRITICAL FIX: Block signals so calculate_grand_total doesn't fire prematurely
            self.cart_table.blockSignals(True) 
            
            row = self.cart_table.rowCount()
            self.cart_table.insertRow(row)
            name_item = QTableWidgetItem(product_name)
            name_item.setData(Qt.UserRole, pid)
            self.cart_table.setItem(row, 0, name_item)
            
            qty_item = QTableWidgetItem(str(qty_to_add))
            qty_item.setFlags(qty_item.flags() | Qt.ItemIsEditable)
            self.cart_table.setItem(row, 1, qty_item)
            
            unit_item = QTableWidgetItem(f"{unit_price:.2f}")
            unit_item.setFlags(unit_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 2, unit_item)
            
            total_item = QTableWidgetItem(f"{total:.2f}")
            total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
            self.cart_table.setItem(row, 3, total_item)
            
            self.cart_table.blockSignals(False) # Resume signals
        
        # Reset inputs
        self.product_dropdown.setCurrentIndex(0)
        self.qty_input.setValue(1)
        self.unit_price_input.clear()
        
        # Manually trigger calculation now that the row is fully ready
        self.calculate_grand_total()

        
    def update_price_on_qty_change(self, item):
        row, col = item.row(), item.column()
        if col != 1: return 

        product_name = self.cart_table.item(row, 0).text()
        available_stock = 0
        for pid, name, price, stock in self.products:
            if name == product_name:
                available_stock = stock if stock else 0
                break

        try:
            qty = int(item.text())
            if qty > available_stock:
                QMessageBox.warning(self, "Stock Limit", f"You cannot sell {qty}. Only {available_stock} in stock.")
                self.cart_table.blockSignals(True)
                item.setText(str(available_stock)) 
                qty = available_stock 
                self.cart_table.blockSignals(False)
            
            if qty <= 0: raise ValueError
            
            unit_price = float(self.cart_table.item(row, 2).text())
            
            self.cart_table.blockSignals(True)
            self.cart_table.setItem(row, 3, QTableWidgetItem(f"{unit_price * qty:.2f}"))
            self.cart_table.blockSignals(False)
        except: pass
        
        self.calculate_grand_total() # Recalculate and Save

    def complete_sale(self):
        if self.cart_table.rowCount() == 0:
            QMessageBox.warning(self, "Empty Cart", "Please add items to the cart.")
            return

        salesperson_id = self.salesperson_dropdown.currentData()
        items = []
        estimated_total = 0.0

        for row in range(self.cart_table.rowCount()):
            product_name = self.cart_table.item(row, 0).text()
            product_id = self.cart_table.item(row, 0).data(Qt.UserRole)
            if not product_id:
                product_id = next((pid for pid, name, _, _ in self.products if name == product_name), None)
            
            qty = int(self.cart_table.item(row, 1).text())
            unit_price = float(self.cart_table.item(row, 2).text())
            
            if product_id:
                items.append((product_id, qty, unit_price))
                estimated_total += (qty * unit_price)

        if not items:
            QMessageBox.warning(self, "Validation", "No valid products found in bill lines.")
            return

        try:
            discount = float(self.discount_input.text()) if self.discount_input.text() else 0
        except ValueError:
            discount = 0
            
        on_credit = self.credit_checkbox.isChecked()
        customer = None
        amount_paid_now = 0.0

        if on_credit:
            if not self.customer_name.text().strip():
                QMessageBox.warning(self, "Validation", "Customer Name is required for credit sales.")
                return
                
            customer = {
                "name": self.customer_name.text(),
                "phone": self.customer_phone.text(),
                "address": self.customer_address.text()
            }
            
            txt_paid = self.paid_now_input.text().strip()
            if txt_paid:
                try: amount_paid_now = float(txt_paid)
                except: 
                    QMessageBox.warning(self, "Validation", "Invalid Paid Now amount.")
                    return
            
            net_total = estimated_total - discount
            if amount_paid_now > net_total:
                 QMessageBox.warning(self, "Validation", f"Paid amount ({amount_paid_now}) cannot exceed Net Total ({net_total}).")
                 return
        
        if self.editing_sale_id:
            confirm_msg = (
                f"You are about to update Bill #{self.editing_sale_id}.\n"
                "This will replace old bill lines and recalculate stock/profit.\n\n"
                "Do you want to continue?"
            )
            confirm = QMessageBox.question(self, "Confirm Bill Update", confirm_msg, QMessageBox.Yes | QMessageBox.No)
            if confirm != QMessageBox.Yes:
                return

            result = update_sale(
                self.editing_sale_id,
                salesperson_id,
                items,
                customer,
                discount,
                on_credit,
                amount_paid_now,
            )
        else:
            result = create_sale(salesperson_id, items, customer, discount, on_credit, amount_paid_now)
        
        if result:
            sale_id = result["sale_id"]
            receipt_name = customer["name"] if customer else "Walk-in Customer"
            if not customer:
                name_input, ok = QInputDialog.getText(self, "Customer Name", "Enter Name for Receipt (Optional):")
                if ok and name_input.strip():
                    receipt_name = name_input.strip()

            safe_name = "".join(c for c in receipt_name if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
            filename = f"receipt_{sale_id}_{safe_name}.pdf"

            create_receipt(sale_id, filename, receipt_name)

            if self.editing_sale_id:
                QMessageBox.information(self, "Success", f"Bill Updated and Reprinted!\nReceipt: {filename}")
            else:
                QMessageBox.information(self, "Success", f"Sale Completed!\nReceipt: {filename}")
            
            # CLEAR THE SAVED STATE HERE
            self.clear_saved_state()
            self.load_products()
        else:
            QMessageBox.critical(self, "Error", "Failed to complete sale.")