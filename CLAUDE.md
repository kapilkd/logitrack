# CLAUDE.md

## Project overview

logitrack is a lightweight logistic tracker and builder application built with Flask and SQLite.

---

## Architecture

```
logitrack/
├── app.py                  # All routes — single file, no blueprints
├── database/
│   ├── db.py               # SQLite helpers + CRUD (see full list below)
│   └── queries.py          # Complex read queries: joins, aggregates, filters
├── templates/
│   ├── base.html           # Shared layout — all templates must extend this
│   ├── _sidebar.html       # Sidebar partial — included by all sidebar pages
│   ├── landing.html
│   ├── login.html
│   ├── register.html
│   ├── placeholder.html    # Shared "coming soon" page, accepts title + active_section
│   ├── profile.html        # Dashboard: stats, date filter, transactions, categories
│   ├── add_expense.html    # Standalone add-expense form
│   ├── edit_expense.html
│   ├── shipments.html      # Shipments list with active/closed toggle
│   ├── add_shipment.html
│   ├── edit_shipment.html
│   ├── shipment_detail.html # Shipment detail: expenses, vendors, billing
│   ├── vendors.html        # Vendor list with filters + contacts panel
│   ├── billing.html        # Shipment-wise vendor billing dashboard
│   ├── notifications.html  # Recent system alerts
│   ├── terms.html
│   └── privacy.html
├── static/
│   ├── css/
│   │   ├── style.css       # Global styles: navbar, buttons, auth pages, footer
│   │   ├── landing.css     # Landing page only
│   │   ├── profile.css     # Sidebar + profile page + accordion sub-menu styles
│   │   ├── shipments.css   # Shipments list + detail shared styles
│   │   ├── vendors.css     # Vendor list, contacts panel
│   │   ├── billing.css     # Billing dashboard
│   │   └── notifications.css
│   └── js/
│       ├── main.js         # Global JS: sidebar accordion toggle (loads on all pages)
│       ├── profile.js      # Profile page: expense modal open/close, edit/delete handlers
│       ├── shipments.js    # Shipments list: status dropdown inline update
│       ├── shipment_detail.js # Shipment detail: expense/vendor modals
│       └── vendors.js      # Vendors page: add/edit/contacts modals
└── requirements.txt
```

**Where things belong:**

- New routes → `app.py` only, no blueprints
- DB CRUD helpers → `database/db.py` only, never inline in routes
- Complex read queries (joins, aggregates, filters) → `database/queries.py`
- New pages → new `.html` file extending `base.html`
- Sidebar → edit `templates/_sidebar.html`; pass `active_section=` from the route
- Page-specific styles → new `.css` file, not inline `<style>` tags
- Page-specific JS → new `.js` file loaded at bottom of that template
- Global/shared JS → `main.js` (loaded by `base.html` on every page)

---

## Code style

- Python: PEP 8, snake_case for all variables and functions
- Templates: Jinja2 with `url_for()` for every internal link — never hardcode URLs
- Route functions: one responsibility only — fetch data, render template, done
- DB queries: always use parameterized queries (`?` placeholders) — never f-strings in SQL
- Error handling: use `abort()` for HTTP errors, not bare `return "error string"`

---

## Tech constraints

- **Flask only** — no FastAPI, no Django, no other web frameworks
- **SQLite only** — no PostgreSQL, no SQLAlchemy ORM, no external DB
- **Vanilla JS only** — no React, no jQuery, no npm packages
- **No new pip packages** — work within `requirements.txt` as-is unless explicitly told otherwise
- Python 3.10+ assumed — f-strings and `match` statements are fine

---

## Subagent Policy

- Always use a builtin explore subagent for codebase exploration
  before implementing any new feature
- Always use a subagent to verify test results
  after any implementation
- When asked to plan, delegate codebase research
  to a subagent before presenting the plan
- always use a builtin plan subagent in plan mode

---

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run dev server (port 5001)
python app.py

# Run all tests
pytest

# Run a specific test file
pytest tests/test_foo.py

# Run a specific test by name
pytest -k "test_name"

# Run tests with output visible
pytest -s
```

---

## Implemented routes

### Auth & static

| Route             | Status                                                     |
| ----------------- | ---------------------------------------------------------- |
| `GET /`           | Implemented — renders `landing.html`                       |
| `GET /register`   | Implemented — registration form                            |
| `POST /register`  | Implemented — validates + creates user, redirects to login |
| `GET /login`      | Implemented — login form                                   |
| `POST /login`     | Implemented — validates credentials, sets session          |
| `GET /logout`     | Implemented — clears session, redirects to landing         |
| `GET /terms`      | Implemented — static terms page                            |
| `GET /privacy`    | Implemented — static privacy page                          |

### Profile / dashboard

| Route          | Status                                                                       |
| -------------- | ---------------------------------------------------------------------------- |
| `GET /profile` | Implemented — dashboard: sidebar, stats, date filter, transactions, category breakdown (login required) |

### Expenses (standalone, pre-shipment routes)

| Route                          | Status                                                     |
| ------------------------------ | ---------------------------------------------------------- |
| `GET /expenses/add`            | Implemented — standalone add-expense form (login required) |
| `POST /expenses/add`           | Implemented — creates expense, redirects to profile        |
| `POST /expenses/<id>/edit`     | Implemented — updates expense, redirects to profile        |
| `POST /expenses/<id>/delete`   | Implemented — deletes expense, returns JSON `{"ok": true}` |

### Shipments

| Route                                          | Status                                                              |
| ---------------------------------------------- | ------------------------------------------------------------------- |
| `GET /shipments`                               | Implemented — list with active/closed sections (login required)     |
| `GET /shipments/add`                           | Implemented — add shipment form (login required)                    |
| `POST /shipments/add`                          | Implemented — creates shipment, redirects to `/shipments`           |
| `GET /shipments/<id>`                          | Implemented — detail: expenses, vendors, billing (login required, ownership check) |
| `GET /shipments/<id>/edit`                     | Implemented — edit shipment form (login required, ownership check)  |
| `POST /shipments/<id>/edit`                    | Implemented — updates shipment, redirects to `/shipments`           |
| `POST /shipments/<id>/status`                  | Implemented — inline status update, returns JSON `{"ok": true, "status": ...}` |
| `POST /shipments/<id>/expenses/add`            | Implemented — adds expense to shipment, redirects to detail         |
| `POST /shipments/<id>/expenses/<id>/edit`      | Implemented — edits shipment expense, redirects to detail           |
| `POST /shipments/<id>/expenses/<id>/delete`    | Implemented — deletes shipment expense, returns JSON `{"ok": true}` |
| `POST /shipments/<id>/vendors/add`             | Implemented — links vendor to shipment, redirects to detail         |
| `POST /shipments/<id>/vendors/<sv_id>/edit`    | Implemented — updates shipment–vendor record, redirects to detail   |
| `POST /shipments/<id>/vendors/<sv_id>/delete`  | Implemented — unlinks vendor from shipment, returns JSON `{"ok": true}` |

### Vendors

| Route                                          | Status                                                              |
| ---------------------------------------------- | ------------------------------------------------------------------- |
| `GET /vendors`                                 | Implemented — vendor list with filters + contacts (login required)  |
| `POST /vendors/add`                            | Implemented — creates vendor, redirects to `/vendors`               |
| `POST /vendors/<id>/edit`                      | Implemented — updates vendor, redirects to `/vendors` (ownership check) |
| `GET /vendors/<id>/contacts`                   | Implemented — returns contacts JSON (ownership check)               |
| `GET /vendors/<id>/info`                       | Implemented — returns vendor category/currency JSON (ownership check) |
| `POST /vendors/<id>/contacts/add`              | Implemented — creates contact, redirects to `/vendors` (ownership check) |
| `POST /vendors/<id>/contacts/<id>/edit`        | Implemented — updates contact, redirects to `/vendors` (ownership check) |
| `POST /vendors/<id>/contacts/<id>/delete`      | Implemented — deletes contact, returns JSON `{"ok": true}` (ownership check) |

### Billing, Notifications, Stubs

| Route              | Status                                                                           |
| ------------------ | -------------------------------------------------------------------------------- |
| `GET /billing`     | Implemented — shipment-wise vendor billing dashboard (login required)            |
| `GET /notifications` | Implemented — recent system alerts (login required)                            |
| `GET /emails`      | Stub — placeholder page (login required)                                         |
| `GET /reports`     | Stub — placeholder page (login required)                                         |
| `GET /settings`    | Stub — placeholder page (login required)                                         |

**Do not add new routes unless the active spec explicitly defines them.**

---

## Sidebar structure

The sidebar lives in `templates/_sidebar.html` and is included with `{% include '_sidebar.html' %}` in every page that uses the two-column shell layout.

- **8 accordion groups** (Overview, Shipments, Vendors, Billing, Emails, Notifications, Reports, Settings), each with 2–4 sub-links
- **Active group** — the group matching `active_section` is pre-expanded server-side via `{% if active_section == 'shipments' %} is-open{% endif %}` on the group `<div>`
- **`active_section`** — every route that renders a sidebar page must pass this string (e.g. `active_section="shipments"`) to `render_template()`
- **Accordion toggle** — `main.js` handles `.sidebar-group-toggle` click to toggle `is-open` class; CSS drives the `max-height` + `opacity` transition
- **Sub-link active state** — individual sub-links use `{% if request.endpoint == 'shipments' %} sidebar-sub-link--active{% endif %}`
- **Placeholder sub-links** — sub-links with no route yet use `href="#"`
- **Footer** — Sign out link in `.sidebar-footer` below the nav

---

## Profile page structure

The profile page (`/profile`) uses a two-column layout (`.profile-shell`):

- **Left sidebar** (220 px, sticky) — rendered via `_sidebar.html` with `active_section="overview"`
- **Right main area** — user info header, date-filter bar, 3 stat cards, recent transactions table with Edit/Delete, category breakdown with progress bars
- Two modals (Add Expense, Edit Expense) rendered as `position: fixed` overlays outside the shell div; toggled by `profile.js`

---

## Navbar

`base.html` navbar is full-width (no max-width constraint). When **logged in**: shows a "Sign out" link (`.nav-cta`). When **logged out**: shows "Sign in" and "Get started".

---

## Database schema

```sql
users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    DEFAULT (datetime('now'))
)

shipments (
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
)

expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,          -- ISO 8601: YYYY-MM-DD
    description TEXT,
    shipment_id INTEGER REFERENCES shipments(id) ON DELETE SET NULL,
    created_at  TEXT    DEFAULT (datetime('now'))
)

vendors (
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
    currency           TEXT    NOT NULL DEFAULT 'INR',
    status             TEXT    NOT NULL DEFAULT 'ACTIVE',
    notes              TEXT,
    created_at         TEXT    DEFAULT (datetime('now')),
    updated_at         TEXT,
    created_by         INTEGER,
    updated_by         INTEGER
)

vendor_contacts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id  INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    title      TEXT,
    phone      TEXT,
    email      TEXT,
    is_primary INTEGER NOT NULL DEFAULT 0,
    notes      TEXT,
    created_at TEXT    DEFAULT (datetime('now'))
)

shipment_vendors (
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
)

system_alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    entity_type  TEXT    NOT NULL,
    entity_id    INTEGER,
    entity_label TEXT,
    action       TEXT    NOT NULL,
    description  TEXT,
    created_at   TEXT    DEFAULT (datetime('now'))
)
```

`get_db()` enables `PRAGMA foreign_keys = ON` on every connection.

---

## database/db.py — key functions

| Function | Purpose |
|----------|---------|
| `get_db(path)` | Open SQLite connection with FK enforcement |
| `init_db(path)` | Create all tables |
| `seed_db(path)` | Insert demo data |
| `create_user / get_user_by_email / get_user_by_id` | User CRUD |
| `create_expense / get_expense_by_id / update_expense / delete_expense` | Standalone expense CRUD |
| `create_vendor / get_vendor_by_id / get_vendors_by_user / update_vendor / delete_vendor` | Vendor CRUD |
| `get_vendor_row(id)` | Fetch single vendor row (used for ownership checks) |
| `create_contact / get_contacts_by_vendor / get_contact_by_id / update_contact / delete_contact` | Vendor contact CRUD |
| `create_shipment / get_shipment_by_id / get_shipments_by_user / update_shipment / update_shipment_status` | Shipment CRUD |
| `get_shipment_by_number(number)` | Uniqueness check |
| `get_expenses_by_shipment / create_shipment_vendor / get_vendors_by_shipment / update_shipment_vendor / delete_shipment_vendor` | Shipment associations |
| `get_total_payables_by_shipment / get_total_receivables_by_shipment` | Billing aggregates |
| `log_alert(user_id, entity_type, entity_id, entity_label, action, description)` | Write system alert |

## database/queries.py — key functions

| Function | Purpose |
|----------|---------|
| `get_user_by_id(user_id)` | User with derived `initials` field |
| `get_summary_stats(user_id, from_date, to_date)` | Profile dashboard stats |
| `get_recent_transactions(user_id, limit, from_date, to_date)` | Expense list for profile |
| `get_category_breakdown(user_id, from_date, to_date)` | Category progress bars |
| `get_filtered_vendors(vendor_type, vendor_category, vendor_status)` | Vendor list with filters |
| `get_billing_stats(user_id)` | Billing dashboard summary cards |
| `get_shipment_billing_list(user_id, payment_status, billing_type)` | Billing table with filter support |
| `get_recent_alerts(user_id, limit)` | Notifications page alerts |

---

## Ownership checks

All vendor mutation routes (`edit_vendor`, `add_contact`, `edit_contact`, `delete_contact_route`) and vendor read-API routes (`get_vendor_contacts`, `vendor_info`) verify that `vendor["user_id"] == session["user_id"]` after the 404 check, and `abort(403)` if not. Shipment routes (`shipment_detail`, `edit_shipment`) do the same for shipments.

---

## Warnings and things to avoid

- **Never hardcode URLs** in templates — always use `url_for()`
- **Never put DB logic in route functions** — CRUD in `database/db.py`, complex reads in `database/queries.py`
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync
- **Never use JS frameworks** — the frontend is intentionally vanilla
- **FK enforcement is manual** — `get_db()` must run `PRAGMA foreign_keys = ON` on every connection
- The app runs on **port 5001**, not the Flask default 5000 — don't change this
- **CSS variables only** — never hardcode hex colour values; use the variables defined in `:root` in `style.css`
- **Always pass `active_section=`** to `render_template()` for any route that renders a page with `_sidebar.html` — the sidebar depends on it for pre-expanding the correct group
- **Sidebar edits go in `_sidebar.html`** — not in individual page templates
- **Global JS goes in `main.js`** — page-specific JS goes in its own file loaded at the bottom of that template
