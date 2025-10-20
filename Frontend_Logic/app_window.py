# Frontend_Logic/app_window.py
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from Frontend_Logic.sidebar import Sidebar
from Frontend_Logic.staffManagment_ui import StaffManagementUI
from Frontend_Logic.products_ui import ProductsUI
from Frontend_Logic.customers_ui import CustomersUI
from Frontend_Logic.sales_ui import SalesWindow
from Frontend_Logic.reporting_ui import ReportingUI
from session import current_user


class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("POS System")
        self.resize(1200, 800)

        # Central container
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # App icon
        self.setWindowIcon(QIcon("icons/logo.png"))

        # Sidebar
        self.sidebar = Sidebar(self)
        layout.addWidget(self.sidebar, 1)

        # Main content area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.content_area, 4)

        # Default content → Products & Stock
        self.show_module("Products", "Products & Stock")

    def show_module(self, module_name: str, submodule_name: str = None):
        # Clear previous content
        for i in reversed(range(self.content_layout.count())):
            widget_to_remove = self.content_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)

        if module_name == "Staff Management":
            widget = StaffManagementUI(parent=self)
        elif module_name == "Products":
            # default submodule → Products & Stock
            widget = ProductsUI(submodule=submodule_name or "Products & Stock", parent=self)
        elif module_name == "Customers":
            widget = CustomersUI(submodule=submodule_name, parent=self)
        elif module_name == "Sales":
            from Frontend_Logic.sales_ui import SalesWindow
            widget = SalesWindow()

        elif module_name == "Reporting & Analytics":
            widget = ReportingUI(submodule=submodule_name, parent=self)
        else:
            widget = QWidget()

        self.content_layout.addWidget(widget)
