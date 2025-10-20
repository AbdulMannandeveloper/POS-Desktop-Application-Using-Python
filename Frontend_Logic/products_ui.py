# Frontend_Logic/products_ui.py

import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QFormLayout,
    QSpinBox, QMessageBox, QDialog, QDialogButtonBox, QTextEdit, QStackedWidget, 
    QAbstractItemView, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from Backend_Logic.Products_n_Stocks import (
    add_product,
    add_product_version,
    customer_stock_return,
    supplier_stock_return,
    get_product_stock,
    list_product_versions,
)

DB_NAME = "POS.db"


# ---------------------- Helpers ----------------------
def fetch_all_products():
    """
    Fetch all products from the database.

    Returns:
        list[tuple]: product_id, product_code, product_name,
                     category, pieces_per_box
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT product_id,
               COALESCE(product_code, ''),
               product_name,
               COALESCE(category, ''),
               COALESCE(pieces_per_box, 1)
        FROM Products
        ORDER BY product_name COLLATE NOCASE
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------------- Dialogs ----------------------
class VersionsDialog(QDialog):
    """Dialog to display product versions in a table."""

    def __init__(self, product_id, product_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Versions — {product_name}")
        self.resize(720, 320)

        layout = QVBoxLayout(self)

        # Table setup
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Version ID", "Unit Selling Price", "Box Cost Price",
            "Box Selling Price", "Current Stock (boxes)", "Valid From"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Populate table
        versions = list_product_versions(product_id)
        self.table.setRowCount(len(versions))
        for r, version in enumerate(versions):
            cells = [
                version.get("version_id"),
                version.get("unit_selling_price"),
                version.get("box_cost_price"),
                version.get("box_selling_price"),
                version.get("current_stock_boxes"),
                version.get("valid_from"),
            ]
            for c, val in enumerate(cells):
                item = QTableWidgetItem("" if val is None else str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)
            # Enable inline edit
            self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked)
            self.table.itemChanged.connect(self._handle_version_edit)

    def _handle_version_edit(self, item):
        """Handle inline edits in version table and update database."""
        try:
            from Backend_Logic.Products_n_Stocks import update_version_field

            row = item.row()
            col = item.column()
            version_id = self.table.item(row, 0).text()
            new_value = item.text().strip()

            # Map editable columns
            field_map = {
                1: "unit_selling_price",   # Unit Selling Price
                2: "box_cost_price",       # Box Cost Price
                3: "box_selling_price",    # Box Selling Price
                4: "current_stock_boxes"   # Stock Boxes
            }

            if col not in field_map:
                return  # Skip other columns

            update_version_field(version_id, field_map[col], new_value)
            item.setBackground(Qt.yellow)  # Optional feedback

        except Exception as e:
            QMessageBox.warning(self, "Edit Error", f"Failed to update version: {e}")


        # Close button
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        #layout.addWidget(btns)


# ---------------------- Main Products UI ----------------------
class ProductsUI(QWidget):
    """
    Products UI Module (embedded, not standalone).

    Supports submodules: "Catalog", "Inventory",
    "Stock Management", "Suppliers", "Returns", "Versions".
    """

    def __init__(self, submodule: str = None, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("ProductsModule")

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
        """)

        # Main layout
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title = QLabel("📦 Products Management")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 22px; 
            font-weight: bold; 
            color: #2c3e50;
            padding: 10px;
            background-color: #ecf0f1;
            border-radius: 6px;
        """)
        self.layout.addWidget(title)

        # Stacked pages
        self.stack = QStackedWidget()
        self.page_products = self._build_products_page()
        self.page_stock_mgmt = self._build_stock_page()
        self.page_supplier_return = self._build_supplier_return_page()
        self.page_customer_return = self._build_customer_return_page()

        self.stack.addWidget(self.page_products)        # index 0
        self.stack.addWidget(self.page_stock_mgmt)      # index 1
        self.stack.addWidget(self.page_supplier_return) # index 2
        self.stack.addWidget(self.page_customer_return) # index 3

        self.layout.addWidget(self.stack)

        # Submodule → page index mapping
        self.submodule_map = {
            None: 0,
            "Catalog": 0,
            "Inventory": 0,
            "Products & Stock": 0,
            "Stock Management": 1,
            "Stock Purchasing": 1,
            "Suppliers": 1,
            "Versions": 1,
            "Return to Supplier": 2,
            "Returns": 2,
            "Return by Customer": 3,
        }

        # Show default page
        self.switch_to_submodule(submodule)

    def _handle_product_edit(self, item):
        """Handle inline editing in products table and update DB."""
        try:
            from Backend_Logic.Products_n_Stocks import update_product_field

            row = item.row()
            col = item.column()
            product_id = self.products_table.item(row, 0).text()
            new_value = item.text().strip()

            # Map editable columns
            field_map = {
                2: "product_name",     # Product Name
                3: "category",         # Category
                4: "pieces_per_box"    # Pieces per Box
            }

            if col not in field_map:
                return  # Skip non-editable columns (like Product ID or Stock)

            update_product_field(product_id, field_map[col], new_value)
            item.setBackground(Qt.yellow)  # Optional visual feedback

        except Exception as e:
            QMessageBox.warning(self, "Edit Error", f"Failed to update product: {e}")

    # ---------------- Page Builders ----------------
    def _build_products_page(self):
        """Page: Products & Stock Catalog."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # Search section
        search_group = QGroupBox("Search Products")
        search_layout = QHBoxLayout(search_group)
        
        self.search_input = QLineEdit(placeholderText="Search by name, code, or category...")
        self.search_input.returnPressed.connect(self.load_products_table)

        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self.load_products_table)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_products_table)

        self.edit_mode_btn = QPushButton("✏ Edit Mode")
        self.edit_mode_btn.setCheckable(True)
        self.edit_mode_btn.toggled.connect(self._toggle_edit_mode)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(refresh_btn)
        search_layout.addWidget(self.edit_mode_btn)
        
        layout.addWidget(search_group)

        # Products table
        table_group = QGroupBox("Products Catalog")
        table_layout = QVBoxLayout(table_group)
        
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels([
            "Product ID", "Product Code", "Product Name",
            "Category", "Pieces/Box", "Total Stock (boxes)"
        ])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.products_table.itemChanged.connect(self._handle_product_edit)
        self.products_table.cellDoubleClicked.connect(self.on_product_double_click)
        
        table_layout.addWidget(self.products_table)
        layout.addWidget(table_group)

        self.load_products_table()
        return page
    
    def _toggle_edit_mode(self, enabled):
        if enabled:
            self.products_table.setEditTriggers(QAbstractItemView.DoubleClicked)
            self.edit_mode_btn.setText("🔒 Disable Edit")
            self.edit_mode_btn.setStyleSheet("background-color: #e74c3c;")
        else:
            self.products_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.edit_mode_btn.setText("✏ Edit Mode")
            self.edit_mode_btn.setStyleSheet("")

    def _build_stock_page(self):
        """Page: Stock Management (Add Product / Add Version)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)

        # Add Product Section
        product_group = QGroupBox("➕ Add New Product")
        product_layout = QFormLayout(product_group)
        product_layout.setLabelAlignment(Qt.AlignRight)
        product_layout.setVerticalSpacing(10)

        self.new_code = QLineEdit(placeholderText="Optional unique product code")
        self.new_name = QLineEdit()
        self.new_category = QLineEdit()
        self.new_pieces = QSpinBox(minimum=1, value=1)

        btn_add_product = QPushButton("✅ Create Product")
        btn_add_product.clicked.connect(self._handle_add_product)

        product_layout.addRow("Product Code:", self.new_code)
        product_layout.addRow("Product Name *:", self.new_name)
        product_layout.addRow("Category:", self.new_category)
        product_layout.addRow("Pieces per Box:", self.new_pieces)
        product_layout.addRow("", btn_add_product)

        layout.addWidget(product_group)

        # Add Version Section
        version_group = QGroupBox("📑 Add Product Version")
        version_layout = QFormLayout(version_group)
        version_layout.setLabelAlignment(Qt.AlignRight)
        version_layout.setVerticalSpacing(10)

        self.version_product_dropdown = QComboBox()
        self._refresh_product_dropdown()

        self.version_unit_selling = QLineEdit(placeholderText="0.00")
        self.version_box_cost = QLineEdit(placeholderText="0.00")
        self.version_box_selling = QLineEdit(placeholderText="0.00")
        self.version_stock_boxes = QSpinBox(minimum=0, value=0)

        btn_add_version = QPushButton("➕ Add Version")
        btn_add_version.clicked.connect(self._handle_add_version)

        version_layout.addRow("Select Product *:", self.version_product_dropdown)
        version_layout.addRow("Unit Selling Price *:", self.version_unit_selling)
        version_layout.addRow("Box Cost Price *:", self.version_box_cost)
        version_layout.addRow("Box Selling Price *:", self.version_box_selling)
        version_layout.addRow("Stock (boxes):", self.version_stock_boxes)
        version_layout.addRow("", btn_add_version)

        layout.addWidget(version_group)

        # Help Note
        note = QLabel("💡 Tip: Add a product first, then add versions for it. Versions preserve historical prices and stock records.")
        note.setStyleSheet("""
            background-color: #fff9c4;
            border: 1px solid #fdd835;
            border-radius: 4px;
            padding: 8px;
            color: #5d4037;
            font-style: italic;
        """)
        note.setWordWrap(True)
        layout.addWidget(note)

        return page

    def _build_supplier_return_page(self):
        """Page: Return stock to supplier."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        header = QLabel("↩ Return to Supplier")
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #e67e22;
            padding: 10px;
            background-color: #fef9e7;
            border-radius: 6px;
        """)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Form Container
        form_group = QGroupBox("Return Details")
        form_layout = QFormLayout(form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setVerticalSpacing(12)

        self.sr_product_dropdown = QComboBox()
        self._fill_supplier_product_dropdown()
        self.sr_qty = QSpinBox(minimum=1, value=1)

        form_layout.addRow("Product *:", self.sr_product_dropdown)
        form_layout.addRow("Quantity (boxes) *:", self.sr_qty)

        layout.addWidget(form_group)

        # Action Button
        btn_container = QHBoxLayout()
        btn = QPushButton("🔄 Process Return to Supplier")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                font-size: 12pt;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        btn.clicked.connect(self._handle_supplier_return)
        btn_container.addWidget(btn)
        btn_container.setAlignment(Qt.AlignCenter)
        layout.addLayout(btn_container)

        return page
    
    def _load_sale_items_for_return(self):
        """Load products from a specific sale into dropdown."""
        sale_id_text = self.cr_sale_id.text().strip()
        if not sale_id_text.isdigit():
            QMessageBox.warning(self, "Validation", "Sale ID must be numeric.")
            return

        sale_id = int(sale_id_text)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            SELECT si.product_id, p.product_name, si.quantity_boxes
            FROM Sale_Items si
            JOIN Products p ON si.product_id = p.product_id
            WHERE si.sale_id = ?
        """, (sale_id,))
        rows = cur.fetchall()
        conn.close()

        self.cr_product_dropdown.clear()
        if not rows:
            self.cr_product_dropdown.addItem("No items found")
            self.available_qty_label.setText("Available in sale: -")
            self.cr_qty.setMaximum(1)
            return

        for pid, pname, qty in rows:
            self.cr_product_dropdown.addItem(f"{pname} (Qty: {qty})", userData=(pid, qty))

        self._update_max_qty_display()

    def _update_max_qty_display(self):
        """Update max quantity allowed based on selected product."""
        data = self.cr_product_dropdown.currentData()
        if not data:
            return
        _, qty = data
        self.cr_qty.setMaximum(int(qty))
        self.available_qty_label.setText(f"Available in sale: {qty}")


    def _build_customer_return_page(self):
        """Page: Handle customer returns (sale-based item selection)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        header = QLabel("🛒 Customer Returns")
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #27ae60;
            padding: 10px;
            background-color: #e8f6f3;
            border-radius: 6px;
        """)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # ---- Form ----
        form_group = QGroupBox("Return Information")
        form_layout = QFormLayout(form_group)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setVerticalSpacing(12)

        # Sale ID
        self.cr_sale_id = QLineEdit(placeholderText="Enter Sale ID")
        self.cr_sale_id.editingFinished.connect(self._load_sale_items_for_return)

        # Product Dropdown (will populate based on Sale ID)
        self.cr_product_dropdown = QComboBox()
        self.cr_product_dropdown.currentIndexChanged.connect(self._update_max_qty_display)

        # Quantity
        self.cr_qty = QSpinBox(minimum=1, value=1)
        self.cr_qty.setMaximum(1)  # dynamically updated

        # Display available quantity label
        self.available_qty_label = QLabel("Available in sale: -")
        self.available_qty_label.setStyleSheet("color: gray; font-size: 9pt;")

        form_layout.addRow("Sale ID *:", self.cr_sale_id)
        form_layout.addRow("Product *:", self.cr_product_dropdown)
        form_layout.addRow("Quantity (boxes) *:", self.cr_qty)
        form_layout.addRow("", self.available_qty_label)

        layout.addWidget(form_group)

        # ---- Action Button ----
        btn_container = QHBoxLayout()
        btn = QPushButton("✅ Process Customer Return")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                font-size: 12pt;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #219150;
            }
        """)
        btn.clicked.connect(self._handle_customer_return)
        btn_container.addWidget(btn)
        btn_container.setAlignment(Qt.AlignCenter)
        layout.addLayout(btn_container)

        return page


    # ---------------- Handlers ----------------
    def load_products_table(self):
        """Load and display products in the table (with search filter)."""
        query = self.search_input.text().strip().lower()
        rows = fetch_all_products()

        if query:
            rows = [
                r for r in rows
                if query in str(r[1]).lower()
                or query in str(r[2]).lower()
                or query in str(r[3]).lower()
            ]

        self.products_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            product_id, product_code, product_name, category, pieces = row
            total_stock = get_product_stock(product_id)
            cells = [product_id, product_code, product_name, category, pieces, total_stock]

            for j, val in enumerate(cells):
                item = QTableWidgetItem("" if val is None else str(val))
                item.setTextAlignment(Qt.AlignCenter)
                
                # Color code stock levels
                if j == 5 and val is not None and val != "":
                    try:
                        stock_val = float(val)
                        if stock_val == 0:
                            item.setBackground(Qt.red)
                            item.setForeground(Qt.white)
                        elif stock_val < 10:
                            item.setBackground(Qt.yellow)
                    except ValueError:
                        pass
                        
                self.products_table.setItem(i, j, item)

    def on_product_double_click(self, row, col):
        """Open versions dialog when a product row is double-clicked."""
        product_id = int(self.products_table.item(row, 0).text())
        product_name = self.products_table.item(row, 2).text()

        dlg = VersionsDialog(product_id, product_name, self)
        dlg.exec_()
        self.load_products_table()

    def _refresh_product_dropdown(self):
        """Refresh dropdown for adding versions."""
        self.version_product_dropdown.clear()
        for pid, pcode, pname, cat, pieces in fetch_all_products():
            label = f"{pname} ({pcode})" if pcode else pname
            self.version_product_dropdown.addItem(label, pid)

    def _fill_supplier_product_dropdown(self):
        """Refresh dropdown for supplier returns."""
        self.sr_product_dropdown.clear()
        for pid, pcode, pname, cat, pieces in fetch_all_products():
            label = f"{pname} ({pcode})" if pcode else pname
            self.sr_product_dropdown.addItem(label, pid)

    # ---------------- Event Handlers ----------------
    def _handle_add_product(self):
        """Add a new product."""
        code = self.new_code.text().strip() or None
        name = self.new_name.text().strip()
        category = self.new_category.text().strip() or None
        pieces = int(self.new_pieces.value())

        if not name:
            QMessageBox.warning(self, "Validation", "Product name is required.")
            return

        if add_product(code, name, category, pieces):
            QMessageBox.information(self, "Success", f"Product '{name}' added successfully.")
            self.new_code.clear()
            self.new_name.clear()
            self.new_category.clear()
            self.new_pieces.setValue(1)
            self._refresh_product_dropdown()
            self._fill_supplier_product_dropdown()
            self.load_products_table()
        else:
            QMessageBox.warning(self, "Error", "Product code already exists or insertion failed.")

    def _handle_add_version(self):
        """Add a new version to an existing product."""
        if self.version_product_dropdown.currentIndex() < 0:
            QMessageBox.warning(self, "Validation", "Select a product first.")
            return

        product_id = self.version_product_dropdown.currentData()

        try:
            unit_price = float(self.version_unit_selling.text().strip())
            box_cost = float(self.version_box_cost.text().strip())
            box_sell = float(self.version_box_selling.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Validation", "Enter valid numeric values for prices.")
            return

        stock = int(self.version_stock_boxes.value())

        if add_product_version(product_id, unit_price, box_cost, box_sell, stock):
            QMessageBox.information(self, "Success", "Product version added successfully.")
            self.version_unit_selling.clear()
            self.version_box_cost.clear()
            self.version_box_selling.clear()
            self.version_stock_boxes.setValue(0)
            self.load_products_table()
        else:
            QMessageBox.warning(self, "Error", "Failed to add version. Check product and values.")

    def _handle_supplier_return(self):
        """Return stock to supplier."""
        if self.sr_product_dropdown.currentIndex() < 0:
            QMessageBox.warning(self, "Validation", "Select product first.")
            return

        product_id = self.sr_product_dropdown.currentData()
        qty = int(self.sr_qty.value())

        if supplier_stock_return(product_id, qty):
            QMessageBox.information(self, "Success", f"Successfully returned {qty} boxes to supplier.")
            self.load_products_table()
        else:
            QMessageBox.warning(self, "Error", "Failed to return to supplier. Check stock levels.")

    def _handle_customer_return(self):
        """Process customer return safely with sale-based product selection."""
        sale_id_text = self.cr_sale_id.text().strip()
        if not sale_id_text.isdigit():
            QMessageBox.warning(self, "Validation", "Sale ID must be numeric.")
            return

        sale_id = int(sale_id_text)
        data = self.cr_product_dropdown.currentData()
        if not data:
            QMessageBox.warning(self, "Validation", "No product selected for return.")
            return

        product_id, available_qty = data
        qty = int(self.cr_qty.value())

        if qty > available_qty:
            QMessageBox.warning(
                self, "Quantity Error",
                f"Cannot return {qty} boxes. Only {available_qty} were sold in this sale."
            )
            return

        if customer_stock_return(sale_id, product_id, qty):
            QMessageBox.information(
                self, "Success",
                f"✅ Processed return: {qty} boxes restored to stock."
            )
            self.load_products_table()
            self._load_sale_items_for_return()
        else:
            QMessageBox.warning(self, "Error", "Failed to process return. Check Sale ID and product selection.")


    # ---------------- Navigation ----------------
    def switch_to_submodule(self, submodule_name: str):
        """Switch to the appropriate page based on submodule name."""
        idx = self.submodule_map.get(submodule_name, 0)
        self.stack.setCurrentIndex(idx)

        # Refresh lists when switching
        if idx == 0:
            self.load_products_table()
        elif idx == 1:
            self._refresh_product_dropdown()
        elif idx == 2:
            self._fill_supplier_product_dropdown()