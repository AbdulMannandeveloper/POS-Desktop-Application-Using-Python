# Frontend_Logic/customers_ui.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, 
    QAbstractItemView, QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

# Make sure your Backend has these updated functions
from Backend_Logic.Credit_Customers import (
    fetch_all_credit_customers, 
    process_credit_payment
)

class CustomersUI(QWidget):
    def __init__(self, submodule=None, parent=None):
        super().__init__(parent)
        
        self.setStyleSheet("""
            QTableWidget { font-size: 10pt; }
            QPushButton { padding: 8px; font-weight: bold; }
            QLabel { font-size: 12pt; font-weight: bold; }
            QLineEdit { padding: 6px; font-size: 10pt; }
            QHeaderView::section { background-color: #34495e; color: white; padding: 5px; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # --- Header ---
        header = QLabel("💳 Credit Customers Management")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("background-color: #ecf0f1; padding: 10px; border-radius: 5px; color: #2c3e50;")
        layout.addWidget(header)

        # --- Search Bar & Refresh ---
        top_bar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by Name or Phone...")
        self.search_input.textChanged.connect(self.filter_table)
        
        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.setStyleSheet("background-color: #3498db; color: white;")
        refresh_btn.clicked.connect(self.load_data)
        
        top_bar.addWidget(self.search_input)
        top_bar.addWidget(refresh_btn)
        layout.addLayout(top_bar)

        # --- Table ---
        self.credit_table = QTableWidget()
        self.credit_table.setColumnCount(7)
        self.credit_table.setHorizontalHeaderLabels([
            "Credit ID", "Customer Name", "Phone", "Total Debt", 
            "Paid So Far", "Remaining", "Sale ID"
        ])
        
        # Styling the table
        self.credit_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.credit_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.credit_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.credit_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.credit_table)

        # --- Action Buttons ---
        btn_layout = QHBoxLayout()
        
        pay_btn = QPushButton("💰 Make Payment (Partial/Full)")
        pay_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-size: 11pt; padding: 10px; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        pay_btn.clicked.connect(self.handle_payment)
        
        btn_layout.addStretch()
        btn_layout.addWidget(pay_btn)
        layout.addLayout(btn_layout)

        # Internal data cache for filtering
        self.all_records = []
        
        # Load initial data
        self.load_data()

    def load_data(self):
        """Fetch data from backend and populate table."""
        try:
            # This expects the NEW backend returning tuples/lists
            self.all_records = fetch_all_credit_customers()
            self.populate_table(self.all_records)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load credit records: {e}")

    def populate_table(self, data):
        """Fill the table widget with data."""
        self.credit_table.setRowCount(len(data))
        self.credit_table.setSortingEnabled(False) # Disable sorting during insert

        for i, row in enumerate(data):
            # unpack tuple based on new backend structure
            # (credit_id, name, phone, total, paid, remaining, sale_id, status)
            # OR dictionary access if your backend still returns dicts. 
            # This code assumes TUPLES from the standard sqlite fetchall
            
            # Safe handling if backend returns dicts or tuples
            if isinstance(row, dict):
                credit_id = row['credit_id']
                name = row['customer_name']
                phone = row['phone']
                total = row['credit_amount']
                paid = row.get('amount_paid', 0) # Handle if key missing
                remaining = total - paid
                sale_id = row.get('sale_id', 'N/A')
            else:
                # Assumes tuple from new backend
                credit_id, name, phone, total, paid, remaining, sale_id, status = row

            vals = [
                credit_id, name, phone, 
                f"{total:,.0f}", f"{paid:,.0f}", f"{remaining:,.0f}", sale_id
            ]

            for j, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                
                # Highlight "Remaining" column (Index 5) in Red
                if j == 5: 
                    item.setForeground(QColor("#c0392b")) # Dark Red text
                    item.setBackground(QColor("#fadbd8")) # Light Red background
                    item.setFont(self.font()) # Reset font to bold if needed
                
                self.credit_table.setItem(i, j, item)
        
        self.credit_table.setSortingEnabled(True)

    def filter_table(self):
        """Client-side filter by name or phone."""
        query = self.search_input.text().lower()
        if not query:
            self.populate_table(self.all_records)
            return
            
        filtered = []
        for row in self.all_records:
            # Check if using dict or tuple backend
            if isinstance(row, dict):
                name = str(row['customer_name']).lower()
                phone = str(row['phone']).lower()
            else:
                name = str(row[1]).lower()
                phone = str(row[2]).lower()
                
            if query in name or query in phone:
                filtered.append(row)
                
        self.populate_table(filtered)

    def handle_payment(self):
        """Open dialog to accept payment."""
        current_row = self.credit_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a customer to record a payment.")
            return
            
        # Extract data from the table cells
        credit_id = int(self.credit_table.item(current_row, 0).text())
        name = self.credit_table.item(current_row, 1).text()
        # Remove commas for float conversion
        remaining_str = self.credit_table.item(current_row, 5).text().replace(',', '')
        remaining = float(remaining_str)
        
        # Open Input Dialog
        amount, ok = QInputDialog.getDouble(
            self, "Record Payment", 
            f"Customer: {name}\nRemaining Balance: {remaining:,.0f}\n\nEnter Amount Received:",
            min=1, max=remaining, decimals=0
        )
        
        if ok:
            # Call Backend
            success, result_msg = process_credit_payment(credit_id, amount)
            
            if success:
                # Show success and filename
                QMessageBox.information(self, "Payment Successful", 
                                      f"✅ Payment recorded!\n\nReceipt generated:\n{result_msg}")
                self.load_data() # Refresh table to show new balance
            else:
                QMessageBox.critical(self, "Payment Failed", f"❌ Error: {result_msg}")