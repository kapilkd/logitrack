# Spec: Add Expense

## Overview

This feature allows logged-in users to add a new logistics expense entry through a
dedicated form page at `/shipments/add`. The user fills in the amount, category,
date, and an optional description; on submission the row is inserted into the
`expenses` table and the user is redirected back to their profile. This is the
primary data-entry path in logitrack — without it, all profile stats and
transaction history rely solely on seeded data.

## Depends on

- Step 01 — Database Setup (`expenses` table exists)
- Step 03 — Login / Logout (session-gated access)
- Step 04 — Profile Page (redirect destination after a successful add)
- Step 05 — Backend Routes for Profile Page (profile page renders live data)

## Routes

- `GET  /shipments/add` — render the add-expense form — logged-in only
- `POST /shipments/add` — validate and insert the new expense row, then redirect
  to `/profile` on success or re-render the form with an error on failure —
  logged-in only

## Database changes

No new tables or columns. The `expenses` table already exists:

```sql
expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,        -- YYYY-MM-DD
    description TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
)
```

A new `create_expense` helper must be added to `database/db.py` to encapsulate
the INSERT. No raw SQL in the route.

## Templates

- **Create:** `templates/add_expense.html`
  - Extends `base.html`
  - Form with `method="post"` and `action="{{ url_for('add_shipment') }}"`
  - Fields:
    - `amount` — number input, step `0.01`, min `0.01`, required
    - `category` — `<select>` with a fixed list of logistics categories (see Rules)
    - `date` — `type="date"` HTML5 input, required, defaults to today's date
    - `description` — optional textarea, max 200 characters
  - A submit button ("Add Expense")
  - An error message area that renders only when an error is passed to the template
  - A "Back to profile" link using `url_for('profile')`

## Files to change

- `app.py` — replace the `/shipments/add` stub with a real GET/POST route:
  - GET: session-guard, render `add_expense.html` with today's date pre-filled
  - POST: validate inputs, call `create_expense`, redirect to `profile` on success
- `database/db.py` — add `create_expense(user_id, amount, category, date, description)`

## Files to create

- `templates/add_expense.html` — the add-expense form page

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never interpolate user input into SQL strings
- Passwords hashed with werkzeug (unchanged)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Category options are a fixed, hard-coded list in the template (no DB lookup):
  `Freight Charges`, `Customs Duty`, `Port Charges`, `Documentation`,
  `Warehouse Charges`, `Insurance`, `Courier & Shipping`, `Penalty & Demurrage`,
  `Other`
- Amount must be a positive number; reject zero and negative values
- Date must be a valid YYYY-MM-DD string; the `type="date"` input enforces this
  client-side, but the route must also validate server-side with a try/except
- Description is optional and may be empty; store `None` if blank
- If the user is not logged in, redirect to `/login` (do not render the form)
- After a successful insert, redirect to `url_for('profile')` — do not re-render
  the add form
- The route function must call `create_expense` from `database/db.py`, not execute
  SQL directly

## Definition of done

- [ ] `GET /shipments/add` renders the add-expense form for a logged-in user
- [ ] `GET /shipments/add` redirects to `/login` for an unauthenticated visitor
- [ ] All four fields (amount, category, date, description) appear on the form
- [ ] The date input defaults to today's date when the form first loads
- [ ] The category `<select>` contains all nine logistics categories listed above
- [ ] Submitting the form with valid data inserts a row into `expenses` and
      redirects to `/profile`
- [ ] The new expense appears in the transaction list on `/profile` immediately
      after submission
- [ ] Submitting with a missing or zero amount re-renders the form with an error
      message — no row is inserted
- [ ] Submitting with a missing category re-renders the form with an error message
- [ ] Submitting with an invalid date string re-renders the form with an error message
- [ ] Description is optional — omitting it does not cause an error
- [ ] No raw SQL string contains f-string interpolation of any user-supplied value
- [ ] The "Back to profile" link on the form navigates to `/profile`
