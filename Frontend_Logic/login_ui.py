# Frontend_Logic/login_ui.py

from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
import sqlite3

from Backend_Logic.Login import login
from session import current_user
# --- update imports ---
from Frontend_Logic.app_window import AppWindow   # <-- main container window (with sidebar)

# Import the Products and Signup windows
from Frontend_Logic.products_ui import ProductsUI
from Frontend_Logic.signup_ui import SignupWindow   # <-- ensure this file exists

DB_NAME = "POS.db"


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("POS Login")
        self.setFixedSize(600, 500)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f2f5;
                font-family: Segoe UI, Arial;
            }
            QLineEdit {
                border: 2px solid #dcdde1;
                border-radius: 10px;
                padding: 12px;
                font-size: 16px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 2px solid #0097e6;
            }
            QPushButton {
                background-color: #0097e6;
                color: white;
                border-radius: 10px;
                padding: 14px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00a8ff;
            }
            QLabel#title {
                font-size: 26px;
                font-weight: bold;
                color: #2f3640;
            }
            QLabel#link {
                color: #0097e6;
                font-size: 14px;
                text-decoration: underline;
            }
            QLabel#link:hover {
                color: #00a8ff;
                cursor: pointer;
            }
        """)

        # Title
        label_title = QLabel("Welcome to POS System")
        label_title.setObjectName("title")
        label_title.setAlignment(Qt.AlignCenter)

        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("👤 Enter your username")

        # Password
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("🔒 Enter your password")

        # Login Button
        self.login_btn = QPushButton("Login")
        self.login_btn.setFixedHeight(50)
        self.login_btn.clicked.connect(self.handle_login)

        # Card container
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 15px;
                padding: 40px;
                border: 1px solid #dcdde1;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(label_title)
        card_layout.addSpacing(25)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addSpacing(20)
        card_layout.addWidget(self.login_btn)

        # Signup link (only if no admin exists)
        if not self.admin_exists():
            signup_link = QLabel("Create Admin Account")
            signup_link.setObjectName("link")
            signup_link.setAlignment(Qt.AlignCenter)
            signup_link.mousePressEvent = self.open_signup_page
            card_layout.addSpacing(15)
            card_layout.addWidget(signup_link)

        # Centering layout
        wrapper = QVBoxLayout(self)
        wrapper.addStretch()
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(card, alignment=Qt.AlignCenter)
        row.addStretch()
        wrapper.addLayout(row)
        wrapper.addStretch()

    def admin_exists(self) -> bool:
        """Check if an Admin user exists in the database."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM Users WHERE role='Admin' LIMIT 1")
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def handle_login(self):
        """Handle login attempt"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return

        if login(username, password):
            QMessageBox.information(
                self, "Success", f"Welcome {current_user['username']} ({current_user['role']})"
            )
            self.open_products_page()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid credentials or inactive account")

    def open_products_page(self):
        """Opens the Main Application Window after login"""
        self.app_window = AppWindow()
        self.app_window.show()
        self.close()


    def open_signup_page(self, event):
        """Opens the Signup page if no Admin exists"""
        self.signup_window = SignupWindow()
        self.signup_window.show()
        self.close()
