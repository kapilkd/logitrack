# Spec: Left Menu Links Working Urls

## Overview

The profile page sidebar currently has eight navigation links (Overview, Shipments, Vendors, Billing, Emails, Notifications, Reports, Settings) all pointing to `#`. This feature gives each link a real URL: Overview maps to the existing `/profile` route, Shipments maps to a new `/shipments` list page, and the remaining six items each get a stub route that renders a simple "coming soon" placeholder. After this step every sidebar link will be a live `url_for()` call rather than a dead `#` anchor.

## Depends on

- Step 04 — Profile Page (profile page and sidebar must exist)
- Step 09 — Profile Page Menu Bar (sidebar HTML structure must be in place)

## Routes

- `GET /shipments` — lists all shipments for the logged-in user — logged-in
- `GET /vendors` — placeholder page — logged-in
- `GET /billing` — placeholder page — logged-in
- `GET /emails` — placeholder page — logged-in
- `GET /notifications` — placeholder page — logged-in
- `GET /reports` — placeholder page — logged-in
- `GET /settings` — placeholder page — logged-in

## Database changes

No database changes.

## Templates

- **Create:**
  - `templates/shipments.html` — shipments list page extending `base.html`, showing a table of the user's expenses (reuses data from `get_recent_transactions`)
  - `templates/placeholder.html` — generic "coming soon" page extending `base.html`, accepts a `title` variable
- **Modify:**
  - `templates/profile.html` — replace every `href="#"` in the sidebar `<nav>` with the appropriate `url_for()` call; add `sidebar-link--active` logic so the correct link is highlighted based on the current route

## Files to change

- `app.py` — add the seven new routes listed above
- `templates/profile.html` — update sidebar link `href` attributes and active-state logic

## Files to create

- `templates/shipments.html`
- `templates/placeholder.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- All new routes must call `login_required` (redirect to `/login` if `user_id` not in session)
- Use `url_for()` for every internal link — never hardcode paths
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Placeholder pages must share a single `placeholder.html` template (no copy-paste per page)
- The `sidebar-link--active` class must be applied dynamically (via `request.endpoint` or a template variable) — not hardcoded on Overview
- `/shipments` list page must query only the logged-in user's expenses (no cross-user data leak)

## Definition of done

- [ ] Clicking "Overview" in the sidebar navigates to `/profile`
- [ ] Clicking "Shipments" in the sidebar navigates to `/shipments` and shows the user's expense records in a table
- [ ] Clicking "Vendors", "Billing", "Emails", "Notifications", "Reports", or "Settings" each navigate to their respective route and render a "coming soon" placeholder page with the correct section title
- [ ] The active sidebar link is highlighted on every page (correct `sidebar-link--active` class applied)
- [ ] Visiting any of the new routes while logged out redirects to `/login`
- [ ] No sidebar link still uses `href="#"` (except any that are intentionally kept as sub-item placeholders inside the sidebar groups, if applicable)
- [ ] The `/shipments` page does not expose another user's data when logged in as a different account
