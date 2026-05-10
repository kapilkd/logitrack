# CLAUDE.md

## Project overview

logitrack is a lightweight logistic tracker and builder application built with Flask and SQLite.

---

## Architecture

```
logitrack/
├── app.py                  # All routes — single file, no blueprints
├── database/
│   ├── db.py               # SQLite helpers + CRUD: get_db(), init_db(), seed_db(),
│   │                       #   create_user(), get_user_by_email(), get_user_by_id(),
│   │                       #   create_expense(), get_expense_by_id(), update_expense(), delete_expense()
│   └── queries.py          # Profile query helpers: get_user_by_id(), get_summary_stats(),
│                           #   get_recent_transactions(), get_category_breakdown()
├── templates/
│   ├── base.html           # Shared layout — all templates must extend this
│   ├── landing.html
│   ├── login.html
│   ├── register.html
│   ├── profile.html        # Dashboard with left sidebar + expense management modals
│   ├── add_expense.html
│   ├── edit_expense.html
│   ├── terms.html
│   └── privacy.html
├── static/
│   ├── css/
│   │   ├── style.css       # Global styles: navbar, buttons, auth pages, footer
│   │   ├── landing.css     # Landing page only
│   │   └── profile.css     # Profile page: sidebar, stats, filter bar, modals
│   └── js/
│       ├── main.js         # Global JS (currently minimal)
│       └── profile.js      # Profile page: modal open/close, edit/delete handlers
└── requirements.txt
```

**Where things belong:**

- New routes → `app.py` only, no blueprints
- DB CRUD helpers → `database/db.py` only, never inline in routes
- Complex read queries (joins, aggregates) → `database/queries.py`
- New pages → new `.html` file extending `base.html`
- Page-specific styles → new `.css` file, not inline `<style>` tags
- Page-specific JS → new `.js` file loaded at bottom of that template

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

| Route                          | Status                                                      |
| ------------------------------ | ----------------------------------------------------------- |
| `GET /`                        | Implemented — renders `landing.html`                        |
| `GET /register`                | Implemented — registration form                             |
| `POST /register`               | Implemented — validates + creates user, redirects to login  |
| `GET /login`                   | Implemented — login form                                    |
| `POST /login`                  | Implemented — validates credentials, sets session           |
| `GET /logout`                  | Implemented — clears session, redirects to landing          |
| `GET /terms`                   | Implemented — static terms page                             |
| `GET /privacy`                 | Implemented — static privacy page                           |
| `GET /profile`                 | Implemented — dashboard with sidebar, stats, date filter,   |
|                                |   recent transactions, category breakdown (login required)  |
| `POST /shipments/add`          | Implemented — creates expense, redirects to profile         |
| `GET /shipments/<id>/edit`     | Implemented — edit expense form                             |
| `POST /shipments/<id>/edit`    | Implemented — updates expense, redirects to profile         |
| `POST /shipments/<id>/delete`  | Implemented — deletes expense, returns JSON `{"ok": true}`  |

**Do not add new routes unless the active spec explicitly defines them.**

---

## Profile page structure

The profile page (`/profile`) uses a two-column layout:

- **Left sidebar** (220 px, sticky) — nav links: Overview, Shipments, Vendors, Billing, Emails, Notifications, Reports, Settings + Sign out footer. All sidebar links except Sign out are currently `#` placeholders.
- **Right main area** — user info header, date-filter bar, 3 stat cards (inline label/value), recent transactions table with Edit/Delete, category breakdown with progress bars.
- Two modals (Add Expense, Edit Expense) are rendered outside the shell div as `position: fixed` overlays; toggled by `profile.js`.

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

expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,          -- ISO 8601: YYYY-MM-DD
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
)
```

`get_db()` enables `PRAGMA foreign_keys = ON` on every connection.

---

## Warnings and things to avoid

- **Never hardcode URLs** in templates — always use `url_for()`
- **Never put DB logic in route functions** — CRUD in `database/db.py`, complex reads in `database/queries.py`
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync
- **Never use JS frameworks** — the frontend is intentionally vanilla
- **FK enforcement is manual** — `get_db()` must run `PRAGMA foreign_keys = ON` on every connection
- The app runs on **port 5001**, not the Flask default 5000 — don't change this
- **CSS variables only** — never hardcode hex colour values; use the variables defined in `:root` in `style.css`
