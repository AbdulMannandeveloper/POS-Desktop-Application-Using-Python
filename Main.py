import sys
import sqlite3
import os
from PyQt5.QtWidgets import QApplication
from Frontend_Logic.login_ui import LoginWindow
from session import current_user
from Backend_Logic.Login import signup_admin, signup_staff, login
from Backend_Logic.Products_n_Stocks import (
    add_product,
    add_product_version,
    customer_stock_return,
    supplier_stock_return,
    get_product_stock,
    list_product_versions
)
from Backend_Logic.Reporting import get_remaining_stock, get_sales_summary, generate_report
from Backend_Logic.Credit_Customers import fetch_all_credit_customers, mark_credit_as_paid, get_customer_credit_history


DB_NAME = "POS.db"


# SQL schema
SCHEMA_SQL = """
-- 1. Users Table
CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    role TEXT CHECK (role IN ('Admin','Staff','Salesman')) NOT NULL,
    status TEXT DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Products Table
CREATE TABLE IF NOT EXISTS Products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT UNIQUE,
    product_name TEXT NOT NULL,
    category TEXT,
    pieces_per_box INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Product Versions Table
CREATE TABLE IF NOT EXISTS Product_Versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    unit_selling_price REAL NOT NULL,
    box_cost_price REAL,
    box_selling_price REAL,
    current_stock_boxes INTEGER DEFAULT 0,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES Products(product_id)
);

-- 4. Suppliers Table
CREATE TABLE IF NOT EXISTS Suppliers (
    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL,
    contact_number TEXT,
    address TEXT
);

-- 5. Stock Transactions Table
CREATE TABLE IF NOT EXISTS Stock_Transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    version_id INTEGER NOT NULL,
    supplier_id INTEGER,
    transaction_type TEXT CHECK (transaction_type IN ('IN','OUT','RETURN','ADJUST')) NOT NULL,
    quantity_boxes INTEGER DEFAULT 0,
    quantity_pieces INTEGER DEFAULT 0,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    remarks TEXT,
    FOREIGN KEY (product_id) REFERENCES Products(product_id),
    FOREIGN KEY (version_id) REFERENCES Product_Versions(version_id),
    FOREIGN KEY (supplier_id) REFERENCES Suppliers(supplier_id)
);

-- 6. Customers Table
CREATE TABLE IF NOT EXISTS Customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    phone_number TEXT,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Sales Table (FIXED)
CREATE TABLE IF NOT EXISTS Sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,          -- Logged-in user who records the sale
    customer_id INTEGER,
    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_amount REAL,
    discount_applied REAL DEFAULT 0,
    net_amount REAL,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);
-- 8. Sale Items Table (UPDATED)
CREATE TABLE IF NOT EXISTS Sale_Items (
    sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    version_id INTEGER NOT NULL,
    quantity_boxes INTEGER DEFAULT 0,
    unit_price REAL,
    total_price REAL,
    unit_cost REAL,
    total_cost REAL,
    profit REAL,
    FOREIGN KEY (sale_id) REFERENCES Sales(sale_id),
    FOREIGN KEY (product_id) REFERENCES Products(product_id),
    FOREIGN KEY (version_id) REFERENCES Product_Versions(version_id)
);

-- 9. Customer Credit Table
CREATE TABLE IF NOT EXISTS Customer_Credit (
    credit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    sale_id INTEGER NOT NULL,
    credit_amount REAL NOT NULL,
    status TEXT CHECK (status IN ('Paid','Unpaid')) DEFAULT 'Unpaid',
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id),
    FOREIGN KEY (sale_id) REFERENCES Sales(sale_id)
);

-- 10. Weekly Progress Table
CREATE TABLE IF NOT EXISTS Weekly_Progress (
    progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start_date TIMESTAMP NOT NULL,
    week_end_date TIMESTAMP NOT NULL,
    total_sales REAL,
    net_profit REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Stock Purchasing Record
CREATE TABLE IF NOT EXISTS StockPurchases (
    purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    version_id INTEGER,
    quantity_added INTEGER NOT NULL,
    purchase_price REAL,
    purchase_date TEXT NOT NULL,
    supplier_name TEXT,
    notes TEXT,
    FOREIGN KEY (product_id) REFERENCES Products(product_id),
    FOREIGN KEY (version_id) REFERENCES ProductVersions(version_id)
);
"""

def init_db():
    if not os.path.exists(DB_NAME):
        print(f"Database '{DB_NAME}' not found. Creating...")
        conn = sqlite3.connect(DB_NAME)
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        conn.close()
        print("Database and tables created successfully.")
    else:
        print(f"Database '{DB_NAME}' already exists. Skipping creation.")


def main():
    init_db()

    app = QApplication(sys.argv)
    login_window = LoginWindow()
    login_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()