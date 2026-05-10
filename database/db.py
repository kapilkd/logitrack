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

        CREATE TABLE IF NOT EXISTS vendors (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id            INTEGER NOT NULL REFERENCES users(id),
            vendor_code        TEXT    NOT NULL UNIQUE,
            vendor_name        TEXT    NOT NULL,
            vendor_type        TEXT    NOT NULL,
            vendor_category    TEXT    NOT NULL,
            company_name       TEXT,
            owner_name         TEXT,
            email              TEXT,
            phone              TEXT,
            alternate_phone    TEXT,
            website            TEXT,
            gst_number         TEXT,
            pan_number         TEXT,
            iec_code           TEXT,
            address_line1      TEXT,
            address_line2      TEXT,
            city               TEXT,
            state              TEXT,
            country            TEXT,
            pincode            TEXT,
            payment_terms_days INTEGER DEFAULT 0,
            credit_limit       REAL    DEFAULT 0,
            bank_name          TEXT,
            account_number     TEXT,
            ifsc_code          TEXT,
            upi_id             TEXT,
            currency           TEXT    DEFAULT 'INR',
            status             TEXT    NOT NULL DEFAULT 'ACTIVE',
            notes              TEXT,
            created_at         TEXT    DEFAULT (datetime('now')),
            updated_at         TEXT,
            created_by         INTEGER,
            updated_by         INTEGER
        );
    """)
    conn.commit()
    conn.close()


def seed_db(path=None):
    conn = get_db(path)

    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
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


def get_user_by_email(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row


def create_user(name, email, password_hash):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    conn.close()


def create_expense(user_id, amount, category, expense_date, description):
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description or None),
    )
    conn.commit()
    conn.close()


def get_expense_by_id(expense_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return row


def update_expense(expense_id, amount, category, expense_date, description):
    conn = get_db()
    conn.execute(
        "UPDATE expenses SET amount=?, category=?, date=?, description=? WHERE id=?",
        (amount, category, expense_date, description or None, expense_id),
    )
    conn.commit()
    conn.close()


def delete_expense(expense_id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def get_expense_summary(user_id):
    conn = get_db()
    totals = conn.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total_amount, COUNT(*) AS total_count "
        "FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    by_category = conn.execute(
        "SELECT category, SUM(amount) AS amount, COUNT(*) AS count "
        "FROM expenses WHERE user_id = ? GROUP BY category ORDER BY amount DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return {
        "total_amount": totals["total_amount"],
        "total_count": totals["total_count"],
        "by_category": [dict(row) for row in by_category],
    }


# ------------------------------------------------------------------ #
# Vendor CRUD                                                         #
# ------------------------------------------------------------------ #

def create_vendor(user_id, vendor_code, vendor_name, vendor_type, vendor_category,
                  company_name=None, owner_name=None, email=None, phone=None,
                  alternate_phone=None, website=None, gst_number=None, pan_number=None,
                  iec_code=None, address_line1=None, address_line2=None, city=None,
                  state=None, country=None, pincode=None, payment_terms_days=0,
                  credit_limit=0.0, bank_name=None, account_number=None, ifsc_code=None,
                  upi_id=None, currency="INR", status="ACTIVE", notes=None, created_by=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO vendors (user_id, vendor_code, vendor_name, vendor_type, vendor_category,"
        " company_name, owner_name, email, phone, alternate_phone, website, gst_number,"
        " pan_number, iec_code, address_line1, address_line2, city, state, country, pincode,"
        " payment_terms_days, credit_limit, bank_name, account_number, ifsc_code, upi_id,"
        " currency, status, notes, created_by)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, vendor_code, vendor_name, vendor_type, vendor_category,
         company_name, owner_name, email, phone, alternate_phone, website, gst_number,
         pan_number, iec_code, address_line1, address_line2, city, state, country, pincode,
         payment_terms_days, credit_limit, bank_name, account_number, ifsc_code, upi_id,
         currency, status, notes, created_by),
    )
    conn.commit()
    conn.close()


def get_vendor_by_id(vendor_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
    conn.close()
    return row


def get_vendor_by_code(vendor_code):
    conn = get_db()
    row = conn.execute("SELECT * FROM vendors WHERE vendor_code = ?", (vendor_code,)).fetchone()
    conn.close()
    return row


def get_vendors_by_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM vendors WHERE user_id = ? ORDER BY vendor_name ASC", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def update_vendor(vendor_id, vendor_code, vendor_name, vendor_type, vendor_category,
                  company_name=None, owner_name=None, email=None, phone=None,
                  alternate_phone=None, website=None, gst_number=None, pan_number=None,
                  iec_code=None, address_line1=None, address_line2=None, city=None,
                  state=None, country=None, pincode=None, payment_terms_days=0,
                  credit_limit=0.0, bank_name=None, account_number=None, ifsc_code=None,
                  upi_id=None, currency="INR", status="ACTIVE", notes=None, updated_by=None):
    conn = get_db()
    conn.execute(
        "UPDATE vendors SET vendor_code=?, vendor_name=?, vendor_type=?, vendor_category=?,"
        " company_name=?, owner_name=?, email=?, phone=?, alternate_phone=?, website=?,"
        " gst_number=?, pan_number=?, iec_code=?, address_line1=?, address_line2=?, city=?,"
        " state=?, country=?, pincode=?, payment_terms_days=?, credit_limit=?, bank_name=?,"
        " account_number=?, ifsc_code=?, upi_id=?, currency=?, status=?, notes=?, updated_by=?,"
        " updated_at=datetime('now') WHERE id=?",
        (vendor_code, vendor_name, vendor_type, vendor_category, company_name, owner_name,
         email, phone, alternate_phone, website, gst_number, pan_number, iec_code,
         address_line1, address_line2, city, state, country, pincode, payment_terms_days,
         credit_limit, bank_name, account_number, ifsc_code, upi_id, currency, status,
         notes, updated_by, vendor_id),
    )
    conn.commit()
    conn.close()


def delete_vendor(vendor_id):
    conn = get_db()
    conn.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
    conn.commit()
    conn.close()


def get_vendor_count(user_id):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM vendors WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    conn.close()
    return count
