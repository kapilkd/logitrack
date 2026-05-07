# Spec: Registration

## Overview

This step wires up the registration form so new users can create an account. The GET `/register` route already renders the template; this step adds the POST handler that validates the submitted data, inserts a new user into the database, and redirects to the login page on success. It also adds `create_user()` and `get_user_by_email()` helpers to `database/db.py` and sets a `secret_key` on the Flask app (required for future session use).

## Depends on

- Step 01 — Database Setup (`users` table and `get_db()` must exist)

## Routes

- `POST /register` — validates form data, creates user, redirects to `/login` on success, re-renders with error on failure — public

## Database changes

No new tables or columns. Two new helper functions added to `database/db.py`:

- `get_user_by_email(email)` — returns the matching `users` row or `None`
- `create_user(name, email, password_hash)` — inserts a new user row

## Templates

- **Modify:** `templates/register.html`
  - Fix hardcoded `action="/register"` → `action="{{ url_for('register') }}"`
  - No other changes needed (error display via `{{ error }}` is already present)

## Files to change

- `app.py` — add `app.secret_key`, add `POST` method to `@app.route('/register')`, add POST handler logic
- `database/db.py` — add `get_user_by_email()` and `create_user()`
- `templates/register.html` — fix form action to use `url_for()`

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — no f-strings or `.format()` in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` before insertion
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `app.secret_key` must be set via `os.environ.get('SECRET_KEY', 'dev-secret-key')`
- DB logic stays in `database/db.py` — no raw SQL in `app.py`
- On duplicate email, catch the `sqlite3.IntegrityError` in `create_user()` or check with `get_user_by_email()` before inserting — do not let the exception bubble to the route unhandled
- Use `abort()` for unexpected HTTP errors, not bare string returns
- After successful registration, redirect to `url_for('login')` — do not implement session login here (that is Step 3)

## Definition of done

- [ ] Submitting the form with a new name, email, and password (≥ 8 chars) creates a row in `users` and redirects to `/login`
- [ ] Submitting with an email that is already registered re-renders the form with the error "An account with that email already exists."
- [ ] Submitting with a password shorter than 8 characters re-renders with the error "Password must be at least 8 characters."
- [ ] Submitting with any field blank re-renders with the error "All fields are required."
- [ ] Stored password is a werkzeug hash, not plaintext — verifiable by inspecting the DB
- [ ] The form `action` uses `url_for('register')`, not a hardcoded URL
- [ ] No SQL strings use f-strings or `.format()` — all values passed as `?` parameters
- [ ] App starts without errors on `python app.py`
