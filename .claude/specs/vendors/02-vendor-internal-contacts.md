# Spec: Vendor Internal Contacts

## Overview

This feature adds a many-to-many contacts layer to the vendor directory. Each vendor can have
one or more named internal contacts (e.g. sales lead, operations manager, billing POC). Contacts
are managed through a dedicated modal triggered from the vendor listing row — consistent with the
existing Add/Edit vendor modal pattern. A "Contacts" button per vendor row opens the modal,
which lists that vendor's contacts and provides inline Add / Edit / Delete actions. This keeps
vendor contact details separate from the flat vendor record while staying within the existing
single-page, modal-driven UX pattern.

## Depends on

- Step 01: Vendor Management Database Setup — vendors table and CRUD helpers must be in place.

## Routes

- `GET  /vendors/<int:vendor_id>/contacts`              — return JSON array of contacts for that vendor — logged-in only
- `POST /vendors/<int:vendor_id>/contacts/add`          — create a new contact for a vendor — logged-in only
- `POST /vendors/<int:vendor_id>/contacts/<int:contact_id>/edit`   — update a contact — logged-in only
- `POST /vendors/<int:vendor_id>/contacts/<int:contact_id>/delete` — delete a contact, returns `{"ok": true}` — logged-in only

## Database changes

New table:

```sql
vendor_contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id   INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    title       TEXT,
    phone       TEXT,
    email       TEXT,
    is_primary  INTEGER NOT NULL DEFAULT 0,   -- 1 = primary contact, 0 = secondary
    notes       TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
)
```

Migration: add `CREATE TABLE IF NOT EXISTS vendor_contacts (...)` inside `init_db()` in `database/db.py`.

When `is_primary = 1` is set on a new or edited contact, all other contacts for that vendor must
have `is_primary` reset to 0 in the same transaction (only one primary per vendor).

## Templates

- **Modify:** `templates/vendors.html`
  - Add a "Contacts" icon/button column to the vendor table row (rightmost, before Edit).
  - Add a new `#contactsModal` overlay (position: fixed, same pattern as Add/Edit modals) containing:
    - Header: vendor name + "Contacts"
    - Contacts list (rendered server-side on modal open via JS fetch to `GET /vendors/<id>/contacts`)
    - "+ Add Contact" button that reveals an inline add-contact form within the modal
    - Per-contact row: name, title, phone, email, primary badge, Edit / Delete buttons
    - Inline edit form (hidden by default, toggled per row)

## Files to change

- `database/db.py` — add `vendor_contacts` table in `init_db()`; add CRUD helpers:
  `create_contact`, `get_contacts_by_vendor`, `get_contact_by_id`, `update_contact`, `delete_contact`
- `app.py` — add four new routes; import new DB helpers
- `templates/vendors.html` — add Contacts button column + contacts modal markup
- `static/js/vendors.js` — add contacts modal open/close, fetch-contacts-on-open, add/edit/delete handlers
- `static/css/vendors.css` — contacts modal styles, primary badge, contact row layout

## Files to create

No new files required (all additions go into existing files above).

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only
- Parameterised queries only — never f-strings in SQL
- `PRAGMA foreign_keys = ON` is already enforced by `get_db()` — rely on it for cascade deletes
- Use CSS variables — never hardcode hex colour values
- All templates extend `base.html`
- No new pip packages
- The "one primary per vendor" constraint must be enforced in Python (in `database/db.py`), not just the UI
- Delete returns JSON `{"ok": true}` (consistent with shipment delete pattern)
- The contacts modal must be a `position: fixed` overlay outside the main shell div (same as Add/Edit modals)
- Vendor ownership is NOT enforced for contacts — any logged-in user can add/edit/delete contacts on any vendor (consistent with global vendor visibility introduced in the vendor listing)

## Definition of done

- [ ] `vendor_contacts` table is created by `init_db()` (running `python app.py` on a fresh DB produces the table)
- [ ] A "Contacts" button appears in each vendor row on `/vendors`
- [ ] Clicking "Contacts" opens the contacts modal showing that vendor's name in the header
- [ ] The modal fetches and renders all contacts for that vendor via `GET /vendors/<id>/contacts`
- [ ] "+ Add Contact" form submits and the new contact appears in the list without a full page reload
- [ ] A contact can be edited inline; changes persist after page reload
- [ ] A contact can be deleted; it disappears from the list immediately
- [ ] Marking a contact as primary sets `is_primary = 1` and clears it on all other contacts for that vendor
- [ ] Primary contacts display a "Primary" badge
- [ ] Deleting a vendor (if implemented) cascades to delete its contacts (FK ON DELETE CASCADE)
- [ ] All SQL uses `?` placeholders — no string interpolation in queries
