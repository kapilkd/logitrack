# Spec: Recent System Alerts

## Overview

This feature replaces the `/notifications` placeholder with a real page that shows a per-user activity feed of recent system events — inserts, updates, and deletes — across shipments, vendors, and billing entries. A new `system_alerts` table persists each event as it happens; the notifications page reads from it and renders an ordered timeline. This gives operators a quick audit trail without requiring any external logging infrastructure.

## Depends on

- `01-database-setup` — base schema and `get_db()` helper
- `03-login-and-logout` — session-based auth
- `shipments/01-vendor-shipments-alignments` — shipment CRUD routes that will be instrumented
- `vendors/01-vendor-management-database-setup` — vendor CRUD routes that will be instrumented
- `billing/01-shipment-wise-vendor-billing-dashboard` — billing CRUD routes that will be instrumented

## Routes

- `GET /notifications` — renders notifications page with recent system alerts — logged-in only

No additional routes are needed; the existing placeholder route in `app.py` is upgraded.

## Database changes

New table added in `init_db()` inside `database/db.py`:

```sql
system_alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    entity_type  TEXT    NOT NULL,   -- 'SHIPMENT', 'VENDOR', 'BILLING', 'CONTACT'
    entity_id    INTEGER,            -- ID of the affected record (NULL if deleted)
    entity_label TEXT,               -- Human-readable label e.g. 'SHP-2026-001', 'Maersk India'
    action       TEXT    NOT NULL,   -- 'CREATED', 'UPDATED', 'DELETED', 'STATUS_CHANGED'
    description  TEXT,               -- One-line summary e.g. 'Shipment SHP-2026-001 status changed to IN_TRANSIT'
    created_at   TEXT    DEFAULT (datetime('now'))
)
```

## Templates

- **Create:** `templates/notifications.html` — full notifications page extending `base.html`; displays a chronological alert feed with entity type badge, action badge, description, and relative timestamp
- **Modify:** none

## Files to change

- `database/db.py` — add `log_alert()` CRUD helper; add `system_alerts` table to `init_db()`; call `log_alert()` at the end of each route that mutates data (see Rules below)
- `database/queries.py` — add `get_recent_alerts(user_id, limit=50)` returning a list of dicts
- `app.py` — upgrade the `/notifications` route from placeholder to real implementation; import `log_alert` and call it in the mutating routes listed below
- `templates/base.html` — update the sidebar Notifications link from `#` to `url_for('notifications')`

## Files to create

- `templates/notifications.html` — notifications page
- `static/css/notifications.css` — page-specific styles (sidebar layout, alert feed, badges)

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders — never f-strings in SQL)
- Passwords hashed with werkzeug (not relevant here, but maintain the pattern)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `log_alert()` must be called from `app.py` routes, not from inside the db CRUD functions — the route is where the user context and human-readable label are both available
- Log events for these routes:
  - `add_shipment` POST → action `CREATED`, entity_type `SHIPMENT`, label = shipment_number
  - `edit_shipment` POST → action `UPDATED`, entity_type `SHIPMENT`, label = shipment_number
  - `update_shipment_status_route` POST → action `STATUS_CHANGED`, entity_type `SHIPMENT`, label = shipment_number, description includes old→new status
  - `add_vendor` POST → action `CREATED`, entity_type `VENDOR`, label = vendor_name
  - `edit_vendor` POST → action `UPDATED`, entity_type `VENDOR`, label = vendor_name
  - `add_shipment_vendor` POST → action `CREATED`, entity_type `BILLING`, label = vendor_name + shipment_number
  - `edit_shipment_vendor` POST → action `UPDATED`, entity_type `BILLING`, label = vendor_name + shipment_number
  - `delete_shipment_vendor_route` POST → action `DELETED`, entity_type `BILLING`, entity_id = None, label includes shipment_number
- `log_alert()` must never raise — wrap the DB call in `try/except` so a logging failure never breaks a route
- `get_recent_alerts()` orders by `created_at DESC`; returns at most `limit` rows
- The notifications page must show at minimum: entity type badge, action badge, description, formatted timestamp
- The page must show an empty state message if there are no alerts yet

## Definition of done

- [ ] Navigating to `/notifications` while logged in renders the notifications page (not the placeholder)
- [ ] The notifications sidebar link in the left menu navigates to `/notifications`
- [ ] After creating a new shipment via `/shipments/add`, a "CREATED" alert for that shipment appears at the top of the notifications page
- [ ] After editing a shipment via `/shipments/<id>/edit`, an "UPDATED" alert for that shipment appears
- [ ] After changing a shipment's status, a "STATUS_CHANGED" alert appears with the new status in the description
- [ ] After adding a vendor via `/vendors/add`, a "CREATED" alert for that vendor appears
- [ ] After editing a vendor via `/vendors/<id>/edit`, an "UPDATED" alert appears
- [ ] After adding a billing entry to a shipment, a "CREATED" BILLING alert appears
- [ ] After editing a billing entry, an "UPDATED" BILLING alert appears
- [ ] After deleting a billing entry, a "DELETED" BILLING alert appears
- [ ] Alerts from other users are not visible (user isolation enforced)
- [ ] If no alerts exist, the page shows an empty-state message instead of a blank list
- [ ] No hardcoded hex colour values in `notifications.css` — all colours use CSS variables from `style.css`
