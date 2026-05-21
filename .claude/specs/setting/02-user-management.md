# Spec: User Management

## Overview

This feature adds a User Management settings page at `/settings/user-management`, giving logged-in users the ability to update their display name, change their email address, and change their password. All changes operate on the existing `users` table — no new tables are needed. This is step 02 in the Settings module and wires the "User Management" sidebar sub-link that currently points to `href="#"`.

## Depends on

- Step 03 — Login and logout (session management, `werkzeug.security`)
- Step 01 (setting) — Company Profile (sidebar layout, settings CSS, `active_section="settings"` pattern)

## Routes

- `GET /settings/user-management` — render user management form with current name and email pre-filled — logged-in
- `POST /settings/user-management/profile` — validate and update display name + email; redirect back to GET — logged-in
- `POST /settings/user-management/password` — verify current password, validate new password, update hash; redirect back to GET — logged-in

## Database changes

No new tables. Add two helper functions to `database/db.py`:

- `update_user_profile(user_id, name, email)` — UPDATE `users` SET name and email WHERE id = user_id
- `update_user_password(user_id, password_hash)` — UPDATE `users` SET password_hash WHERE id = user_id

Both use parameterised queries. `get_user_by_email` (already exists) is used to detect email conflicts before updating.

## Templates

- **Create:** `templates/settings_user_management.html` — two-column shell (sidebar + main), two distinct card sections: "Profile" (name + email fields) and "Change Password" (current password + new password + confirm new password fields)
- **Modify:** `templates/_sidebar.html` — wire the "User Management" sub-link from `href="#"` to `url_for('user_management_settings')` and add active-state class check

## Files to change

- `app.py` — add `GET /settings/user-management`, `POST /settings/user-management/profile`, and `POST /settings/user-management/password` routes
- `database/db.py` — add `update_user_profile(user_id, name, email)` and `update_user_password(user_id, password_hash)` helpers
- `templates/_sidebar.html` — wire "User Management" sub-link with active-state
- `static/css/settings.css` — extend with any new styles needed for the user management page (reuse existing settings card styles where possible)

## Files to create

- `templates/settings_user_management.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw SQLite via `get_db()`
- Parameterised queries only — `?` placeholders, never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`; verified with `check_password_hash`
- Use CSS variables — never hardcode hex values; use variables from `:root` in `style.css`
- All templates extend `base.html`
- DB CRUD helpers go in `database/db.py` only, not inline in routes
- Pass `active_section="settings"` to `render_template()` so the sidebar Settings group expands
- The "User Management" sub-link in `_sidebar.html` uses `{% if request.endpoint == 'user_management_settings' %} sidebar-sub-link--active{% endif %}`
- Profile update validation: `name` is required and must be non-empty; `email` is required, must be non-empty, and must not already belong to another user (check via `get_user_by_email`)
- Password update validation: `current_password` must match the stored hash (`check_password_hash`); `new_password` must be at least 8 characters; `confirm_password` must match `new_password`
- On successful profile update: update `session["user_name"]` to reflect the new name; flash `"Profile updated."` with category `"success"`
- On successful password change: flash `"Password changed."` with category `"success"`
- On any validation failure: flash the specific error with category `"error"` and do not save
- Log an alert via `log_alert()` after each successful change: action `"updated"`, entity_type `"user"`, entity_id = user_id, entity_label = user name
- Render flash messages in `settings_user_management.html` (not in `base.html`)
- The two forms (Profile and Change Password) are separate `<form>` elements posting to their own routes — they do not share a submit button
- Display read-only account info (join date from `created_at`) in the page header — this is shown but not editable

## Definition of done

- [ ] Visiting `/settings/user-management` while logged in renders the page with the sidebar, Settings group expanded, and "User Management" sub-link highlighted
- [ ] The profile form is pre-filled with the current user's name and email
- [ ] The join date is displayed as a read-only field
- [ ] Submitting the profile form with a blank name shows a validation error flash and does not save
- [ ] Submitting the profile form with an email already used by another account shows a validation error flash and does not save
- [ ] Submitting the profile form with valid name and email updates the record, updates `session["user_name"]`, and shows a success flash
- [ ] Submitting the password form with an incorrect current password shows a validation error flash and does not save
- [ ] Submitting the password form where new and confirm passwords do not match shows a validation error flash and does not save
- [ ] Submitting the password form with a new password under 8 characters shows a validation error flash and does not save
- [ ] Submitting the password form with valid data updates the password hash and shows a success flash; the user can log in with the new password
- [ ] A system alert is written to `system_alerts` after every successful profile or password change
- [ ] `/settings/user-management` returns a redirect to `/login` when accessed without a session
- [ ] Page is styled consistently with the rest of the settings module using CSS variables only
