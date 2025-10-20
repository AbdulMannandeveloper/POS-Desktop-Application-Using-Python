import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QHBoxLayout,
    QMessageBox, QDialog, QDialogButtonBox, QFormLayout
)
from PyQt5.QtCore import Qt
from Backend_Logic.Login import signup_staff

DB_NAME = "POS.db"


class EditUserDialog(QDialog):
    """Dialog to update user status."""

    def __init__(self, user_id, current_status, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Edit User Status")
        self.setModal(True)

        self.setStyleSheet("""
            QDialog {
                background-color: #f9f9f9;
            }
            QLabel {
                font-size: 14px;
                font-weight: bold;
            }
            QComboBox {
                padding: 6px;
                border-radius: 6px;
                border: 1px solid #ccc;
                font-size: 14px;
            }
            QPushButton {
                padding: 6px 14px;
                font-size: 14px;
                border-radius: 6px;
                background-color: #2ecc71;
                color: white;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)

        layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.status_dropdown = QComboBox()
        self.status_dropdown.addItems(["Active", "Inactive"])
        self.status_dropdown.setCurrentText(current_status)
        form_layout.addRow("Status:", self.status_dropdown)
        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("💾 Save")
        buttons.button(QDialogButtonBox.Cancel).setText("✖ Cancel")
        buttons.accepted.connect(self.save_status)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def save_status(self):
        new_status = self.status_dropdown.currentText()
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET status=? WHERE user_id=?", (new_status, self.user_id))
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Success", f"User status updated to {new_status}")
        self.accept()


class StaffManagementUI(QWidget):
    def __init__(self, submodule=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Staff Management")
        layout = QVBoxLayout(self)

        # Global stylesheet
        self.setStyleSheet("""
            QWidget {
                background-color: #f4f6f9;
                font-family: Arial;
            }
            QLabel#TitleLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 15px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                font-size: 14px;
            }
            QComboBox {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QTableWidget {
                background: white;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                gridline-color: #ecf0f1;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 6px;
                border: none;
                font-size: 14px;
            }
        """)

        # Title
        if submodule:
            title = QLabel(f"Staff Management – {submodule}")
        else:
            title = QLabel("Staff Management Module")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Add Staff Form ---
        form_layout = QHBoxLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.role_dropdown = QComboBox()
        self.role_dropdown.addItems(["Staff", "Salesman"])
        self.role_dropdown.currentTextChanged.connect(self.handle_role_change)

        self.add_button = QPushButton("➕ Add Staff")
        self.add_button.clicked.connect(self.add_staff)

        form_layout.addWidget(self.username_input)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.role_dropdown)
        form_layout.addWidget(self.add_button)

        layout.addLayout(form_layout)

        # --- Users Table ---
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(5)
        self.user_table.setHorizontalHeaderLabels(
            ["ID", "Username", "Role", "Status", "Created At"]
        )
        self.user_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.user_table.cellDoubleClicked.connect(self.edit_user_status)

        layout.addWidget(self.user_table)

        self.setLayout(layout)
        self.load_users()

    def handle_role_change(self, role):
        """Auto-fill and lock password for Salesman."""
        if role == "Salesman":
            self.password_input.setText("salesman@123")
            self.password_input.setReadOnly(True)
        else:
            self.password_input.clear()
            self.password_input.setReadOnly(False)

    def add_staff(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_dropdown.currentText()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Username and Password cannot be empty")
            return

        success = signup_staff(username, password, role)
        if success:
            QMessageBox.information(self, "Success", f"{role} account created successfully")
            self.username_input.clear()
            self.password_input.clear()
            self.load_users()
        else:
            QMessageBox.warning(self, "Error", "Username already exists")

    def load_users(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, role, status, created_at FROM Users")
        users = cursor.fetchall()
        conn.close()

        self.user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            for col, val in enumerate(user):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.user_table.setItem(row, col, item)

    def edit_user_status(self, row, col):
        user_id = int(self.user_table.item(row, 0).text())
        current_status = self.user_table.item(row, 3).text()

        dialog = EditUserDialog(user_id, current_status, self)
        if dialog.exec_():
            self.load_users()
