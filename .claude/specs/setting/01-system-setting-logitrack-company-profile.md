# Spec: System Setting Logitrack Company Profile

## Overview

This feature replaces the `/settings` stub with a real Company Profile settings page. Users can view and edit their organisation's identity — company name, legal name, industry, contact details, GST/PAN/IEC registration numbers, default currency, and default incoterms. The data is stored in a new `company_profiles` table (one row per user) and surfaced through a GET/POST route at `/settings/company-profile`. The sidebar "System Settings" sub-link is wired to this route. This is step 01 in the Settings module and lays the foundation for all future settings pages.

## Depends on

- Step 03 — Login and logout (session management)
- Step 04/05 — Profile page (sidebar layout, `_sidebar.html`, `active_section` pattern)

## Routes

- `GET /settings` — redirect to `/settings/company-profile` — logged-in
- `GET /settings/company-profile` — render company profile form pre-filled with existing data — logged-in
- `POST /settings/company-profile` — validate and save company profile, redirect back to `GET` with flash — logged-in

## Database changes

Add a new table `company_profiles`:

```sql
company_profiles (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    company_name   TEXT,
    legal_name     TEXT,
    industry       TEXT,
    website        TEXT,
    email          TEXT,
    phone          TEXT,
    address_line1  TEXT,
    address_line2  TEXT,
    city           TEXT,
    state          TEXT,
    country        TEXT,
    pincode        TEXT,
    gst_number     TEXT,
    pan_number     TEXT,
    iec_code       TEXT,
    currency       TEXT    NOT NULL DEFAULT 'INR',
    incoterms      TEXT,
    created_at     TEXT    DEFAULT (datetime('now')),
    updated_at     TEXT
)
```

- One row per user (`user_id UNIQUE`). An upsert pattern is used: insert on first save, update thereafter.

## Templates

- **Create:** `templates/settings_company_profile.html` — two-column shell (sidebar + main), company profile form with sections: Basic Info, Contact Details, Registration Numbers, Defaults
- **Modify:** `templates/_sidebar.html` — wire the "System Settings" sub-link from `href="#"` to `url_for('settings_company_profile')` and add active-state class check

## Files to change

- `app.py` — replace `/settings` stub with redirect; add `GET /settings/company-profile` and `POST /settings/company-profile` routes
- `database/db.py` — add `get_company_profile(user_id)`, `upsert_company_profile(user_id, data)` helpers
- `templates/_sidebar.html` — wire "System Settings" sub-link to real route with active-state
- `static/css/settings.css` — new file for settings page styles (import in template)

## Files to create

- `templates/settings_company_profile.html`
- `static/css/settings.css`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw SQLite via `get_db()`
- Parameterised queries only — `?` placeholders, never f-strings in SQL
- Passwords hashed with werkzeug (not applicable here, but keep in mind for any auth changes)
- Use CSS variables — never hardcode hex values; use variables from `:root` in `style.css`
- All templates extend `base.html`
- DB CRUD helpers go in `database/db.py` only, not inline in routes
- The `GET /settings` route must redirect to `/settings/company-profile` (not render its own template)
- The existing `/settings` function in `app.py` is replaced — do not keep the old stub
- `upsert_company_profile` must use `INSERT OR REPLACE` or check-then-insert/update logic; update `updated_at` on every save
- Log an alert via `log_alert()` when the company profile is saved (action: `"updated"`, entity_type: `"company_profile"`)
- Pass `active_section="settings"` to `render_template()` so the sidebar Settings group expands
- The "System Settings" sub-link in `_sidebar.html` uses `{% if request.endpoint == 'settings_company_profile' %} sidebar-sub-link--active{% endif %}`
- Form validation: `company_name` is required; all other fields are optional
- Flash messages: use `flash("Company profile saved.", "success")` on success; `flash("Company name is required.", "error")` on validation failure
- Render flash messages in `settings_company_profile.html` (not in `base.html`)
- Currency dropdown must list at least: INR, USD, EUR, GBP, AED, SGD
- Incoterms dropdown must list: EXW, FCA, FAS, FOB, CFR, CIF, CPT, CIP, DAP, DPU, DDP

## Definition of done

- [ ] Visiting `/settings` while logged in redirects to `/settings/company-profile`
- [ ] The company profile page renders with the sidebar, Settings group expanded, and "System Settings" sub-link highlighted
- [ ] A fresh user sees an empty form (all fields blank except defaults)
- [ ] Submitting the form without a company name shows a validation error flash and does not save
- [ ] Submitting with a valid company name saves all fields and shows a success flash
- [ ] Revisiting the page after saving shows all previously entered values pre-filled in the form
- [ ] Saving again updates the record (no duplicate rows for the same user)
- [ ] A system alert is written to `system_alerts` after every successful save
- [ ] `/settings/company-profile` returns 302 redirect to `/login` when accessed without a session
- [ ] Page is styled consistently with the rest of the app using CSS variables only
