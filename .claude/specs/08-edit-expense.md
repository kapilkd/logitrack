# Spec: Edit Expense

## Overview

This feature allows logged-in users to edit an existing expense entry from their
profile page. Each row in the Recent Transactions table gains an Edit action link
that navigates to a pre-filled form at `/shipments/<id>/edit`. On submission the
row is updated in the `expenses` table and the user is redirected back to their
profile. This replaces the Step 8 stub (`"Edit shipment — coming in Step 8"`)
and completes the create → read → update side of the expense lifecycle in
logitrack.

## Depends on

- Step 01 — Database Setup (`expenses` table exists)
- Step 03 — Login / Logout (session-gated access)
- Step 04 — Profile Page (transaction table that will receive Edit links)
- Step 05 — Backend Routes for Profile Page (`get_recent_transactions` returns expense rows)
- Step 07 — Add Expense (`create_expense` pattern and `add_expense.html` to model the edit form on)

## Routes

- `GET  /shipments/<int:id>/edit` — render the edit-expense form pre-filled with
  the existing row — logged-in only; 404 if expense does not exist; 403 if the
  expense belongs to a different user
- `POST /shipments/<int:id>/edit` — validate and update the expense row, then
  redirect to `/profile` on success or re-render the form with an error on
  failure — logged-in only; same 404/403 guards

## Database changes

No new tables or columns. The existing `expenses` table has all required columns.

A new `get_expense_by_id` helper and an `update_expense` helper must be added to
`database/db.py`.

## Templates

- **Create:** `templates/edit_expense.html`
  - Extends `base.html`
  - Identical field set to `add_expense.html`: amount, category (select), date, description
  - All fields pre-populated with the current values from the database row
  - Form action: `{{ url_for('edit_shipment', id=expense.id) }}` with `method="post"`
  - Submit button: "Save Changes"
  - Error message area that renders only when an error is passed
  - A "Cancel" link using `url_for('profile')` that discards changes

- **Modify:** `templates/profile.html`
  - Add an "Actions" column header to the `<thead>` of the transactions table
  - Add an Edit link cell to each `<tr>` in the `<tbody>` using
    `url_for('edit_shipment', id=txn.id)` — each transaction row must expose its `id`
  - The link should be styled as a small inline action link (not a full button)

## Files to change

- `app.py` — replace the `/shipments/<int:id>/edit` stub with a real GET/POST route:
  - GET: session-guard, fetch expense by id, 404 if not found, 403 if
    `expense.user_id != session["user_id"]`, render `edit_expense.html`
  - POST: same guards, validate inputs (same rules as add), call `update_expense`,
    redirect to `profile` on success
- `database/db.py` — add two new helpers:
  - `get_expense_by_id(expense_id)` → sqlite3.Row or None
  - `update_expense(expense_id, amount, category, expense_date, description)`
- `database/queries.py` — update `get_recent_transactions` to include the expense
  `id` column in the returned dicts so the template can build edit links
- `templates/profile.html` — add Actions column with Edit link per row (see Templates)

## Files to create

- `templates/edit_expense.html` — the edit-expense form page

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never interpolate user input into SQL strings
- Passwords hashed with werkzeug (unchanged)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `abort(404)` if the expense row does not exist
- `abort(403)` if `expense.user_id != session["user_id"]` — never allow cross-user edits
- Amount must be a positive number; reject zero and negative values (same as add)
- Date must be a valid YYYY-MM-DD string; validate server-side with try/except
- Description is optional; store `None` if blank
- Category must be one of the nine fixed logistics categories (same list as add)
- After a successful update, redirect to `url_for('profile')` — do not re-render the form
- `get_expense_by_id` and `update_expense` live in `database/db.py`, not inline in the route
- The `edit_shipment` route function has one responsibility: fetch, validate, update, redirect

## Definition of done

- [ ] `GET /shipments/<id>/edit` renders the edit form pre-filled with the correct
      existing values for a logged-in owner of that expense
- [ ] `GET /shipments/<id>/edit` redirects to `/login` for an unauthenticated visitor
- [ ] `GET /shipments/<id>/edit` returns 404 for a non-existent expense id
- [ ] `GET /shipments/<id>/edit` returns 403 when the logged-in user does not own
      the expense
- [ ] Submitting valid changes updates the row in the database and redirects to `/profile`
- [ ] The updated values appear in the profile page transaction list immediately after
      redirect
- [ ] Submitting with a missing or zero amount re-renders the form with an error —
      no row is updated
- [ ] Submitting with an invalid category re-renders the form with an error
- [ ] Submitting with an invalid date string re-renders the form with an error
- [ ] Each row in the profile page transaction table has an Edit link
- [ ] The Edit link for each transaction correctly navigates to
      `/shipments/<that expense's id>/edit`
- [ ] The "Cancel" link on the edit form navigates back to `/profile`
- [ ] No raw SQL strings contain f-string interpolation of any user-supplied value
