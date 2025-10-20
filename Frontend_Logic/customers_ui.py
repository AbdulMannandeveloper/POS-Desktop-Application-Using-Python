# Frontend_Logic/customers_ui.py
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox, QTabWidget
)
from PyQt5.QtCore import Qt

from Backend_Logic.Credit_Customers import (
    fetch_all_credit_customers,
    mark_credit_as_paid,
    get_customer_credit_history
)


class CustomersUI(QWidget):
    def __init__(self, submodule=None, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.setStyleSheet("""
            QLabel, QLineEdit, QPushButton, QTableWidget, QComboBox, 
            QSpinBox, QTextEdit, QHeaderView::section {
                font-size: 10pt;
            }
        """)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("💳 Customer Credit Management")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1 → Credit Records
        records_tab = QWidget()
        r_layout = QVBoxLayout()

        top_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or phone...")
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_credit_records)
        top_bar.addWidget(self.search_input)
        top_bar.addWidget(refresh_btn)
        r_layout.addLayout(top_bar)

        self.credit_table = QTableWidget()
        self.credit_table.setColumnCount(6)
        self.credit_table.setHorizontalHeaderLabels(
            ["Credit ID", "Customer Name", "Phone", "Amount", "Status", "Sale Date"]
        )
        self.credit_table.horizontalHeader().setStretchLastSection(True)
        r_layout.addWidget(self.credit_table)

        records_tab.setLayout(r_layout)
        self.tabs.addTab(records_tab, "📋 Credit Records")

        # Tab 2 → Update Status
        update_tab = QWidget()
        u_layout = QVBoxLayout()

        self.customer_id_input = QLineEdit()
        self.customer_id_input.setPlaceholderText("Enter Customer ID")
        self.history_btn = QPushButton("🔍 View Credit History")
        self.history_btn.clicked.connect(self.show_credit_history)

        u_layout.addWidget(self.customer_id_input)
        u_layout.addWidget(self.history_btn)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            ["Credit ID", "Sale ID", "Amount", "Status", "Sale Date"]
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)
        u_layout.addWidget(self.history_table)

        self.pay_btn = QPushButton("✅ Mark Selected as Paid")
        self.pay_btn.clicked.connect(self.mark_selected_paid)
        u_layout.addWidget(self.pay_btn)

        update_tab.setLayout(u_layout)
        self.tabs.addTab(update_tab, "✏️ Update Status")

        # Load initial data
        self.load_credit_records()

    def load_credit_records(self):
        """Load unpaid credit customers into the table, with optional search."""
        records = fetch_all_credit_customers()
        search = self.search_input.text().strip().lower()
        if search:
            records = [r for r in records if search in r["customer_name"].lower() or search in (r["phone"] or "").lower()]

        self.credit_table.setRowCount(len(records))
        for row_idx, record in enumerate(records):
            self.credit_table.setItem(row_idx, 0, QTableWidgetItem(str(record["credit_id"])))
            self.credit_table.setItem(row_idx, 1, QTableWidgetItem(record["customer_name"]))
            self.credit_table.setItem(row_idx, 2, QTableWidgetItem(record["phone"]))
            self.credit_table.setItem(row_idx, 3, QTableWidgetItem(str(record["credit_amount"])))
            self.credit_table.setItem(row_idx, 4, QTableWidgetItem(record["status"]))
            self.credit_table.setItem(row_idx, 5, QTableWidgetItem(str(record["sale_date"])))

    def show_credit_history(self):
        """Fetch and display credit history for entered Credit ID."""
        customer_id = self.customer_id_input.text().strip()
        if not customer_id.isdigit():
            QMessageBox.warning(self, "Error", "Please enter a valid numeric Customer ID.")
            return

        history = get_customer_credit_history(int(customer_id))
        self.history_table.setRowCount(len(history))
        for row_idx, record in enumerate(history):
            self.history_table.setItem(row_idx, 0, QTableWidgetItem(str(record["credit_id"])))
            self.history_table.setItem(row_idx, 1, QTableWidgetItem(str(record["sale_id"])))
            self.history_table.setItem(row_idx, 2, QTableWidgetItem(str(record["credit_amount"])))
            self.history_table.setItem(row_idx, 3, QTableWidgetItem(record["status"]))
            self.history_table.setItem(row_idx, 4, QTableWidgetItem(str(record["sale_date"])))

    def mark_selected_paid(self):
        """Mark selected credit record as Paid."""
        selected_row = self.history_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Error", "Please select a credit record first.")
            return

        credit_id = self.history_table.item(selected_row, 0).text()
        if mark_credit_as_paid(int(credit_id)):
            QMessageBox.information(self, "Success", f"Credit ID {credit_id} marked as Paid.")
            self.show_credit_history()
            self.load_credit_records()
        else:
            QMessageBox.warning(self, "Failed", f"Unable to update Credit ID {credit_id}.")
