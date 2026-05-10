# Spec: Vendor Management Database Setup

## Overview

Adds a `vendors` table and its CRUD helper functions to the logitrack data layer.
Vendors are companies or individuals that a user works with for logistics operations —
freight forwarders, customs agents, port handlers, etc. This step establishes the
database foundation required by all subsequent vendor-facing routes and UI. No routes
or templates are introduced here; this is purely a data-layer step.

## Depends on

- Step 01 — Database Setup (users table, `get_db()`, `init_db()`)

## Routes

No new routes.

## Database changes

Add one new table to `init_db()` in `database/db.py`:

```sql
CREATE TABLE IF NOT EXISTS vendors (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id               INTEGER NOT NULL REFERENCES users(id),
    vendor_code           TEXT    NOT NULL UNIQUE,
    vendor_name           TEXT    NOT NULL,
    vendor_type           TEXT    NOT NULL,
    vendor_category       TEXT    NOT NULL,
    company_name          TEXT,
    owner_name            TEXT,
    email                 TEXT,
    phone                 TEXT,
    alternate_phone       TEXT,
    website               TEXT,
    gst_number            TEXT,
    pan_number            TEXT,
    iec_code              TEXT,
    address_line1         TEXT,
    address_line2         TEXT,
    city                  TEXT,
    state                 TEXT,
    country               TEXT,
    pincode               TEXT,
    payment_terms_days    INTEGER DEFAULT 0,
    credit_limit          REAL    DEFAULT 0,
    bank_name             TEXT,
    account_number        TEXT,
    ifsc_code             TEXT,
    upi_id                TEXT,
    currency              TEXT    DEFAULT 'INR',
    status                TEXT    NOT NULL DEFAULT 'ACTIVE',
    notes                 TEXT,
    created_at            TEXT    DEFAULT (datetime('now')),
    updated_at            TEXT,
    created_by            INTEGER,
    updated_by            INTEGER
);
```

**Vendor types (fixed list):**

```
INBOUND
OUTBOUND
```

** status (fixed list):**

```
ACTIVE
INACTIVE
BLOCKED
```

**Vendor categories (fixed list):**

```
CUSTOMER
TRANSPORTER
SHIPPER
CONSIGNEE
WAREHOUSE
CUSTOM_CLEARANCE_AGENT
FREIGHT_FORWARDER
PACKAGING_VENDOR
INSURANCE_PROVIDER
SHIPPING_LINE
AIR_CARRIER
LOCAL_TRANSPORT
PORT_AGENT
COURIER_PARTNER
BILLING_PARTNER
OTHER
```

## Templates

- **Create:** none
- **Modify:** none

## Files to change

- `database/db.py` — add `vendors` table to `init_db()`, add CRUD helpers, extend `seed_db()`

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never f-strings or `%` formatting in SQL
- `PRAGMA foreign_keys = ON` is already enforced by `get_db()` — do not duplicate it
- Use CSS variables — never hardcode hex values (not applicable here, data layer only)
- All templates extend `base.html` (not applicable here, data layer only)
- `init_db()` uses `CREATE TABLE IF NOT EXISTS` — safe to call multiple times
- `seed_db()` must guard against duplicate inserts (check count before inserting)
- Seed vendors must all reference the demo user (`demo@logitrack.com`)
- currency defaults to INR
- payment_terms_days defaults to 0
- credit_limit defaults to 0

## CRUD helpers to add in `database/db.py`

Add these six functions **after** the existing expense helpers:

### `create_vendor(user_id, name, contact_name, email, phone, address, category, notes)`

Inserts one row into `vendors`. `contact_name`, `email`, `phone`, `address`, and `notes` are optional (may be `None`). Returns nothing.

### `get_vendor_by_id(vendor_id)`

Returns the matching `vendors` row as `sqlite3.Row`, or `None` if not found.

### `get_vendors_by_user(user_id)`

Returns all `vendors` rows for the given user, ordered by `name ASC`.

### `update_vendor(vendor_id, name, contact_name, email, phone, address, category, notes)`

Updates all editable fields on the given vendor. Optional fields may be `None`.

### `delete_vendor(vendor_id)`

Deletes the vendor row with the given `vendor_id`.

### `get_vendor_count(user_id)`

Returns the integer count of vendors belonging to `user_id`. Used for stats display.

## Seed data

Extend `seed_db()` to insert **5 sample vendors** for the demo user, but only if the `vendors` table is empty. Guard with:

```python
if conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0] > 0:
    # skip vendor seeding
```

## Definition of done

- [ ] App starts without errors after the change (`python app.py`)
- [ ] `vendors` table exists in `logitrack.db` with the correct schema (verify via SQLite browser or `sqlite3` CLI)
- [ ] Foreign key constraint on `vendors.user_id` is enforced — inserting a vendor with a non-existent `user_id` raises an `IntegrityError`
- [ ] `init_db()` is idempotent — calling it twice does not error or duplicate the table
- [ ] `seed_db()` inserts exactly 5 vendors for the demo user on first run
- [ ] `seed_db()` does not insert duplicate vendors on repeated runs
- [ ] `create_vendor()` inserts a row and is retrievable via `get_vendor_by_id()`
- [ ] `get_vendors_by_user()` returns vendors sorted by `vendore name ASC`
- [ ] `update_vendor()` persists changes correctly
- [ ] `vendor_code uniqueness validation
- [ ] `updated_at update validation
- [ ] `get_vendor_by_code validation
- [ ] `delete_vendor()` removes the row; subsequent `get_vendor_by_id()` returns `None`
- [ ] `get_vendor_count()` returns the correct integer count
- [ ] All queries use `?` placeholders — no string interpolation in SQL
