# products_n_stock.py
import sqlite3
from session import current_user

DB_NAME = "POS.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

# ------------------ PRODUCT MANAGEMENT ------------------

def add_product(product_code, product_name, category=None, pieces_per_box=1):
    """Add a new product to Products table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Products (product_code, product_name, category, pieces_per_box)
            VALUES (?, ?, ?, ?)
        """, (product_code, product_name, category, pieces_per_box))
        conn.commit()
        print(f"✅ Product '{product_name}' added successfully.")
        return True
    except sqlite3.IntegrityError:
        print("❌ Product code already exists.")
        return False
    finally:
        conn.close()


def add_product_version(product_id, unit_selling_price, box_cost_price,
                        box_selling_price, stock_boxes, supplier_name="N/A", notes=""):
    """
    Add a new product version.
    Older versions remain with their stock until sold out.
    Also records stock purchase for reporting.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Insert the new product version
    cursor.execute("""
        INSERT INTO Product_Versions
        (product_id, unit_selling_price, box_cost_price, box_selling_price, current_stock_boxes, valid_from)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (product_id, unit_selling_price, box_cost_price, box_selling_price, stock_boxes))

    version_id = cursor.lastrowid  # Get the version ID for logging purchase

    # Commit before calling record_stock_purchase (to avoid lock)
    conn.commit()
    conn.close()

    # Log the purchase in StockPurchases
    record_stock_purchase(
        product_id=product_id,
        version_id=version_id,
        qty=stock_boxes,
        price=box_cost_price,
        supplier=supplier_name,
        notes=notes
    )

    print(f"✅ New version added for Product ID {product_id}. Stock: {stock_boxes} boxes.")
    print(f"🧾 Stock purchase recorded for supplier '{supplier_name}'.")
    return True


def customer_stock_return(sale_id, product_id, quantity_boxes):
    """
    Handle customer return → 
    1. Increase stock of the product version.
    2. Update Sale_Items (reduce qty, total, profit).
    3. Update Sales totals accordingly.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Find the sale item entry
    cursor.execute("""
        SELECT si.version_id, si.quantity_boxes, si.unit_price, si.total_price, si.profit
        FROM Sale_Items si
        WHERE si.sale_id=? AND si.product_id=?
    """, (sale_id, product_id))
    result = cursor.fetchone()

    if not result:
        print("❌ No sale found for this product.")
        conn.close()
        return False

    version_id, sold_qty, unit_price, total_price, profit = result

    if quantity_boxes > sold_qty:
        print("⚠️ Return quantity is greater than sold quantity. Operation cancelled.")
        conn.close()
        return False

    # ---- 1. Restore stock ----
    cursor.execute("""
        UPDATE Product_Versions
        SET current_stock_boxes = current_stock_boxes + ?
        WHERE version_id=?
    """, (quantity_boxes, version_id))

    # ---- 2. Update Sale_Items ----
    new_qty = sold_qty - quantity_boxes
    new_total = unit_price * new_qty
    profit_per_box = (profit / sold_qty) if sold_qty > 0 else 0
    new_profit = profit_per_box * new_qty

    if new_qty > 0:
        cursor.execute("""
            UPDATE Sale_Items
            SET quantity_boxes=?, total_price=?, profit=?
            WHERE sale_id=? AND product_id=?
        """, (new_qty, new_total, new_profit, sale_id, product_id))
    else:
        # If all items returned → delete row
        cursor.execute("""
            DELETE FROM Sale_Items
            WHERE sale_id=? AND product_id=?
        """, (sale_id, product_id))

    # ---- 3. Update Sales table totals ----
    cursor.execute("""
        SELECT SUM(total_price), SUM(profit)
        FROM Sale_Items
        WHERE sale_id=?
    """, (sale_id,))
    row = cursor.fetchone()
    new_total_amount = row[0] or 0
    new_profit_total = row[1] or 0

    # Fetch discount from original sale (unchanged)
    cursor.execute("SELECT discount_applied FROM Sales WHERE sale_id=?", (sale_id,))
    discount = cursor.fetchone()[0] or 0

    new_net = new_total_amount - discount

    cursor.execute("""
        UPDATE Sales
        SET total_amount=?, net_amount=?
        WHERE sale_id=?
    """, (new_total_amount, new_net, sale_id))

    conn.commit()
    conn.close()

    print(f"✅ Customer return processed. {quantity_boxes} boxes restored to Version {version_id}.")
    print(f"   Sale {sale_id} updated → total {new_total_amount:.2f}, net {new_net:.2f}, profit {new_profit_total:.2f}")
    return True


def supplier_stock_return(product_id, quantity_boxes):
    """
    Handle stock return to supplier.
    Deduct from the latest product version first, then older ones if needed.
    If total available stock < quantity_boxes → return error.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Get all versions (latest first) with stock
    cursor.execute("""
        SELECT version_id, current_stock_boxes
        FROM Product_Versions
        WHERE product_id=?
        ORDER BY valid_from DESC
    """, (product_id,))
    versions = cursor.fetchall()

    if not versions:
        print("❌ No product versions found.")
        conn.close()
        return False

    total_stock = sum(v[1] for v in versions)
    if total_stock < quantity_boxes:
        print(f"❌ Not enough stock to return. Available: {total_stock}, Requested: {quantity_boxes}")
        conn.close()
        return False

    # 2. Deduct stock starting from latest version
    to_return = quantity_boxes
    for version_id, stock in versions:
        if to_return <= 0:
            break

        if stock >= to_return:
            cursor.execute("""
                UPDATE Product_Versions
                SET current_stock_boxes = current_stock_boxes - ?
                WHERE version_id=?
            """, (to_return, version_id))
            print(f"✅ Deducted {to_return} boxes from Version {version_id}.")
            to_return = 0
        else:
            cursor.execute("""
                UPDATE Product_Versions
                SET current_stock_boxes = 0
                WHERE version_id=?
            """, (version_id,))
            print(f"✅ Deducted {stock} boxes from Version {version_id}.")
            to_return -= stock

    conn.commit()
    conn.close()

    print(f"✅ Supplier return of {quantity_boxes} boxes processed successfully.")
    return True


# ------------------ STOCK UTILITIES ------------------

def get_product_stock(product_id):
    """
    Return total available stock across all versions.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(current_stock_boxes) FROM Product_Versions
        WHERE product_id = ?
    """, (product_id,))
    total_stock = cursor.fetchone()[0]
    conn.close()
    return total_stock or 0


def list_product_versions(product_id):
    """
    Return list of all versions of a product with details.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT version_id, unit_selling_price, box_cost_price, box_selling_price,
               current_stock_boxes, valid_from, valid_to
        FROM Product_Versions
        WHERE product_id = ?
        ORDER BY valid_from DESC
    """, (product_id,))
    versions = cursor.fetchall()
    conn.close()

    return [
        {
            "version_id": v[0],
            "unit_selling_price": v[1],
            "box_cost_price": v[2],
            "box_selling_price": v[3],
            "current_stock_boxes": v[4],
            "valid_from": v[5],
            "valid_to": v[6]
        }
        for v in versions
    ]
# ===============================
# Editable Update Functions
# ===============================

def update_product_field(product_id, field, new_value):
    """Update a specific field of the Products table."""
    allowed_fields = ["product_name", "category", "pieces_per_box"]
    if field not in allowed_fields:
        raise ValueError("Invalid field for product update")

    conn = sqlite3.connect("pos.db")
    c = conn.cursor()
    query = f"UPDATE Products SET {field} = ? WHERE product_id = ?"
    c.execute(query, (new_value, product_id))
    conn.commit()
    conn.close()


def update_version_field(version_id, field, new_value):
    """Update a specific field of the Product_Versions table."""
    allowed_fields = ["current_stock_boxes", "unit_selling_price", "box_cost_price", "box_selling_price"]
    if field not in allowed_fields:
        raise ValueError("Invalid field for version update")

    conn = sqlite3.connect("pos.db")
    c = conn.cursor()
    query = f"UPDATE Product_Versions SET {field} = ? WHERE version_id = ?"
    c.execute(query, (new_value, version_id))
    conn.commit()
    conn.close()

def record_stock_purchase(product_id, version_id, qty, price, supplier, notes=""):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO StockPurchases (product_id, version_id, quantity_added, purchase_price, purchase_date, supplier_name, notes)
        VALUES (?, ?, ?, ?, DATE('now'), ?, ?)
    """, (product_id, version_id, qty, price, supplier, notes))
    conn.commit()
    conn.close()


def delete_product_safely(product_id):
    """
    Deletes a product ONLY if it has no associated sales.
    Returns: (bool, message)
    """
    conn = sqlite3.connect("POS.db")
    cur = conn.cursor()
    
    try:
        # 1. Check for sales
        cur.execute("SELECT COUNT(*) FROM Sale_Items WHERE product_id = ?", (product_id,))
        if cur.fetchone()[0] > 0:
            return False, "Cannot delete: Product has existing sales records. Archive it instead."

        # 2. Delete dependencies (Versions, Stock Transactions)
        cur.execute("DELETE FROM Stock_Transactions WHERE product_id = ?", (product_id,))
        cur.execute("DELETE FROM Product_Versions WHERE product_id = ?", (product_id,))
        
        # 3. Delete the Product
        cur.execute("DELETE FROM Products WHERE product_id = ?", (product_id,))
        
        conn.commit()
        return True, "Product deleted successfully."
        
    except Exception as e:
        conn.rollback()
        return False, f"Error: {e}"
    finally:
        conn.close()

# Append this to Backend_Logic/Products_n_Stocks.py

def delete_version_safely(version_id):
    """
    Deletes a specific stock version (batch) ONLY if it has no associated sales.
    Returns: (bool, message)
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    try:
        # 1. Check for sales dependencies
        # We check if this specific version_id exists in Sale_Items
        cur.execute("SELECT COUNT(*) FROM Sale_Items WHERE version_id = ?", (version_id,))
        count = cur.fetchone()[0]
        
        if count > 0:
            return False, f"Cannot delete: This version has {count} associated sales records."

        # 2. Delete the Version
        cur.execute("DELETE FROM Product_Versions WHERE version_id = ?", (version_id,))
        
        # Optional: You might want to remove the StockPurchase record too if it was a mistake entry
        # cur.execute("DELETE FROM StockPurchases WHERE version_id = ?", (version_id,))
        
        conn.commit()
        return True, "Stock version deleted successfully."
        
    except Exception as e:
        conn.rollback()
        return False, f"Error: {e}"
    finally:
        conn.close()
