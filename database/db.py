import sqlite3
import os
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "logitrack.db")


def get_db(path=None):
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path=None):
    conn = get_db(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def seed_db(path=None):
    conn = get_db(path)

    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        conn.close()
        return

    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@logitrack.com", generate_password_hash("demo123")),
    )
    conn.commit()

    user_id = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@logitrack.com",)
    ).fetchone()["id"]

    expenses = [
        (user_id, 12500.00, "Freight Charges",    "2026-05-01", "Sea freight Mumbai to Dubai"),
        (user_id,  3200.00, "Customs Duty",        "2026-05-02", "Import clearance charges"),
        (user_id,  1800.00, "Port Charges",        "2026-05-03", "Port handling fee JNPT"),
        (user_id,   950.00, "Documentation",       "2026-05-04", "Bill of lading and packing list"),
        (user_id,  4750.00, "Warehouse Charges",   "2026-05-05", "Cold storage 7 days"),
        (user_id,  2100.00, "Insurance",           "2026-05-06", "Marine cargo insurance premium"),
        (user_id,   680.00, "Courier & Shipping",  "2026-05-07", "Last-mile delivery documents"),
        (user_id,  1350.00, "Penalty & Demurrage", "2026-05-08", "Container detention charges"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()
