# Spec: Login and Logout

## Overview

This step wires up credential-based login and session-based logout. The GET `/login` route already renders the form; this step adds the POST handler that verifies the email/password against the database, writes the user's id and name into Flask's signed session cookie, and redirects to `/profile` on success. Logout clears the session and redirects to the landing page. The navbar in `base.html` is updated to show context-appropriate links — "Sign in / Get started" for guests, "Sign out" for authenticated users.

## Depends on

- Step 01 — Database Setup (`users` table, `get_db()`, and `get_user_by_email()` must exist)
- Step 02 — Registration (`app.secret_key` must be set; session signing depends on it)

## Routes

- `POST /login` — validates credentials, sets session on success, re-renders with error on failure — public
- `GET /logout` — clears session, redirects to `/` — public (safe to call even when not logged in)

## Database changes

No database changes. Login uses the existing `get_user_by_email()` helper from Step 02.

## Templates

- **Modify:** `templates/login.html`
  - Fix hardcoded `action="/login"` → `action="{{ url_for('login') }}"`
  - No other changes needed (error display via `{{ error }}` is already present)
- **Modify:** `templates/base.html`
  - Nav links: when `session.user_id` is set, replace "Sign in" and "Get started" with a "Sign out" link pointing to `url_for('logout')`
  - When not logged in, keep the existing "Sign in" and "Get started" links

## Files to change

- `app.py` — add `session` and `check_password_hash` to imports; expand `/login` to `methods=["GET", "POST"]`; implement POST handler; implement `logout` route
- `templates/login.html` — fix hardcoded form action to use `url_for()`
- `templates/base.html` — conditional nav links based on `session.user_id`

## Files to create

None.

## New dependencies

No new dependencies. `check_password_hash` is already available from `werkzeug.security`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — no f-strings or `.format()` in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Session keys: use exactly `session['user_id']` (integer) and `session['user_name']` (string)
- On invalid credentials, render the same generic error "Invalid email or password." — do not reveal which field was wrong
- Logout must call `session.clear()` — do not selectively pop keys
- After login, redirect to `url_for('profile')` (stub is acceptable; do not implement profile here)
- After logout, redirect to `url_for('landing')`
- DB logic stays in `database/db.py` — no raw SQL in `app.py`

## Definition of done

- [ ] Submitting correct email and password sets `session['user_id']` and `session['user_name']` and redirects to `/profile`
- [ ] Submitting a wrong password re-renders the form with "Invalid email or password."
- [ ] Submitting an unknown email re-renders the form with "Invalid email or password."
- [ ] Visiting `/logout` clears the session and redirects to `/`
- [ ] Navbar shows "Sign out" link when logged in; shows "Sign in" and "Get started" when not
- [ ] The login form `action` uses `url_for('login')`, not a hardcoded URL
- [ ] Passwords are compared with `check_password_hash` — never plaintext
- [ ] App starts without errors on `python app.py`
