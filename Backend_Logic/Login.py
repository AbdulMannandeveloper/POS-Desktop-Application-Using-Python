import sqlite3
import hashlib
from session import current_user

DB_NAME = "POS.db"

def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def signup_admin(username: str, password: str):
    """Create the first Admin account (only once)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Check if admin already exists
    cursor.execute("SELECT * FROM Users WHERE role='Admin'")
    if cursor.fetchone():
        print("❌ Admin already exists. Cannot create another one.")
        conn.close()
        return False

    # Insert Admin
    cursor.execute("""
        INSERT INTO Users (username, password_hash, role)
        VALUES (?, ?, 'Admin')
    """, (username, hash_password(password)))

    conn.commit()
    conn.close()
    print("✅ Admin account created successfully.")
    return True

def signup_staff(username: str, password: str, role: str):
    """Create a Staff user account."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Users (username, password_hash, role)
            VALUES (?, ?, ?)
        """, (username, hash_password(password), role))
        conn.commit()
        print("✅ Staff account created successfully.")
        return True
    except sqlite3.IntegrityError:
        print("❌ Username already exists.")
        return False
    finally:
        conn.close()

def login(username: str, password: str):
    """General login (Admin or Staff)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, role FROM Users
        WHERE username=? AND password_hash=? AND status='Active'
    """, (username, hash_password(password)))

    user = cursor.fetchone()
    conn.close()

    if user:
        current_user["user_id"] = user[0]
        current_user["username"] = username
        current_user["role"] = user[1]
        print(f"✅ {user[1]} login successful. Welcome {username}.")
        return True
    else:
        print("❌ Invalid login credentials or account inactive.")
        return False
