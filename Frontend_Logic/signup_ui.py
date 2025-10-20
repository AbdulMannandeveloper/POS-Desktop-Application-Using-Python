from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QMessageBox, QFrame, QComboBox
)
from PyQt5.QtCore import Qt
from Backend_Logic.Login import signup_admin, signup_staff
# from Frontend_Logic.login_ui import LoginWindow   # <-- add this import at the top


class SignupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("POS Signup")
        self.setFixedSize(600, 500)

        self.setStyleSheet("""
            QWidget {
                background-color: #f7f9fc;
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
                border: 2px solid #27ae60;
            }
            QPushButton {
                background-color: #27ae60;
                color: white;
                border-radius: 10px;
                padding: 14px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QLabel#title {
                font-size: 26px;
                font-weight: bold;
                color: #2f3640;
            }
            QComboBox {
                border: 2px solid #dcdde1;
                border-radius: 10px;
                padding: 10px;
                font-size: 16px;
                background-color: #ffffff;
            }
        """)

        # Title
        self.label_title = QLabel("Create New Account")
        self.label_title.setObjectName("title")
        self.label_title.setAlignment(Qt.AlignCenter)

        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("👤 Enter username")

        # Password
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("🔒 Enter password")

        # Role (Admin only once, then Staff)
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Admin", "Staff"])

        # Signup Button
        self.signup_btn = QPushButton("Sign Up")
        self.signup_btn.setFixedHeight(50)
        self.signup_btn.clicked.connect(self.handle_signup)

        # Card layout
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 15px;
                padding: 40px;
                border: 1px solid #dcdde1;
            }
        """)
        card_layout = QVBoxLayout()
        card_layout.addWidget(self.label_title)
        card_layout.addSpacing(25)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.role_combo)
        card_layout.addSpacing(20)
        card_layout.addWidget(self.signup_btn)
        card.setLayout(card_layout)

        # Center everything
        main_layout = QHBoxLayout()
        main_layout.addStretch()
        main_layout.addWidget(card, alignment=Qt.AlignCenter)
        main_layout.addStretch()

        wrapper = QVBoxLayout()
        wrapper.addStretch()
        wrapper.addLayout(main_layout)
        wrapper.addStretch()

        self.setLayout(wrapper)

    def handle_signup(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_combo.currentText()

        if not username or not password:
            QMessageBox.warning(self, "Error", "Please fill all fields")
            return

        if role == "Admin":
            success = signup_admin(username, password)
        else:
            success = signup_staff(username, password)

        if success:
            QMessageBox.information(self, "Success", f"{role} account created successfully.")
            
            from Frontend_Logic.login_ui import LoginWindow   # lazy import here
            self.login_window = LoginWindow()
            self.login_window.show()
            self.close()
        else:
            QMessageBox.critical(self, "Failed", f"Could not create {role} account.")
