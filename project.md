# LogiTrack

A lightweight logistics tracker and business management application for freight forwarders and logistics professionals. Built with Flask and PostgreSQL, deployed on Railway.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Flask 3.1 |
| Database | PostgreSQL (psycopg2-binary) |
| Templating | Jinja2 (server-rendered) |
| Frontend | Vanilla JS, CSS custom properties |
| Auth | Flask sessions + Werkzeug password hashing |
| Email | Gmail API (OAuth 2.0) |
| AI | Anthropic Claude API |
| PDF | pdfplumber |
| Server | Gunicorn |
| Deployment | Railway |
| Testing | pytest + pytest-flask |

## Features

### Enquiries
Manage customer enquiries end-to-end before converting them to shipments.
- Create and track enquiries with customer details, cargo specs (weight, CBM, consignment type), priority, and incoterms
- Add line-item particulars (description, quantity, unit, rate, currency) with subtotals and grand totals
- Live USD forex rate fetch from HDFC TT selling rate; manual override supported
- Inline status updates (Open → Quoted → Won / Lost / Cancelled)
- Generate printable PDF-ready invoice/quotation directly from an enquiry
- Convert confirmed enquiries into full shipments in one click

### Shipments
Track active and closed shipments across their full lifecycle.
- Shipment fields: number, origin, destination, carrier, port of loading/discharge, ETD, ETA, incoterms, status
- Statuses: Draft → Booked → In Transit → At Destination → Delivered → Closed
- Link vendors (as agents, carriers, or CHA) with billing type (Payable / Receivable), invoice details, and payment status
- Add quoted particulars per shipment with vendor cost assignment
- Per-shipment expense tracking
- Printable bill page: company profile as seller, vendors with payables and receivables

### Vendors
Maintain a vendor/partner directory with full contact and banking details.
- Fields: vendor type, category, company name, GST/PAN/IEC, address, payment terms, credit limit, bank details
- Per-vendor contacts (name, title, phone, email, primary flag)
- Status toggle: Active / Inactive
- Filter by type, category, and status

### Billing
Dashboard view of all shipment–vendor billing entries.
- Summary cards: total payables, receivables, pending payments
- Filter by payment status and billing type
- Payment recording against billing entries

### Reports
- Shipment reports: per-shipment P&L, expense breakdown, vendor costs
- Financial reports: expense trends, category breakdown, monthly summaries
- Vendor reports: vendor-wise billing and payment history

### Email (Gmail Integration)
- Connect a Gmail account via OAuth 2.0
- Sync inbox messages; view threaded email conversations
- Send and reply to emails from within the app
- AI-powered email processing: auto-summary, category detection, entity extraction, shipment/invoice reference detection
- AI auto-reply drafting in selectable tone (professional, friendly, concise, etc.)

### Settings
- **Company Profile** — logo upload, GST/PAN/IEC, address, default currency, incoterms, billing terms
- **Company Account** — additional company-level configuration
- **User Management** — update profile and change password
- **Gmail Integration** — OAuth connect/disconnect with prerequisite checks
- **Notification Settings** — system alert preferences (stub)

### Dashboard (Overview)
- Stats cards: total shipments, active shipments, total enquiries, total vendors
- Date filter with presets (Today, Week, Month, Quarter, Year) and custom range
- Recent transactions table with edit/delete
- Expense category breakdown with progress bars

### Notifications
System alerts generated automatically on key actions (shipment created, vendor linked, payment recorded, etc.)

## Architecture

```
logitrack/
├── app.py                          # All routes — single file, no blueprints
├── ai_utils.py                     # Anthropic Claude client — email processing & reply drafting
├── gmail_utils.py                  # Gmail API client, OAuth token encryption, sync & send
├── forex_utils.py                  # HDFC forex rate fetch + manual rate persistence
├── database/
│   ├── db.py                       # PostgreSQL helpers, schema (init_db), seed data, all CRUD
│   └── queries.py                  # Complex read queries: joins, aggregates, filters
├── templates/                      # Jinja2 templates (server-rendered)
├── static/
│   ├── css/                        # Page-specific stylesheets + global style.css
│   ├── js/                         # Page-specific JS files + main.js (global)
│   └── uploads/logos/              # Company logo uploads (per-user)
├── tests/                          # pytest test suite
├── requirements.txt
├── Procfile                        # Gunicorn entry point for Railway
└── .env                            # Local environment variables (not committed)
```

**Design rules:**
- All routes live in `app.py` — no blueprints
- All CRUD helpers live in `database/db.py`
- Complex joined/aggregated queries live in `database/queries.py`
- Page-specific CSS → its own `.css` file; never inline `<style>`
- Page-specific JS → its own `.js` file loaded at template bottom
- Global JS → `main.js` (loaded by `base.html` on every page)
- All templates except standalone print pages (bill_print, enquiry_invoice) extend `base.html`
- Sidebar partial (`_sidebar.html`) included by every page with the two-column shell layout

## Database Schema (key tables)

```
users               — auth; one record per account
company_profiles    — one row per user; seller identity for invoices
enquiries           — customer enquiry pre-shipment
enquiry_particulars — line items for enquiry quotations
shipments           — logistics shipments
shipment_vendors    — many-to-many: shipment ↔ vendor with billing metadata
shipment_particulars — quoted items linked to a shipment
expenses            — standalone or shipment-linked expense records
vendors             — vendor/partner directory
vendor_contacts     — per-vendor contacts
system_alerts       — notification feed (written by log_alert())
gmail_accounts      — Gmail OAuth tokens (Fernet-encrypted)
emails              — synced inbox and sent messages
email_ai_processing — AI processing results per email
```

## Setup

### Prerequisites
- Python 3.10+
- PostgreSQL (local: `logitrack_db`; test: `logitrack_test`)

### Install

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Environment variables

Create a `.env` file at the project root (never commit it):

```env
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://postgres:password@localhost:5432/logitrack_db

# Optional — required for Gmail features
GMAIL_TOKEN_KEY=<base64-urlsafe-fernet-key>

# Optional — required for AI email features
ANTHROPIC_API_KEY=sk-ant-...
```

For Gmail OAuth you also need a `credentials.json` file (Google Cloud OAuth client secret) at the project root.

### Run locally

```bash
python app.py
# App runs at http://localhost:5001
```

### Run tests

```bash
pytest                        # all tests
pytest tests/test_foo.py      # specific file
pytest -k "test_name"         # specific test
pytest -s                     # show print output
```

Tests use a separate database (`logitrack_test`) and truncate all tables on teardown.

## Deployment

The app is deployed on [Railway](https://railway.app).

- `Procfile` defines the Gunicorn entry point
- `DATABASE_URL` is set automatically by Railway's PostgreSQL plugin
- `RAILWAY_ENVIRONMENT` env var is used to detect production (disables seed data, enables secure cookies)
- Static file uploads (`static/uploads/logos/`) are ephemeral on Railway — use object storage for persistence in production

## Security

- Passwords hashed with Werkzeug (`pbkdf2:sha256`)
- Session cookies: `HttpOnly`, `SameSite=Lax`, `Secure` in production
- All DB queries use parameterized `%s` placeholders (no f-strings in SQL)
- Gmail OAuth tokens encrypted at rest with Fernet symmetric encryption
- Ownership checks (`user_id` match) on all shipment, vendor, enquiry, and email routes — `abort(403)` on mismatch
- Logo uploads restricted to known safe extensions (png, jpg, jpeg, gif, webp, svg)

## Graceful degradation

The app runs without external API credentials:
- `GMAIL_AVAILABLE = False` when `credentials.json` or `GMAIL_TOKEN_KEY` is absent — Gmail UI shows a setup guide instead of crashing
- `ANTHROPIC_AVAILABLE = False` when `ANTHROPIC_API_KEY` is absent — AI buttons are hidden or return a user-friendly error
- `FOREX_AVAILABLE` controls whether live rate fetch is attempted

## Repository

GitHub: [github.com/kapilkd/logitrack](https://github.com/kapilkd/logitrack)
