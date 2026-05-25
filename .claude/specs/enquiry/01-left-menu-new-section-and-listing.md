# Spec: Left Menu New Section and Listing

## Overview

This step introduces the **Enquiries** module to logitrack — a new first-class section in the sidebar for managing inbound logistics enquiries (pre-shipment requests from customers or prospects). It covers two deliverables: (1) adding an "Enquiries" accordion group to the sidebar, and (2) creating an enquiries listing page at `/enquiries` that shows all enquiries owned by the logged-in user with status badges, key metadata, and a "New Enquiry" action button. This lays the foundation for subsequent steps (add/edit/detail for enquiries, potential conversion to shipments).

## Depends on

- All auth steps (register / login / session) must be complete
- Sidebar and profile shell layout must be in place (`_sidebar.html`, `profile.css`)
- Vendors module must be complete (`vendors` table and `create_vendor` must exist in `database/db.py`)

## Routes

- `GET /enquiries` — list all enquiries for the logged-in user — logged-in

## Database changes

New table:

```sql
enquiries (
    id                 SERIAL PRIMARY KEY,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    enquiry_number     TEXT    NOT NULL,

    -- Customer info (new customer is auto-mirrored into vendors table)
    customer_name      TEXT,
    customer_email     TEXT,
    customer_phone     TEXT,
    customer_vendor_id INTEGER REFERENCES vendors(id),

    -- Cargo section (replaces single cargo_description field)
    commodity          TEXT,
    consignment_type   TEXT,
    shipment_terms     TEXT,
    weight             REAL    DEFAULT 0,
    weight_unit        TEXT    DEFAULT 'KGS',
    packages           INTEGER DEFAULT 0,
    mawb               TEXT,
    hawb               TEXT,
    origin             TEXT,
    destination        TEXT,
    ex_rate            REAL    DEFAULT 0,

    -- Metadata
    incoterms          TEXT,
    currency           TEXT    NOT NULL DEFAULT 'INR',
    estimated_value    REAL    DEFAULT 0,
    status             TEXT    NOT NULL DEFAULT 'OPEN',
    priority           TEXT    NOT NULL DEFAULT 'NORMAL',
    enquiry_date       TEXT    NOT NULL,
    follow_up_date     TEXT,
    notes              TEXT,
    created_at         TEXT    DEFAULT (NOW()::TEXT),
    updated_at         TEXT
)
```

Status values: `OPEN`, `IN_PROGRESS`, `QUOTED`, `CONVERTED`, `CLOSED`
Priority values: `LOW`, `NORMAL`, `HIGH`, `URGENT`
Weight unit values: `KGS`, `LBS`, `MT`

### Customer → vendor auto-creation

When `create_enquiry` is called and `customer_name` is non-empty, the helper must also call
the existing `create_vendor(...)` in `database/db.py` and store the resulting vendor id:

- `vendor_type = 'INBOUND'`
- `vendor_category = 'CUSTOMER'`
- `status = 'INACTIVE'` — activated manually when the enquiry converts to a shipment
- `vendor_name = customer_name`
- `vendor_code = generate_customer_vendor_code(user_id)` → `CUST-<year>-<NNN>` e.g. `CUST-2026-001`
- Store returned `vendor.id` in `enquiries.customer_vendor_id`
- If `customer_name` is blank, skip vendor creation; `customer_vendor_id` stays `NULL`

### Ex.rate (exchange rate)

`ex_rate` stores the USD → INR TT Selling rate at the time the enquiry is created.
Auto-fetch from the HDFC Bank treasury forex card rates PDF is **implemented in step 02**
(add-enquiry form). In step 02 a "Fetch Rate" button will call `GET /enquiries/forex-rate`,
which downloads the PDF and reads the "United States Dollar / T.T. Selling (O/w Rem)" cell
using `pdfplumber`. The user may also type the rate manually. In this step (01) the column
is defined in the schema only.

### New `database/db.py` functions

- `create_enquiry(user_id, data)` — INSERT enquiry row; if `customer_name` is provided,
  auto-calls `create_vendor` (INBOUND/CUSTOMER/INACTIVE) and stores the id in
  `customer_vendor_id`; returns the new enquiry row
- `get_enquiries_by_user(user_id)` — SELECT all enquiries for user, ordered by `created_at DESC`
- `get_enquiry_count(user_id)` — COUNT of enquiries for user
- `generate_customer_vendor_code(user_id)` — queries the highest existing `CUST-<year>-NNN`
  vendor code for the current year and returns the next one (e.g. `CUST-2026-003`)

## Templates

- **Create:** `templates/enquiries.html` — enquiry listing page
- **Modify:** `templates/_sidebar.html` — add new Enquiries accordion group

## Files to change

- `templates/_sidebar.html` — add Enquiries group between Shipments and Vendors
- `database/db.py` — add `enquiries` table to `init_db()`, add the four new functions above
- `app.py` — add `GET /enquiries` route

## Files to create

- `templates/enquiries.html` — enquiry listing page
- `static/css/enquiries.css` — page-specific styles

## New dependencies

`pdfplumber` — required for ex_rate auto-fetch. Added to `requirements.txt` in **step 02**
(add-enquiry form). Not needed for this listing step.

## Rules for implementation

- No SQLAlchemy or ORMs — raw psycopg2 with `%s` placeholders only
- Parameterised queries only — never f-strings in SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Always pass `active_section="enquiries"` to `render_template()` on the listing route
- `init_db()` must remain idempotent — use `CREATE TABLE IF NOT EXISTS`
- The Enquiries accordion group in `_sidebar.html` must follow the exact same HTML structure
  as existing groups (button + sidebar-sub-nav pattern)
- Insert the Enquiries group **between Shipments and Vendors** in `_sidebar.html`
- The listing table must follow the same `.txn-table` pattern used in `shipments.html`
- Status badges must use `.status-badge` CSS class with modifier classes:
  `status-badge--open`, `status-badge--in-progress`, `status-badge--quoted`,
  `status-badge--converted`, `status-badge--closed`
- `enquiry_number` must be auto-generated in `create_enquiry` as `ENQ-<year>-<NNN>`
  (e.g. `ENQ-2026-001`) using the same MAX+1 pattern as `generate_customer_vendor_code`

## Definition of done

- [ ] Navigating to `/enquiries` while logged in renders the enquiries listing page without errors
- [ ] The sidebar shows an "Enquiries" accordion group that expands to reveal sub-links including "All Enquiries"
- [ ] The "Enquiries" sidebar group is pre-expanded (`is-open`) when `active_section == "enquiries"`
- [ ] The active sub-link highlight (`.sidebar-sub-link--active`) appears on "All Enquiries" when on `/enquiries`
- [ ] The listing page shows a "New Enquiry" button (links to `#` as placeholder — full add form is a future step)
- [ ] The listing table renders columns: Enquiry #, Customer, Route (origin → destination), Commodity, Consignment Type, Status, Priority, Ex.rate, Date, Estimated Value
- [ ] Status column renders colour-coded badges for each of the five status values
- [ ] An empty state message is shown when no enquiries exist for the user
- [ ] Navigating to `/enquiries` while logged out redirects to `/login`
- [ ] `init_db()` creates the `enquiries` table without errors on a fresh database
- [ ] `get_enquiries_by_user(user_id)` returns rows ordered by `created_at DESC`
- [ ] `generate_customer_vendor_code` returns `CUST-<current-year>-001` when no customer vendors exist yet
