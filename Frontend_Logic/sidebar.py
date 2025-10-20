# Frontend_Logic/sidebar.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt5.QtCore import Qt
from session import current_user


class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.buttons = {}       # store main module buttons
        self.sub_buttons = {}   # store submodule buttons

        # Sidebar styling
        self.setStyleSheet("""
            QFrame {
                background-color: #111111;
            }
            QPushButton {
                color: #dcdde1;
                background-color: transparent;
                border: none;
                text-align: left;
                padding: 12px 20px;
                font-size: 15px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2f3640;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #0097e6;
                color: #ffffff;
                border-radius: 4px;
            }
            QLabel {
                color: #f5f6fa;
                font-size: 18px;
                font-weight: bold;
                padding: 15px 20px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)

        # Sidebar header
        header = QLabel("POS Menu")
        layout.addWidget(header)

        # Conditional: Staff Management only if admin
        if current_user.get("role") == "Admin":
            self.add_button(layout, "Staff Management")

        # Products module with only 4 pages
        self.add_button(layout, "Products", [
            "Products & Stock",
            "Stock Purchasing",
            "Return to Supplier",
            "Return by Customer"
        ])

        # Customers
        self.add_button(layout, "Customers")

        # Sales
        self.add_button(layout, "Sales")

        # Reporting
        self.add_button(layout, "Reporting & Analytics")

        layout.addStretch()

        # Logout
        logout_btn = QPushButton("Logout")
        logout_btn.clicked.connect(self.handle_logout)
        layout.addWidget(logout_btn)

        # --- Default selection on login ---
        self.buttons["Products"].setChecked(True)

    def resizeEvent(self, event):
        """Make sidebar always 20% of parent width."""
        if self.parent:
            parent_width = self.parent.width()
            self.setFixedWidth(int(parent_width * 0.20))
        super().resizeEvent(event)

    def add_button(self, layout, module_name, submodules=None):
        btn = QPushButton(module_name)
        btn.setCheckable(True)
        btn.clicked.connect(lambda _, m=module_name: self.module_clicked(m))
        layout.addWidget(btn)
        self.buttons[module_name] = btn

        if submodules:
            for sub in submodules:
                sub_btn = QPushButton(f"   ↳ {sub}")
                sub_btn.setCheckable(True)
                sub_btn.clicked.connect(lambda _, m=module_name, s=sub: self.submodule_clicked(m, s))
                layout.addWidget(sub_btn)
                self.sub_buttons[(module_name, sub)] = sub_btn

    def module_clicked(self, module_name):
        self.reset_buttons()
        self.buttons[module_name].setChecked(True)
        if self.parent:
            self.parent.show_module(module_name)

    def submodule_clicked(self, module_name, submodule_name):
        self.reset_buttons()
        self.sub_buttons[(module_name, submodule_name)].setChecked(True)
        if self.parent:
            self.parent.show_module(module_name, submodule_name)

    def reset_buttons(self):
        for btn in self.buttons.values():
            btn.setChecked(False)
        for btn in self.sub_buttons.values():
            btn.setChecked(False)

    def handle_logout(self):
        from Frontend_Logic.login_ui import LoginWindow
        self.parent.close()
        self.login = LoginWindow()
        self.login.show()
