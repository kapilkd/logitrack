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

        CREATE TABLE IF NOT EXISTS shipments (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id           INTEGER NOT NULL REFERENCES users(id),
            shipment_number   TEXT    NOT NULL,
            origin            TEXT,
            destination       TEXT,
            carrier           TEXT,
            status            TEXT    NOT NULL DEFAULT 'DRAFT',
            shipment_date     TEXT,
            etd               TEXT,
            eta               TEXT,
            port_of_loading   TEXT,
            port_of_discharge TEXT,
            incoterms         TEXT,
            description       TEXT,
            created_at        TEXT    DEFAULT (datetime('now')),
            updated_at        TEXT
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            shipment_id INTEGER REFERENCES shipments(id) ON DELETE SET NULL,
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

        CREATE TABLE IF NOT EXISTS vendor_contacts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id  INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
            name       TEXT    NOT NULL,
            title      TEXT,
            phone      TEXT,
            email      TEXT,
            is_primary INTEGER NOT NULL DEFAULT 0,
            notes      TEXT,
            created_at TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS shipment_vendors (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id         INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
            shipment_id       INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
            relationship_type TEXT    NOT NULL,
            billing_type      TEXT    NOT NULL,
            amount            REAL    DEFAULT 0,
            currency          TEXT    DEFAULT 'INR',
            invoice_number    TEXT,
            invoice_date      TEXT,
            due_date          TEXT,
            payment_status    TEXT    NOT NULL DEFAULT 'PENDING',
            notes             TEXT
        );
    """)
    conn.commit()
    try:
        conn.execute(
            "ALTER TABLE expenses ADD COLUMN"
            " shipment_id INTEGER REFERENCES shipments(id) ON DELETE SET NULL"
        )
        conn.commit()
    except Exception:
        pass
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

    if conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0] == 0:
        user_row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@logitrack.com",)
        ).fetchone()
        if user_row:
            uid = user_row["id"]
            vendors = [
                (uid, 'VND001', 'Maersk India Pvt Ltd',      'INBOUND',  'SHIPPING_LINE',
                 'Maersk India Pvt Ltd',           None, None, None, None, None, None, None, None,
                 'JNPT Road', None, 'Mumbai',    'Maharashtra', 'India', '400707',
                 30, 100000.0, None, None, None, None, 'INR', 'ACTIVE', None, uid),
                (uid, 'VND002', 'Blue Dart Express',          'OUTBOUND', 'TRANSPORTER',
                 'Blue Dart Express Ltd',           None, None, None, None, None, None, None, None,
                 'Nehru Place', None, 'Delhi',   'Delhi',       'India', '110019',
                 15,  50000.0, None, None, None, None, 'INR', 'ACTIVE', None, uid),
                (uid, 'VND003', 'Customs Plus Clearance',     'INBOUND',  'CUSTOM_CLEARANCE_AGENT',
                 'Customs Plus Clearance Pvt Ltd', None, None, None, None, None, None, None, None,
                 'BKC',        None, 'Mumbai',    'Maharashtra', 'India', '400051',
                 45, 200000.0, None, None, None, None, 'INR', 'ACTIVE', None, uid),
                (uid, 'VND004', 'Global Trade Partners',      'OUTBOUND', 'CUSTOMER',
                 'Global Trade Partners LLP',       None, None, None, None, None, None, None, None,
                 'MG Road',    None, 'Bangalore', 'Karnataka',   'India', '560001',
                 60, 500000.0, None, None, None, None, 'INR', 'ACTIVE', None, uid),
                (uid, 'VND005', 'SecureFreight Insurance',    'INBOUND',  'INSURANCE_PROVIDER',
                 'SecureFreight Insurance Co',      None, None, None, None, None, None, None, None,
                 'Anna Salai', None, 'Chennai',   'Tamil Nadu',  'India', '600002',
                 30, 150000.0, None, None, None, None, 'INR', 'ACTIVE', None, uid),
            ]
            conn.executemany(
                "INSERT INTO vendors"
                " (user_id, vendor_code, vendor_name, vendor_type, vendor_category,"
                "  company_name, owner_name, email, phone, alternate_phone, website, gst_number,"
                "  pan_number, iec_code, address_line1, address_line2, city, state, country, pincode,"
                "  payment_terms_days, credit_limit, bank_name, account_number, ifsc_code, upi_id,"
                "  currency, status, notes, created_by)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                vendors,
            )
            conn.commit()

    if conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0] == 0:
        user_row = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("demo@logitrack.com",)
        ).fetchone()
        if user_row:
            uid = user_row["id"]
            shp_rows = [
                (uid, 'SHP-2026-001', 'Mumbai, India',  'Dubai, UAE',   'Maersk Line',    'IN_TRANSIT',
                 '2026-04-28', '2026-04-29', '2026-05-10', 'JNPT',            'Jebel Ali Port',  'FOB',
                 'Sea freight consignment — electronics components'),
                (uid, 'SHP-2026-002', 'Delhi, India',   'Singapore',    'Blue Dart',      'DELIVERED',
                 '2026-05-03', '2026-05-03', '2026-05-07', 'IGI Airport',     'Changi Airport',  'CIF',
                 'Air freight — pharmaceutical samples'),
                (uid, 'SHP-2026-003', 'Chennai, India', 'London, UK',   'Air India Cargo','ACTIVE',
                 '2026-05-06', '2026-05-07', '2026-05-14', 'Chennai Airport', 'Heathrow Airport','DDP',
                 'International courier — textile exports'),
            ]
            conn.executemany(
                "INSERT INTO shipments"
                " (user_id, shipment_number, origin, destination, carrier, status,"
                "  shipment_date, etd, eta, port_of_loading, port_of_discharge, incoterms, description)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                shp_rows,
            )
            conn.commit()

            shp1 = conn.execute(
                "SELECT id FROM shipments WHERE shipment_number = ?", ('SHP-2026-001',)
            ).fetchone()["id"]
            shp2 = conn.execute(
                "SELECT id FROM shipments WHERE shipment_number = ?", ('SHP-2026-002',)
            ).fetchone()["id"]
            shp3 = conn.execute(
                "SELECT id FROM shipments WHERE shipment_number = ?", ('SHP-2026-003',)
            ).fetchone()["id"]

            conn.execute(
                "UPDATE expenses SET shipment_id = ?"
                " WHERE user_id = ? AND date BETWEEN '2026-05-01' AND '2026-05-04'"
                " AND shipment_id IS NULL",
                (shp1, uid),
            )
            conn.execute(
                "UPDATE expenses SET shipment_id = ?"
                " WHERE user_id = ? AND date BETWEEN '2026-05-05' AND '2026-05-06'"
                " AND shipment_id IS NULL",
                (shp2, uid),
            )
            conn.execute(
                "UPDATE expenses SET shipment_id = ?"
                " WHERE user_id = ? AND date BETWEEN '2026-05-07' AND '2026-05-08'"
                " AND shipment_id IS NULL",
                (shp3, uid),
            )
            conn.commit()

    if conn.execute("SELECT COUNT(*) FROM shipment_vendors").fetchone()[0] == 0:
        vnd = {}
        for code in ('VND001', 'VND002', 'VND003', 'VND004', 'VND005'):
            row = conn.execute(
                "SELECT id FROM vendors WHERE vendor_code = ?", (code,)
            ).fetchone()
            if row:
                vnd[code] = row["id"]
        if len(vnd) < 5:
            available = conn.execute(
                "SELECT id FROM vendors ORDER BY id LIMIT 5"
            ).fetchall()
            codes = ['VND001', 'VND002', 'VND003', 'VND004', 'VND005']
            for i, row in enumerate(available):
                if codes[i] not in vnd:
                    vnd[codes[i]] = row["id"]
        shp = {}
        for num in ('SHP-2026-001', 'SHP-2026-002', 'SHP-2026-003'):
            row = conn.execute(
                "SELECT id FROM shipments WHERE shipment_number = ?", (num,)
            ).fetchone()
            if row:
                shp[num] = row["id"]
        if len(vnd) >= 1 and len(shp) >= 1:
            candidates = [
                ('VND001', 'SHP-2026-001', 'TRANSPORTER',    'PAYABLE',
                 12500.00, 'INR', 'INV-2026-001', '2026-04-28', '2026-05-31', 'PAID',    'Sea freight — Maersk Line'),
                ('VND003', 'SHP-2026-001', 'CLEARING_AGENT', 'PAYABLE',
                  3200.00, 'INR', 'INV-2026-002', '2026-05-02', '2026-06-01', 'PENDING', 'Customs clearance JNPT'),
                ('VND004', 'SHP-2026-001', 'CUSTOMER',       'RECEIVABLE',
                 85000.00, 'INR', 'INV-2026-003', '2026-05-01', '2026-05-31', 'PENDING', 'Invoice to Global Trade Partners'),
                ('VND002', 'SHP-2026-002', 'TRANSPORTER',    'PAYABLE',
                  4750.00, 'INR', 'INV-2026-004', '2026-05-03', '2026-06-02', 'PARTIAL', 'Air freight Blue Dart'),
                ('VND004', 'SHP-2026-002', 'CONSIGNEE',      'RECEIVABLE',
                 65000.00, 'INR', 'INV-2026-005', '2026-05-03', '2026-06-02', 'PAID',    'Delivery confirmed — Singapore'),
                ('VND001', 'SHP-2026-003', 'TRANSPORTER',    'PAYABLE',
                  8200.00, 'INR', 'INV-2026-006', '2026-05-06', '2026-06-05', 'OVERDUE', 'Air India Cargo charges'),
                ('VND005', 'SHP-2026-003', 'CLEARING_AGENT', 'PAYABLE',
                  2100.00, 'INR', 'INV-2026-007', '2026-05-07', '2026-06-06', 'PENDING', 'Marine insurance — textile exports'),
            ]
            sv_rows = [
                (vnd[vc], shp[sn], rt, bt, amt, cur, inv, invd, due, ps, notes)
                for vc, sn, rt, bt, amt, cur, inv, invd, due, ps, notes in candidates
                if vc in vnd and sn in shp
            ]
            if sv_rows:
                conn.executemany(
                    "INSERT INTO shipment_vendors"
                    " (vendor_id, shipment_id, relationship_type, billing_type, amount, currency,"
                    "  invoice_number, invoice_date, due_date, payment_status, notes)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    sv_rows,
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


def create_expense(user_id, amount, category, expense_date, description, shipment_id=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description, shipment_id)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description or None, shipment_id),
    )
    conn.commit()
    conn.close()


def get_expense_by_id(expense_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return row


def update_expense(expense_id, amount, category, expense_date, description, shipment_id=None):
    conn = get_db()
    conn.execute(
        "UPDATE expenses SET amount=?, category=?, date=?, description=?, shipment_id=? WHERE id=?",
        (amount, category, expense_date, description or None, shipment_id, expense_id),
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


def get_all_vendors():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM vendors ORDER BY vendor_name ASC"
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


def create_contact(vendor_id, name, title=None, phone=None,
                   email=None, is_primary=0, notes=None):
    conn = get_db()
    if is_primary:
        conn.execute(
            "UPDATE vendor_contacts SET is_primary = 0 WHERE vendor_id = ?",
            (vendor_id,)
        )
    conn.execute(
        "INSERT INTO vendor_contacts (vendor_id, name, title, phone, email, is_primary, notes)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (vendor_id, name, title or None, phone or None,
         email or None, 1 if is_primary else 0, notes or None),
    )
    conn.commit()
    conn.close()


def get_contacts_by_vendor(vendor_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM vendor_contacts WHERE vendor_id = ?"
        " ORDER BY is_primary DESC, name ASC",
        (vendor_id,)
    ).fetchall()
    conn.close()
    return rows


def get_contact_by_id(contact_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM vendor_contacts WHERE id = ?", (contact_id,)
    ).fetchone()
    conn.close()
    return row


def update_contact(contact_id, vendor_id, name, title=None,
                   phone=None, email=None, is_primary=0, notes=None):
    conn = get_db()
    if is_primary:
        conn.execute(
            "UPDATE vendor_contacts SET is_primary = 0"
            " WHERE vendor_id = ? AND id != ?",
            (vendor_id, contact_id)
        )
    conn.execute(
        "UPDATE vendor_contacts SET name=?, title=?, phone=?, email=?, is_primary=?, notes=?"
        " WHERE id=?",
        (name, title or None, phone or None, email or None,
         1 if is_primary else 0, notes or None, contact_id),
    )
    conn.commit()
    conn.close()


def delete_contact(contact_id):
    conn = get_db()
    conn.execute("DELETE FROM vendor_contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# Shipment CRUD                                                       #
# ------------------------------------------------------------------ #

SHIPMENT_STATUSES = ('DRAFT', 'ACTIVE', 'IN_TRANSIT', 'DELIVERED', 'CANCELLED')
INCOTERMS = ('EXW', 'FCA', 'FOB', 'CFR', 'CIF', 'CPT', 'CIP', 'DAP', 'DPU', 'DDP')


def create_shipment(user_id, shipment_number, origin=None, destination=None,
                    carrier=None, status='DRAFT', shipment_date=None,
                    etd=None, eta=None, port_of_loading=None,
                    port_of_discharge=None, incoterms=None, description=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO shipments"
        " (user_id, shipment_number, origin, destination, carrier, status,"
        "  shipment_date, etd, eta, port_of_loading, port_of_discharge, incoterms, description)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, shipment_number, origin, destination, carrier, status,
         shipment_date, etd, eta, port_of_loading, port_of_discharge, incoterms, description),
    )
    conn.commit()
    conn.close()


def get_shipment_by_id(shipment_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,)).fetchone()
    conn.close()
    return row


def get_shipments_by_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM shipments WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def update_shipment(shipment_id, shipment_number, origin=None, destination=None,
                    carrier=None, status='DRAFT', shipment_date=None,
                    etd=None, eta=None, port_of_loading=None,
                    port_of_discharge=None, incoterms=None, description=None):
    conn = get_db()
    conn.execute(
        "UPDATE shipments SET shipment_number=?, origin=?, destination=?, carrier=?,"
        " status=?, shipment_date=?, etd=?, eta=?, port_of_loading=?, port_of_discharge=?,"
        " incoterms=?, description=?, updated_at=datetime('now') WHERE id=?",
        (shipment_number, origin, destination, carrier, status, shipment_date,
         etd, eta, port_of_loading, port_of_discharge, incoterms, description, shipment_id),
    )
    conn.commit()
    conn.close()


def delete_shipment(shipment_id):
    conn = get_db()
    conn.execute("DELETE FROM shipments WHERE id = ?", (shipment_id,))
    conn.commit()
    conn.close()


def get_shipment_count(user_id):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM shipments WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


def get_shipment_by_number(shipment_number):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM shipments WHERE shipment_number = ?", (shipment_number,)
    ).fetchone()
    conn.close()
    return row


def get_expenses_by_shipment(shipment_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE shipment_id = ? ORDER BY date ASC", (shipment_id,)
    ).fetchall()
    conn.close()
    return rows


# ------------------------------------------------------------------ #
# Shipment-Vendor CRUD                                                #
# ------------------------------------------------------------------ #

RELATIONSHIP_TYPES = ('CUSTOMER', 'TRANSPORTER', 'CONSIGNEE', 'CLEARING_AGENT')
BILLING_TYPES      = ('PAYABLE', 'RECEIVABLE')
PAYMENT_STATUSES   = ('PENDING', 'PARTIAL', 'PAID', 'OVERDUE')


def create_shipment_vendor(vendor_id, shipment_id, relationship_type, billing_type,
                            amount=0, currency='INR', invoice_number=None,
                            invoice_date=None, due_date=None,
                            payment_status='PENDING', notes=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO shipment_vendors"
        " (vendor_id, shipment_id, relationship_type, billing_type, amount, currency,"
        "  invoice_number, invoice_date, due_date, payment_status, notes)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (vendor_id, shipment_id, relationship_type, billing_type,
         amount, currency, invoice_number, invoice_date, due_date,
         payment_status, notes),
    )
    conn.commit()
    conn.close()


def get_shipment_vendor_by_id(sv_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM shipment_vendors WHERE id = ?", (sv_id,)
    ).fetchone()
    conn.close()
    return row


def get_vendors_by_shipment(shipment_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT sv.*, v.vendor_name, v.vendor_code, v.vendor_category"
        " FROM shipment_vendors sv"
        " JOIN vendors v ON sv.vendor_id = v.id"
        " WHERE sv.shipment_id = ?"
        " ORDER BY v.vendor_name ASC",
        (shipment_id,),
    ).fetchall()
    conn.close()
    return rows


def get_shipments_by_vendor(vendor_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT sv.*, s.shipment_number, s.origin, s.destination, s.status, s.carrier"
        " FROM shipment_vendors sv"
        " JOIN shipments s ON sv.shipment_id = s.id"
        " WHERE sv.vendor_id = ?"
        " ORDER BY s.created_at DESC",
        (vendor_id,),
    ).fetchall()
    conn.close()
    return rows


def update_shipment_vendor(sv_id, relationship_type, billing_type,
                            amount=0, currency='INR', invoice_number=None,
                            invoice_date=None, due_date=None,
                            payment_status='PENDING', notes=None):
    conn = get_db()
    conn.execute(
        "UPDATE shipment_vendors"
        " SET relationship_type=?, billing_type=?, amount=?, currency=?,"
        "     invoice_number=?, invoice_date=?, due_date=?, payment_status=?, notes=?"
        " WHERE id=?",
        (relationship_type, billing_type, amount, currency,
         invoice_number, invoice_date, due_date, payment_status, notes, sv_id),
    )
    conn.commit()
    conn.close()


def delete_shipment_vendor(sv_id):
    conn = get_db()
    conn.execute("DELETE FROM shipment_vendors WHERE id = ?", (sv_id,))
    conn.commit()
    conn.close()


def get_shipment_vendor_count(shipment_id):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM shipment_vendors WHERE shipment_id = ?", (shipment_id,)
    ).fetchone()[0]
    conn.close()
    return count


def get_total_payables_by_shipment(shipment_id):
    conn = get_db()
    total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM shipment_vendors"
        " WHERE shipment_id = ? AND billing_type = 'PAYABLE'",
        (shipment_id,),
    ).fetchone()[0]
    conn.close()
    return float(total)


def get_total_receivables_by_shipment(shipment_id):
    conn = get_db()
    total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM shipment_vendors"
        " WHERE shipment_id = ? AND billing_type = 'RECEIVABLE'",
        (shipment_id,),
    ).fetchone()[0]
    conn.close()
    return float(total)
