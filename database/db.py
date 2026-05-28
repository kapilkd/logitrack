import datetime
import os
import psycopg2
from psycopg2.extras import DictCursor
from werkzeug.security import generate_password_hash

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:1234@localhost:5432/logitrack_db"
)


class _PgConn:
    """Thin wrapper giving psycopg2 a SQLite-like .execute() / .executemany() API."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        cur = self._conn.cursor(cursor_factory=DictCursor)
        cur.execute(sql, params or ())
        return cur

    def executemany(self, sql, seq_of_params):
        cur = self._conn.cursor(cursor_factory=DictCursor)
        cur.executemany(sql, seq_of_params)
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_db(path=None):
    conn = psycopg2.connect(DATABASE_URL)
    return _PgConn(conn)


def init_db(path=None):
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            SERIAL PRIMARY KEY,
            name          TEXT      NOT NULL,
            email         TEXT      UNIQUE NOT NULL,
            password_hash TEXT      NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            id                SERIAL PRIMARY KEY,
            user_id           INTEGER   NOT NULL REFERENCES users(id),
            shipment_number   TEXT      NOT NULL,
            origin            TEXT,
            destination       TEXT,
            carrier           TEXT,
            status            TEXT      NOT NULL DEFAULT 'DRAFT',
            shipment_date     TEXT,
            etd               TEXT,
            eta               TEXT,
            port_of_loading   TEXT,
            port_of_discharge TEXT,
            incoterms         TEXT,
            description       TEXT,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at        TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER   NOT NULL REFERENCES users(id),
            amount      REAL      NOT NULL,
            category    TEXT      NOT NULL,
            date        TEXT      NOT NULL,
            description TEXT,
            shipment_id INTEGER   REFERENCES shipments(id) ON DELETE SET NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id                 SERIAL PRIMARY KEY,
            user_id            INTEGER   NOT NULL REFERENCES users(id),
            vendor_code        TEXT      NOT NULL UNIQUE,
            vendor_name        TEXT      NOT NULL,
            vendor_type        TEXT      NOT NULL,
            vendor_category    TEXT      NOT NULL,
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
            payment_terms_days INTEGER   DEFAULT 0,
            credit_limit       REAL      DEFAULT 0,
            bank_name          TEXT,
            account_number     TEXT,
            ifsc_code          TEXT,
            upi_id             TEXT,
            currency           TEXT      NOT NULL DEFAULT 'INR',
            status             TEXT      NOT NULL DEFAULT 'ACTIVE',
            notes              TEXT,
            created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at         TIMESTAMP,
            created_by         INTEGER,
            updated_by         INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS vendor_contacts (
            id         SERIAL PRIMARY KEY,
            vendor_id  INTEGER   NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
            name       TEXT      NOT NULL,
            title      TEXT,
            phone      TEXT,
            email      TEXT,
            is_primary INTEGER   NOT NULL DEFAULT 0,
            notes      TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipment_vendors (
            id                SERIAL PRIMARY KEY,
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
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipment_vendor_payments (
            id                 SERIAL PRIMARY KEY,
            shipment_vendor_id INTEGER NOT NULL REFERENCES shipment_vendors(id) ON DELETE CASCADE,
            amount             REAL    NOT NULL,
            payment_date       TEXT    NOT NULL,
            reference          TEXT,
            notes              TEXT,
            created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_alerts (
            id           SERIAL PRIMARY KEY,
            user_id      INTEGER   NOT NULL REFERENCES users(id),
            entity_type  TEXT      NOT NULL,
            entity_id    INTEGER,
            entity_label TEXT,
            action       TEXT      NOT NULL,
            description  TEXT,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS company_profiles (
            id            SERIAL PRIMARY KEY,
            user_id       INTEGER   NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            company_name  TEXT,
            legal_name    TEXT,
            industry      TEXT,
            website       TEXT,
            email         TEXT,
            phone         TEXT,
            address_line1 TEXT,
            address_line2 TEXT,
            city          TEXT,
            state         TEXT,
            country       TEXT,
            pincode       TEXT,
            gst_number    TEXT,
            pan_number    TEXT,
            iec_code      TEXT,
            currency      TEXT      NOT NULL DEFAULT 'INR',
            incoterms     TEXT,
            logo_path     TEXT,
            billing_terms TEXT,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at    TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS gmail_accounts (
            id                SERIAL PRIMARY KEY,
            user_id           INTEGER   NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            gmail_email       TEXT      NOT NULL,
            google_account_id TEXT,
            access_token      TEXT      NOT NULL,
            refresh_token     TEXT      NOT NULL,
            token_expiry      TEXT,
            scope             TEXT,
            is_connected      INTEGER   DEFAULT 1,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at        TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id               SERIAL PRIMARY KEY,
            user_id          INTEGER   NOT NULL REFERENCES users(id),
            gmail_message_id TEXT      NOT NULL UNIQUE,
            gmail_thread_id  TEXT,
            direction        TEXT      NOT NULL,
            from_email       TEXT,
            from_name        TEXT,
            to_email         TEXT,
            to_name          TEXT,
            cc               TEXT,
            bcc              TEXT,
            subject          TEXT,
            body_plain       TEXT,
            body_html        TEXT,
            snippet          TEXT,
            status           TEXT      DEFAULT 'RECEIVED',
            label_names      TEXT,
            has_attachments  INTEGER   DEFAULT 0,
            received_at      TEXT,
            sent_at          TEXT,
            synced_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_attachments (
            id                  SERIAL PRIMARY KEY,
            email_id            INTEGER   NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
            filename            TEXT,
            mime_type           TEXT,
            gmail_attachment_id TEXT,
            file_path           TEXT,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS email_ai_processing (
            id                 SERIAL PRIMARY KEY,
            email_id           INTEGER   NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
            ai_summary         TEXT,
            detected_category  TEXT,
            extracted_entities TEXT,
            shipment_reference TEXT,
            invoice_reference  TEXT,
            processing_status  TEXT      DEFAULT 'PENDING',
            created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS particulars_types (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
            label      TEXT    NOT NULL,
            is_custom  BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (label)
        )
    """)

    _default_types = [
        'Air Freight', 'Exworks', 'Airline DO Fee', 'Delivery Fee',
        'Customs Clearance', 'House DO', 'CFS/AAI',
    ]
    for _lbl in _default_types:
        conn.execute(
            "INSERT INTO particulars_types (user_id, label, is_custom)"
            " VALUES (NULL, %s, FALSE) ON CONFLICT (label) DO NOTHING",
            (_lbl,)
        )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS enquiries (
            id                 SERIAL PRIMARY KEY,
            user_id            INTEGER   NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            enquiry_number     TEXT      NOT NULL,
            customer_name      TEXT,
            customer_email     TEXT,
            customer_phone     TEXT,
            customer_vendor_id INTEGER   REFERENCES vendors(id),
            commodity          TEXT,
            consignment_type   TEXT,
            shipment_terms     TEXT,
            weight             REAL      DEFAULT 0,
            weight_unit        TEXT      DEFAULT 'KGS',
            packages           INTEGER   DEFAULT 0,
            mawb               TEXT,
            hawb               TEXT,
            origin             TEXT,
            destination        TEXT,
            ex_rate            REAL      DEFAULT 0,
            incoterms          TEXT,
            currency           TEXT      NOT NULL DEFAULT 'INR',
            estimated_value    REAL      DEFAULT 0,
            status             TEXT      NOT NULL DEFAULT 'OPEN',
            priority           TEXT      NOT NULL DEFAULT 'NORMAL',
            enquiry_date       TEXT      NOT NULL,
            follow_up_date     TEXT,
            notes              TEXT,
            created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at         TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS enquiry_particulars (
            id              SERIAL PRIMARY KEY,
            enquiry_id      INTEGER NOT NULL REFERENCES enquiries(id) ON DELETE CASCADE,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            particular_type TEXT    NOT NULL,
            sac_hsn         TEXT,
            qty             INTEGER NOT NULL DEFAULT 1,
            ex_rate         REAL    NOT NULL DEFAULT 0,
            weight          REAL    NOT NULL DEFAULT 0,
            weight_unit     TEXT    NOT NULL DEFAULT 'KGS',
            offered_rate    REAL    NOT NULL DEFAULT 0,
            use_formula     BOOLEAN NOT NULL DEFAULT FALSE,
            expense         REAL    NOT NULL DEFAULT 0,
            tax_rate        REAL    NOT NULL DEFAULT 0,
            cgst            REAL    NOT NULL DEFAULT 0,
            sgst            REAL    NOT NULL DEFAULT 0,
            igst            REAL    NOT NULL DEFAULT 0,
            total           REAL    NOT NULL DEFAULT 0,
            currency        TEXT    NOT NULL DEFAULT 'INR',
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipment_particulars (
            id                    SERIAL PRIMARY KEY,
            shipment_id           INTEGER NOT NULL REFERENCES shipments(id) ON DELETE CASCADE,
            user_id               INTEGER NOT NULL REFERENCES users(id),
            particular_type       TEXT    NOT NULL,
            sac_hsn               TEXT,
            qty                   INTEGER NOT NULL DEFAULT 1,
            ex_rate               REAL    NOT NULL DEFAULT 0,
            weight                REAL    NOT NULL DEFAULT 0,
            weight_unit           TEXT    NOT NULL DEFAULT 'KGS',
            offered_rate          REAL    NOT NULL DEFAULT 0,
            use_formula           BOOLEAN NOT NULL DEFAULT FALSE,
            expense               REAL    NOT NULL DEFAULT 0,
            tax_rate              REAL    NOT NULL DEFAULT 0,
            cgst                  REAL    NOT NULL DEFAULT 0,
            sgst                  REAL    NOT NULL DEFAULT 0,
            igst                  REAL    NOT NULL DEFAULT 0,
            total                 REAL    NOT NULL DEFAULT 0,
            currency              TEXT    NOT NULL DEFAULT 'INR',
            enquiry_particular_id INTEGER,
            created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def seed_db(path=None):
    conn = get_db()

    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
            ("Demo User", "demo@logitrack.com", generate_password_hash("demo123")),
        )
        conn.commit()

        user_id = conn.execute(
            "SELECT id FROM users WHERE email = %s", ("demo@logitrack.com",)
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
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (%s, %s, %s, %s, %s)",
            expenses,
        )
        conn.commit()

    if conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0] == 0:
        user_row = conn.execute(
            "SELECT id FROM users WHERE email = %s", ("demo@logitrack.com",)
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
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
                "         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                vendors,
            )
            conn.commit()

    if conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0] == 0:
        user_row = conn.execute(
            "SELECT id FROM users WHERE email = %s", ("demo@logitrack.com",)
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
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                shp_rows,
            )
            conn.commit()

            shp1 = conn.execute(
                "SELECT id FROM shipments WHERE shipment_number = %s", ('SHP-2026-001',)
            ).fetchone()["id"]
            shp2 = conn.execute(
                "SELECT id FROM shipments WHERE shipment_number = %s", ('SHP-2026-002',)
            ).fetchone()["id"]
            shp3 = conn.execute(
                "SELECT id FROM shipments WHERE shipment_number = %s", ('SHP-2026-003',)
            ).fetchone()["id"]

            conn.execute(
                "UPDATE expenses SET shipment_id = %s"
                " WHERE user_id = %s AND date BETWEEN '2026-05-01' AND '2026-05-04'"
                " AND shipment_id IS NULL",
                (shp1, uid),
            )
            conn.execute(
                "UPDATE expenses SET shipment_id = %s"
                " WHERE user_id = %s AND date BETWEEN '2026-05-05' AND '2026-05-06'"
                " AND shipment_id IS NULL",
                (shp2, uid),
            )
            conn.execute(
                "UPDATE expenses SET shipment_id = %s"
                " WHERE user_id = %s AND date BETWEEN '2026-05-07' AND '2026-05-08'"
                " AND shipment_id IS NULL",
                (shp3, uid),
            )
            conn.commit()

    if conn.execute("SELECT COUNT(*) FROM shipment_vendors").fetchone()[0] == 0:
        vnd = {}
        for code in ('VND001', 'VND002', 'VND003', 'VND004', 'VND005'):
            row = conn.execute(
                "SELECT id FROM vendors WHERE vendor_code = %s", (code,)
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
                "SELECT id FROM shipments WHERE shipment_number = %s", (num,)
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
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    sv_rows,
                )
                conn.commit()

    conn.close()


def get_user_by_email(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()
    conn.close()
    return row


def create_user(name, email, password_hash):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
        (name, email, password_hash),
    )
    conn.commit()
    conn.close()


def create_expense(user_id, amount, category, expense_date, description, shipment_id=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description, shipment_id)"
        " VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, amount, category, expense_date, description or None, shipment_id),
    )
    conn.commit()
    conn.close()


def get_expense_by_id(expense_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,)).fetchone()
    conn.close()
    return row


def update_expense(expense_id, amount, category, expense_date, description, shipment_id=None):
    conn = get_db()
    conn.execute(
        "UPDATE expenses SET amount=%s, category=%s, date=%s, description=%s, shipment_id=%s"
        " WHERE id=%s",
        (amount, category, expense_date, description or None, shipment_id, expense_id),
    )
    conn.commit()
    conn.close()


def delete_expense(expense_id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    conn.commit()
    conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
    conn.close()
    return row


def get_expense_summary(user_id):
    conn = get_db()
    totals = conn.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total_amount, COUNT(*) AS total_count"
        " FROM expenses WHERE user_id = %s",
        (user_id,),
    ).fetchone()
    by_category = conn.execute(
        "SELECT category, SUM(amount) AS amount, COUNT(*) AS count"
        " FROM expenses WHERE user_id = %s GROUP BY category ORDER BY amount DESC",
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
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
        "         %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
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
    row = conn.execute("SELECT * FROM vendors WHERE id = %s", (vendor_id,)).fetchone()
    conn.close()
    return row


def get_vendor_by_code(vendor_code):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM vendors WHERE vendor_code = %s", (vendor_code,)
    ).fetchone()
    conn.close()
    return row


def get_vendors_by_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM vendors WHERE user_id = %s ORDER BY vendor_name ASC", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_all_vendors(user_id=None):
    conn = get_db()
    if user_id is not None:
        rows = conn.execute(
            "SELECT * FROM vendors WHERE user_id = %s ORDER BY vendor_name ASC", (user_id,)
        ).fetchall()
    else:
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
        "UPDATE vendors SET vendor_code=%s, vendor_name=%s, vendor_type=%s, vendor_category=%s,"
        " company_name=%s, owner_name=%s, email=%s, phone=%s, alternate_phone=%s, website=%s,"
        " gst_number=%s, pan_number=%s, iec_code=%s, address_line1=%s, address_line2=%s, city=%s,"
        " state=%s, country=%s, pincode=%s, payment_terms_days=%s, credit_limit=%s, bank_name=%s,"
        " account_number=%s, ifsc_code=%s, upi_id=%s, currency=%s, status=%s, notes=%s,"
        " updated_by=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
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
    conn.execute("DELETE FROM vendors WHERE id = %s", (vendor_id,))
    conn.commit()
    conn.close()


def get_vendor_count(user_id):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM vendors WHERE user_id = %s", (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


def create_contact(vendor_id, name, title=None, phone=None,
                   email=None, is_primary=0, notes=None):
    conn = get_db()
    if is_primary:
        conn.execute(
            "UPDATE vendor_contacts SET is_primary = 0 WHERE vendor_id = %s",
            (vendor_id,)
        )
    conn.execute(
        "INSERT INTO vendor_contacts (vendor_id, name, title, phone, email, is_primary, notes)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (vendor_id, name, title or None, phone or None,
         email or None, 1 if is_primary else 0, notes or None),
    )
    conn.commit()
    conn.close()


def get_contacts_by_vendor(vendor_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM vendor_contacts WHERE vendor_id = %s"
        " ORDER BY is_primary DESC, name ASC",
        (vendor_id,)
    ).fetchall()
    conn.close()
    return rows


def get_contact_by_id(contact_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM vendor_contacts WHERE id = %s", (contact_id,)
    ).fetchone()
    conn.close()
    return row


def update_contact(contact_id, vendor_id, name, title=None,
                   phone=None, email=None, is_primary=0, notes=None):
    conn = get_db()
    if is_primary:
        conn.execute(
            "UPDATE vendor_contacts SET is_primary = 0"
            " WHERE vendor_id = %s AND id != %s",
            (vendor_id, contact_id)
        )
    conn.execute(
        "UPDATE vendor_contacts SET name=%s, title=%s, phone=%s, email=%s, is_primary=%s, notes=%s"
        " WHERE id=%s",
        (name, title or None, phone or None, email or None,
         1 if is_primary else 0, notes or None, contact_id),
    )
    conn.commit()
    conn.close()


def delete_contact(contact_id):
    conn = get_db()
    conn.execute("DELETE FROM vendor_contacts WHERE id = %s", (contact_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# Shipment CRUD                                                       #
# ------------------------------------------------------------------ #

SHIPMENT_STATUSES = (
    'DRAFT', 'BOOKED', 'PICKUP_PENDING', 'PICKED_UP',
    'IN_TRANSIT', 'AT_WAREHOUSE', 'CUSTOMS_CLEARANCE', 'CUSTOMS_HOLD',
    'PORT_IN', 'PORT_OUT', 'SAILED', 'ARRIVED',
    'DESTINATION_CUSTOMS', 'OUT_FOR_DELIVERY',
    'DELIVERED', 'PARTIALLY_DELIVERED', 'RETURNED',
    'CANCELLED', 'ON_HOLD', 'DELAYED', 'CLOSED',
)
INCOTERMS = ('EXW', 'FCA', 'FOB', 'CFR', 'CIF', 'CPT', 'CIP', 'DAP', 'DPU', 'DDP')


def create_shipment(user_id, shipment_number, origin=None, destination=None,
                    carrier=None, status='DRAFT', shipment_date=None,
                    etd=None, eta=None, port_of_loading=None,
                    port_of_discharge=None, incoterms=None, description=None,
                    enquiry_id=None):
    conn = get_db()
    row = conn.execute(
        "INSERT INTO shipments"
        " (user_id, shipment_number, origin, destination, carrier, status,"
        "  shipment_date, etd, eta, port_of_loading, port_of_discharge, incoterms, description, enquiry_id)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        " RETURNING *",
        (user_id, shipment_number, origin, destination, carrier, status,
         shipment_date, etd, eta, port_of_loading, port_of_discharge, incoterms, description, enquiry_id),
    ).fetchone()
    conn.commit()
    conn.close()
    return row


def get_shipment_by_id(shipment_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM shipments WHERE id = %s", (shipment_id,)
    ).fetchone()
    conn.close()
    return row


def get_shipments_by_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM shipments WHERE user_id = %s ORDER BY created_at DESC", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def update_shipment(shipment_id, shipment_number, origin=None, destination=None,
                    carrier=None, status='DRAFT', shipment_date=None,
                    etd=None, eta=None, port_of_loading=None,
                    port_of_discharge=None, incoterms=None, description=None):
    conn = get_db()
    conn.execute(
        "UPDATE shipments SET shipment_number=%s, origin=%s, destination=%s, carrier=%s,"
        " status=%s, shipment_date=%s, etd=%s, eta=%s, port_of_loading=%s,"
        " port_of_discharge=%s, incoterms=%s, description=%s, updated_at=CURRENT_TIMESTAMP"
        " WHERE id=%s",
        (shipment_number, origin, destination, carrier, status, shipment_date,
         etd, eta, port_of_loading, port_of_discharge, incoterms, description, shipment_id),
    )
    conn.commit()
    conn.close()


def update_shipment_status(shipment_id, status):
    conn = get_db()
    conn.execute(
        "UPDATE shipments SET status=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s",
        (status, shipment_id),
    )
    conn.commit()
    conn.close()


def get_shipment_count(user_id):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM shipments WHERE user_id = %s", (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


def get_shipment_by_number(shipment_number):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM shipments WHERE shipment_number = %s", (shipment_number,)
    ).fetchone()
    conn.close()
    return row


def get_expenses_by_shipment(shipment_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM expenses WHERE shipment_id = %s ORDER BY date ASC", (shipment_id,)
    ).fetchall()
    conn.close()
    return rows


# ------------------------------------------------------------------ #
# Shipment-Vendor CRUD                                                #
# ------------------------------------------------------------------ #

RELATIONSHIP_TYPES = ('CUSTOMER', 'TRANSPORTER', 'CONSIGNEE', 'CLEARING_AGENT')
BILLING_TYPES      = ('PAYABLE', 'RECEIVABLE')
PAYMENT_STATUSES   = ('PENDING', 'PARTIAL', 'PAID', 'OVERDUE')
CURRENCIES         = ('INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD', 'JPY', 'CNY')

ENQUIRY_STATUSES   = ('OPEN', 'IN_PROGRESS', 'QUOTED', 'CONVERTED', 'CLOSED')
ENQUIRY_PRIORITIES = ('LOW', 'NORMAL', 'HIGH', 'URGENT')
WEIGHT_UNITS       = ('KGS', 'LBS', 'MT')
CONSIGNMENT_TYPES  = ('AIR CARGO', 'FCL', 'LCL', 'BREAK BULK', 'RORO', 'COURIER')


def create_shipment_vendor(vendor_id, shipment_id, relationship_type, billing_type,
                            amount=0, currency='INR', invoice_number=None,
                            invoice_date=None, due_date=None,
                            payment_status='PENDING', notes=None,
                            particular_id=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO shipment_vendors"
        " (vendor_id, shipment_id, relationship_type, billing_type, amount, currency,"
        "  invoice_number, invoice_date, due_date, payment_status, notes, particular_id)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (vendor_id, shipment_id, relationship_type, billing_type,
         amount, currency, invoice_number, invoice_date, due_date,
         payment_status, notes, particular_id),
    )
    conn.commit()
    conn.close()


def get_shipment_vendor_by_id(sv_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM shipment_vendors WHERE id = %s", (sv_id,)
    ).fetchone()
    conn.close()
    return row


def get_vendors_by_shipment(shipment_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT sv.*, v.vendor_name, v.vendor_code, v.vendor_category"
        " FROM shipment_vendors sv"
        " JOIN vendors v ON sv.vendor_id = v.id"
        " WHERE sv.shipment_id = %s"
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
        " WHERE sv.vendor_id = %s"
        " ORDER BY s.created_at DESC",
        (vendor_id,),
    ).fetchall()
    conn.close()
    return rows


def update_shipment_vendor(sv_id, relationship_type, billing_type,
                            amount=0, currency='INR', invoice_number=None,
                            invoice_date=None, due_date=None,
                            payment_status='PENDING', notes=None,
                            particular_id=None):
    conn = get_db()
    conn.execute(
        "UPDATE shipment_vendors"
        " SET relationship_type=%s, billing_type=%s, amount=%s, currency=%s,"
        "     invoice_number=%s, invoice_date=%s, due_date=%s, payment_status=%s,"
        "     notes=%s, particular_id=%s"
        " WHERE id=%s",
        (relationship_type, billing_type, amount, currency,
         invoice_number, invoice_date, due_date, payment_status, notes, particular_id, sv_id),
    )
    conn.commit()
    conn.close()


def delete_shipment_vendor(sv_id):
    conn = get_db()
    conn.execute("DELETE FROM shipment_vendors WHERE id = %s", (sv_id,))
    conn.commit()
    conn.close()


def get_shipment_vendor_count(shipment_id):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM shipment_vendors WHERE shipment_id = %s", (shipment_id,)
    ).fetchone()[0]
    conn.close()
    return count


def get_total_payables_by_shipment(shipment_id):
    conn = get_db()
    total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM shipment_vendors"
        " WHERE shipment_id = %s AND billing_type = 'PAYABLE'",
        (shipment_id,),
    ).fetchone()[0]
    conn.close()
    return float(total)


def get_total_receivables_by_shipment(shipment_id):
    conn = get_db()
    total = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM shipment_particulars WHERE shipment_id = %s",
        (shipment_id,),
    ).fetchone()[0]
    conn.close()
    return float(total)


# ── shipment_vendor_payments ──────────────────────────────────────────────────

def _refresh_sv_payment_status(sv_id):
    conn = get_db()
    sv_row = conn.execute(
        "SELECT amount FROM shipment_vendors WHERE id = %s", (sv_id,)
    ).fetchone()
    if sv_row is None:
        conn.close()
        return
    total = float(sv_row["amount"] or 0)
    paid = float(conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM shipment_vendor_payments"
        " WHERE shipment_vendor_id = %s", (sv_id,)
    ).fetchone()[0])
    if paid <= 0:
        status = "PENDING"
    elif paid >= total:
        status = "PAID"
    else:
        status = "PARTIAL"
    conn.execute(
        "UPDATE shipment_vendors SET payment_status = %s WHERE id = %s", (status, sv_id)
    )
    conn.commit()
    conn.close()


def create_sv_payment(sv_id, amount, payment_date, reference=None, notes=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO shipment_vendor_payments"
        " (shipment_vendor_id, amount, payment_date, reference, notes)"
        " VALUES (%s, %s, %s, %s, %s)",
        (sv_id, amount, payment_date, reference or None, notes or None),
    )
    conn.commit()
    conn.close()
    _refresh_sv_payment_status(sv_id)


def get_payments_by_sv(sv_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM shipment_vendor_payments"
        " WHERE shipment_vendor_id = %s ORDER BY payment_date ASC, id ASC",
        (sv_id,),
    ).fetchall()
    conn.close()
    return rows


def get_sv_payment_by_id(payment_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM shipment_vendor_payments WHERE id = %s", (payment_id,)
    ).fetchone()
    conn.close()
    return row


def delete_sv_payment(payment_id):
    conn = get_db()
    row = conn.execute(
        "SELECT shipment_vendor_id FROM shipment_vendor_payments WHERE id = %s",
        (payment_id,),
    ).fetchone()
    sv_id = row["shipment_vendor_id"] if row else None
    conn.execute("DELETE FROM shipment_vendor_payments WHERE id = %s", (payment_id,))
    conn.commit()
    conn.close()
    if sv_id:
        _refresh_sv_payment_status(sv_id)


def get_payments_by_shipment(shipment_id):
    """Return {sv_id: [payment_dicts]} for all payments in a shipment (one query)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT p.* FROM shipment_vendor_payments p"
        " JOIN shipment_vendors sv ON p.shipment_vendor_id = sv.id"
        " WHERE sv.shipment_id = %s"
        " ORDER BY p.payment_date ASC, p.id ASC",
        (shipment_id,),
    ).fetchall()
    conn.close()
    result = {}
    for r in rows:
        result.setdefault(r["shipment_vendor_id"], []).append(dict(r))
    return result


def log_alert(user_id, entity_type, entity_id, entity_label, action, description=None):
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO system_alerts"
            " (user_id, entity_type, entity_id, entity_label, action, description)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (user_id, entity_type, entity_id, entity_label, action, description),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_company_profile(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM company_profiles WHERE user_id = %s", (user_id,)
    ).fetchone()
    conn.close()
    return row


def get_all_contact_emails_by_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT vc.email, vc.name, v.vendor_name"
        " FROM vendor_contacts vc"
        " JOIN vendors v ON vc.vendor_id = v.id"
        " WHERE v.user_id = %s AND vc.email IS NOT NULL AND vc.email != ''"
        " ORDER BY vc.name ASC",
        (user_id,),
    ).fetchall()
    conn.close()
    return rows


# ------------------------------------------------------------------ #
# Gmail account CRUD                                                  #
# ------------------------------------------------------------------ #

def upsert_gmail_account(user_id, gmail_email, google_account_id,
                          access_token_enc, refresh_token_enc,
                          token_expiry=None, scope=None):
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM gmail_accounts WHERE user_id = %s", (user_id,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE gmail_accounts SET gmail_email=%s, google_account_id=%s,"
            " access_token=%s, refresh_token=%s, token_expiry=%s, scope=%s,"
            " is_connected=1, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s",
            (gmail_email, google_account_id, access_token_enc, refresh_token_enc,
             token_expiry, scope, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO gmail_accounts"
            " (user_id, gmail_email, google_account_id, access_token, refresh_token,"
            "  token_expiry, scope, is_connected)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, 1)",
            (user_id, gmail_email, google_account_id, access_token_enc,
             refresh_token_enc, token_expiry, scope),
        )
    conn.commit()
    conn.close()


def get_gmail_account(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM gmail_accounts WHERE user_id = %s AND is_connected = 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return row


def delete_gmail_account(user_id):
    conn = get_db()
    conn.execute("DELETE FROM gmail_accounts WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# Email CRUD                                                          #
# ------------------------------------------------------------------ #

def save_email(user_id, gmail_message_id, gmail_thread_id=None,
               direction="INBOUND", from_email=None, from_name=None,
               to_email=None, to_name=None, cc=None, bcc=None,
               subject=None, body_plain=None, body_html=None,
               snippet=None, status="RECEIVED", label_names=None,
               has_attachments=0, received_at=None, sent_at=None):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO emails"
        " (user_id, gmail_message_id, gmail_thread_id, direction,"
        "  from_email, from_name, to_email, to_name, cc, bcc,"
        "  subject, body_plain, body_html, snippet, status,"
        "  label_names, has_attachments, received_at, sent_at)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        " ON CONFLICT (gmail_message_id) DO NOTHING"
        " RETURNING id",
        (user_id, gmail_message_id, gmail_thread_id, direction,
         from_email, from_name, to_email, to_name, cc, bcc,
         subject, body_plain, body_html, snippet, status,
         label_names, has_attachments, received_at, sent_at),
    )
    conn.commit()
    row = cursor.fetchone()
    email_id = row["id"] if row else None
    conn.close()
    return email_id


def get_emails_by_user(user_id, limit=50, direction=None):
    conn = get_db()
    if direction:
        rows = conn.execute(
            "SELECT * FROM emails WHERE user_id = %s AND direction = %s"
            " ORDER BY COALESCE(received_at, sent_at, synced_at::text) DESC LIMIT %s",
            (user_id, direction, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM emails WHERE user_id = %s"
            " ORDER BY COALESCE(received_at, sent_at, synced_at::text) DESC LIMIT %s",
            (user_id, limit),
        ).fetchall()
    conn.close()
    return rows


def get_email_by_id(email_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM emails WHERE id = %s", (email_id,)).fetchone()
    conn.close()
    return row


def get_email_by_gmail_id(gmail_message_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM emails WHERE gmail_message_id = %s", (gmail_message_id,)
    ).fetchone()
    conn.close()
    return row


def get_emails_by_thread(gmail_thread_id, user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM emails WHERE gmail_thread_id = %s AND user_id = %s"
        " ORDER BY COALESCE(received_at, sent_at, synced_at::text) ASC",
        (gmail_thread_id, user_id),
    ).fetchall()
    conn.close()
    return rows


def delete_email(email_id):
    conn = get_db()
    conn.execute("DELETE FROM emails WHERE id = %s", (email_id,))
    conn.commit()
    conn.close()


def save_email_attachment(email_id, filename=None, mime_type=None,
                           gmail_attachment_id=None, file_path=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO email_attachments"
        " (email_id, filename, mime_type, gmail_attachment_id, file_path)"
        " VALUES (%s, %s, %s, %s, %s)",
        (email_id, filename, mime_type, gmail_attachment_id, file_path),
    )
    conn.commit()
    conn.close()


def upsert_ai_processing(email_id, ai_summary=None, detected_category=None,
                          extracted_entities=None, shipment_reference=None,
                          invoice_reference=None, processing_status="DONE"):
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM email_ai_processing WHERE email_id = %s", (email_id,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE email_ai_processing SET ai_summary=%s, detected_category=%s,"
            " extracted_entities=%s, shipment_reference=%s, invoice_reference=%s,"
            " processing_status=%s WHERE email_id=%s",
            (ai_summary, detected_category, extracted_entities,
             shipment_reference, invoice_reference, processing_status, email_id),
        )
    else:
        conn.execute(
            "INSERT INTO email_ai_processing"
            " (email_id, ai_summary, detected_category, extracted_entities,"
            "  shipment_reference, invoice_reference, processing_status)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (email_id, ai_summary, detected_category, extracted_entities,
             shipment_reference, invoice_reference, processing_status),
        )
    conn.commit()
    conn.close()


def get_ai_processing(email_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM email_ai_processing WHERE email_id = %s", (email_id,)
    ).fetchone()
    conn.close()
    return row


def upsert_company_profile(user_id, company_name, legal_name=None, industry=None,
                           website=None, email=None, phone=None, address_line1=None,
                           address_line2=None, city=None, state=None, country=None,
                           pincode=None, gst_number=None, pan_number=None, iec_code=None,
                           currency="INR", incoterms=None, logo_path=None,
                           billing_terms=None):
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM company_profiles WHERE user_id = %s", (user_id,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE company_profiles SET company_name=%s, legal_name=%s, industry=%s,"
            " website=%s, email=%s, phone=%s, address_line1=%s, address_line2=%s, city=%s,"
            " state=%s, country=%s, pincode=%s, gst_number=%s, pan_number=%s, iec_code=%s,"
            " currency=%s, incoterms=%s, logo_path=%s, billing_terms=%s,"
            " updated_at=CURRENT_TIMESTAMP WHERE user_id=%s",
            (company_name, legal_name, industry, website, email, phone,
             address_line1, address_line2, city, state, country, pincode,
             gst_number, pan_number, iec_code, currency, incoterms,
             logo_path, billing_terms, user_id),
        )
    else:
        conn.execute(
            "INSERT INTO company_profiles (user_id, company_name, legal_name, industry,"
            " website, email, phone, address_line1, address_line2, city, state, country,"
            " pincode, gst_number, pan_number, iec_code, currency, incoterms,"
            " logo_path, billing_terms)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (user_id, company_name, legal_name, industry, website, email, phone,
             address_line1, address_line2, city, state, country, pincode,
             gst_number, pan_number, iec_code, currency, incoterms,
             logo_path, billing_terms),
        )
    conn.commit()
    conn.close()


def update_user_profile(user_id, name, email):
    conn = get_db()
    conn.execute(
        "UPDATE users SET name=%s, email=%s WHERE id=%s",
        (name, email, user_id),
    )
    conn.commit()
    conn.close()


def update_user_password(user_id, password_hash):
    conn = get_db()
    conn.execute(
        "UPDATE users SET password_hash=%s WHERE id=%s",
        (password_hash, user_id),
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# Enquiry CRUD                                                        #
# ------------------------------------------------------------------ #

def generate_customer_vendor_code():
    year = datetime.datetime.now().year
    conn = get_db()
    row = conn.execute(
        "SELECT vendor_code FROM vendors WHERE vendor_code LIKE %s"
        " ORDER BY vendor_code DESC LIMIT 1",
        (f"CUST-{year}-%",)
    ).fetchone()
    conn.close()
    if row is None:
        return f"CUST-{year}-001"
    try:
        return f"CUST-{year}-{int(row['vendor_code'].split('-')[2]) + 1:03d}"
    except (IndexError, ValueError):
        return f"CUST-{year}-001"


def _next_enquiry_number(user_id):
    year = datetime.datetime.now().year
    conn = get_db()
    row = conn.execute(
        "SELECT enquiry_number FROM enquiries WHERE user_id = %s"
        " AND enquiry_number LIKE %s ORDER BY enquiry_number DESC LIMIT 1",
        (user_id, f"ENQ-{year}-%")
    ).fetchone()
    conn.close()
    if row is None:
        return f"ENQ-{year}-001"
    try:
        return f"ENQ-{year}-{int(row['enquiry_number'].split('-')[2]) + 1:03d}"
    except (IndexError, ValueError):
        return f"ENQ-{year}-001"


def create_enquiry(user_id, data):
    enquiry_number = _next_enquiry_number(user_id)
    customer_vendor_id = None
    if data.get("customer_name"):
        vendor_code = generate_customer_vendor_code()
        create_vendor(
            user_id=user_id, vendor_code=vendor_code,
            vendor_name=data["customer_name"], vendor_type="INBOUND",
            vendor_category="CUSTOMER", email=data.get("customer_email"),
            phone=data.get("customer_phone"), status="INACTIVE",
            currency="INR", created_by=user_id,
        )
        v = get_vendor_by_code(vendor_code)
        customer_vendor_id = v["id"] if v else None
    conn = get_db()
    row = conn.execute(
        "INSERT INTO enquiries (user_id, enquiry_number, customer_name, customer_email,"
        " customer_phone, customer_vendor_id, commodity, consignment_type, shipment_terms,"
        " weight, weight_unit, packages, mawb, hawb, origin, destination, ex_rate,"
        " incoterms, currency, estimated_value, status, priority, enquiry_date,"
        " follow_up_date, notes)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        " RETURNING *",
        (user_id, enquiry_number, data.get("customer_name"), data.get("customer_email"),
         data.get("customer_phone"), customer_vendor_id, data.get("commodity"),
         data.get("consignment_type"), data.get("shipment_terms"),
         float(data.get("weight") or 0), data.get("weight_unit", "KGS"),
         int(data.get("packages") or 0), data.get("mawb"), data.get("hawb"),
         data.get("origin"), data.get("destination"), float(data.get("ex_rate") or 0),
         data.get("incoterms"), data.get("currency", "INR"),
         float(data.get("estimated_value") or 0),
         data.get("status", "OPEN"), data.get("priority", "NORMAL"),
         data.get("enquiry_date"), data.get("follow_up_date"), data.get("notes"))
    ).fetchone()
    conn.commit()
    conn.close()
    return row


def get_enquiries_by_user(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM enquiries WHERE user_id = %s ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_enquiry_count(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM enquiries WHERE user_id = %s", (user_id,)
    ).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def get_enquiry_by_id(enquiry_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM enquiries WHERE id = %s", (enquiry_id,)
    ).fetchone()
    conn.close()
    return row


def update_enquiry(enquiry_id, data):
    conn = get_db()
    conn.execute(
        "UPDATE enquiries SET customer_name=%s, customer_email=%s, customer_phone=%s,"
        " commodity=%s, consignment_type=%s, shipment_terms=%s, weight=%s, weight_unit=%s,"
        " packages=%s, mawb=%s, hawb=%s, origin=%s, destination=%s, ex_rate=%s,"
        " incoterms=%s, currency=%s, estimated_value=%s, status=%s, priority=%s,"
        " enquiry_date=%s, follow_up_date=%s, notes=%s, updated_at=NOW()"
        " WHERE id=%s",
        (data.get("customer_name"), data.get("customer_email"), data.get("customer_phone"),
         data.get("commodity"), data.get("consignment_type"), data.get("shipment_terms"),
         float(data.get("weight") or 0), data.get("weight_unit", "KGS"),
         int(data.get("packages") or 0), data.get("mawb") or None, data.get("hawb") or None,
         data.get("origin"), data.get("destination"), float(data.get("ex_rate") or 0),
         data.get("incoterms") or None, data.get("currency", "INR"),
         float(data.get("estimated_value") or 0),
         data.get("status", "OPEN"), data.get("priority", "NORMAL"),
         data.get("enquiry_date"), data.get("follow_up_date") or None, data.get("notes") or None,
         enquiry_id)
    )
    conn.commit()
    conn.close()


def update_enquiry_status(enquiry_id, status):
    conn = get_db()
    conn.execute(
        "UPDATE enquiries SET status = %s, updated_at = NOW() WHERE id = %s",
        (status, enquiry_id),
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# Particulars Types                                                   #
# ------------------------------------------------------------------ #

def get_particular_types(user_id):
    """Return system defaults + this user's custom types, ordered."""
    conn = get_db()
    rows = conn.execute(
        "SELECT label FROM particulars_types"
        " WHERE user_id IS NULL OR user_id = %s"
        " ORDER BY is_custom ASC, label ASC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [r["label"] for r in rows]


def ensure_particular_type(user_id, label):
    """Persist a custom label if it doesn't already exist."""
    label = label.strip()
    if not label:
        return
    conn = get_db()
    conn.execute(
        "INSERT INTO particulars_types (user_id, label, is_custom)"
        " VALUES (%s, %s, TRUE) ON CONFLICT (label) DO NOTHING",
        (user_id, label)
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# Enquiry Particulars CRUD                                            #
# ------------------------------------------------------------------ #

def get_particulars_by_enquiry(enquiry_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM enquiry_particulars WHERE enquiry_id = %s ORDER BY created_at ASC",
        (enquiry_id,)
    ).fetchall()
    conn.close()
    return rows


def create_enquiry_particular(enquiry_id, user_id, data):
    conn = get_db()
    row = conn.execute(
        "INSERT INTO enquiry_particulars"
        " (enquiry_id, user_id, particular_type, sac_hsn, qty,"
        "  ex_rate, weight, weight_unit, offered_rate, use_formula,"
        "  expense, tax_rate, cgst, sgst, igst, total, currency)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        " RETURNING *",
        (enquiry_id, user_id,
         data["particular_type"], data.get("sac_hsn") or None,
         int(data.get("qty") or 1),
         float(data.get("ex_rate") or 0), float(data.get("weight") or 0),
         data.get("weight_unit", "KGS"),
         float(data.get("offered_rate") or 0),
         bool(data.get("use_formula")),
         float(data.get("expense") or 0),
         float(data.get("tax_rate") or 0),
         float(data.get("cgst") or 0), float(data.get("sgst") or 0),
         float(data.get("igst") or 0),
         float(data.get("total") or 0),
         data.get("currency", "INR"))
    ).fetchone()
    conn.commit()
    conn.close()
    return row


def delete_enquiry_particular(particular_id):
    conn = get_db()
    conn.execute("DELETE FROM enquiry_particulars WHERE id = %s", (particular_id,))
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# Shipment Particulars CRUD                                           #
# ------------------------------------------------------------------ #

def get_particulars_by_shipment(shipment_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM shipment_particulars WHERE shipment_id = %s ORDER BY created_at ASC",
        (shipment_id,)
    ).fetchall()
    conn.close()
    return rows


def get_shipment_particular_by_id(particular_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM shipment_particulars WHERE id = %s", (particular_id,)
    ).fetchone()
    conn.close()
    return row


def create_shipment_particular(shipment_id, user_id, data, enquiry_particular_id=None):
    conn = get_db()
    row = conn.execute(
        "INSERT INTO shipment_particulars"
        " (shipment_id, user_id, particular_type, sac_hsn, qty,"
        "  ex_rate, weight, weight_unit, offered_rate, use_formula,"
        "  expense, tax_rate, cgst, sgst, igst, total, currency, enquiry_particular_id)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        " RETURNING *",
        (shipment_id, user_id,
         data["particular_type"], data.get("sac_hsn") or None,
         int(data.get("qty") or 1),
         float(data.get("ex_rate") or 0), float(data.get("weight") or 0),
         data.get("weight_unit", "KGS"),
         float(data.get("offered_rate") or 0),
         bool(data.get("use_formula")),
         float(data.get("expense") or 0),
         float(data.get("tax_rate") or 0),
         float(data.get("cgst") or 0), float(data.get("sgst") or 0),
         float(data.get("igst") or 0),
         float(data.get("total") or 0),
         data.get("currency", "INR"),
         enquiry_particular_id)
    ).fetchone()
    conn.commit()
    conn.close()
    return row


def update_shipment_particular(particular_id, data):
    conn = get_db()
    conn.execute(
        "UPDATE shipment_particulars"
        " SET particular_type=%s, sac_hsn=%s, qty=%s, ex_rate=%s, weight=%s,"
        "     weight_unit=%s, offered_rate=%s, use_formula=%s, expense=%s,"
        "     tax_rate=%s, cgst=%s, sgst=%s, igst=%s, total=%s, currency=%s"
        " WHERE id=%s",
        (data["particular_type"], data.get("sac_hsn") or None,
         int(data.get("qty") or 1),
         float(data.get("ex_rate") or 0), float(data.get("weight") or 0),
         data.get("weight_unit", "KGS"),
         float(data.get("offered_rate") or 0),
         bool(data.get("use_formula")),
         float(data.get("expense") or 0),
         float(data.get("tax_rate") or 0),
         float(data.get("cgst") or 0), float(data.get("sgst") or 0),
         float(data.get("igst") or 0),
         float(data.get("total") or 0),
         data.get("currency", "INR"),
         particular_id)
    )
    conn.commit()
    conn.close()


def delete_shipment_particular(particular_id):
    conn = get_db()
    conn.execute("DELETE FROM shipment_particulars WHERE id = %s", (particular_id,))
    conn.commit()
    conn.close()


def get_sv_by_particular(particular_id):
    """Return the PAYABLE shipment_vendor entry linked to a particular, or None."""
    conn = get_db()
    row = conn.execute(
        "SELECT sv.*, v.vendor_name, v.vendor_code, v.vendor_category"
        " FROM shipment_vendors sv"
        " JOIN vendors v ON sv.vendor_id = v.id"
        " WHERE sv.particular_id = %s",
        (particular_id,)
    ).fetchone()
    conn.close()
    return row
