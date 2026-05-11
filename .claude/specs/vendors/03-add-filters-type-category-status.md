# Spec: Add Filters Type Category Status

## Overview

Adds a filter bar to the vendor listing page (`/vendors`) that lets users narrow the
vendor table by `vendor_type` (INBOUND / OUTBOUND), `vendor_category` (any of the 15
predefined categories), and `status` (ACTIVE / INACTIVE / BLOCKED). Filters are applied
server-side via GET query parameters so the filtered URL is bookmarkable and shareable.
The UI pattern mirrors the date-filter bar already present on the profile page — no
JavaScript required for the filter form itself, using native `<select>` elements inside
an HTML form with `method="get"`.

## Depends on

- Vendors 01 — Vendor Management Database Setup (vendors table, CRUD helpers)
- Vendors 02 — Vendor Internal Contacts (current vendors.html structure)

## Routes

No new routes. The existing `GET /vendors` route is extended to read optional query
parameters: `vendor_type`, `vendor_category`, `vendor_status`.

## Database changes

No database changes. All filter columns (`vendor_type`, `vendor_category`, `status`)
already exist in the `vendors` table.

## Templates

- **Modify:** `templates/vendors.html`
  - Add a filter bar section above the vendor table
  - Pass active filter values into the template so dropdowns reflect current selection
  - Keep vendor count in the stats cards reflecting filtered results

## Files to change

- `app.py` — Modify `GET /vendors` route to read and validate filter query params,
  pass them to a new filtered query helper, and forward active filters to the template
- `database/queries.py` — Add `get_filtered_vendors(user_id, vendor_type, vendor_category, vendor_status)`
  that builds a parameterized WHERE clause and returns matching vendors
- `templates/vendors.html` — Add filter bar UI above the table
- `static/css/vendors.css` — Add filter bar styles (`.vendor-filter-bar`, `.vendor-filter-form`,
  `.vendor-filter-group`, `.vendor-filter-select`, `.vendor-filter-btn`)

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Filter values must be validated server-side: only accept known enum values for
  `vendor_type` and `status`; `vendor_category` must be one of the 15 defined values
  (or empty/None to mean "all"). Silently ignore any unknown value passed in the URL.
- The filter form must use `method="get"` so filters appear in the URL
- An "All" option (empty value) must be available for each dropdown so users can clear
  individual filters without clearing all
- A "Clear filters" link must appear only when at least one filter is active; it links
  to bare `/vendors` with no params
- Stats cards (Total, Active, Inactive/Blocked) must reflect the **filtered** vendor set,
  not the global count
- The existing `get_vendors_by_user()` in `db.py` must NOT be changed; the new filtered
  query belongs in `queries.py`
- Filter state must be passed back to the template as a dict so the template can
  pre-select the correct `<option>` for each dropdown

## Definition of done

- [ ] Visiting `/vendors` with no query params shows all vendors (unchanged behaviour)
- [ ] Selecting "INBOUND" from the Type dropdown and submitting shows only inbound vendors
- [ ] Selecting "OUTBOUND" from the Type dropdown and submitting shows only outbound vendors
- [ ] Selecting a category (e.g. "TRANSPORTER") shows only vendors with that category
- [ ] Selecting "ACTIVE" from the Status dropdown shows only active vendors
- [ ] Selecting "INACTIVE" shows only inactive vendors; "BLOCKED" shows only blocked
- [ ] Multiple filters can be combined: e.g. type=INBOUND&status=ACTIVE narrows correctly
- [ ] The active filter values are reflected in the dropdowns after form submission
- [ ] Stats cards (Total, Active, Inactive/Blocked) update to match the filtered set
- [ ] A "Clear filters" link is visible when any filter is active and resets to all vendors
- [ ] Supplying an invalid `vendor_type` or `status` in the URL is silently ignored
      (treated as "all"), not a 400 or 500 error
- [ ] The filter bar is styled consistently with the rest of the vendors page using
      CSS variables only — no hardcoded colours
- [ ] The filtered URL is bookmarkable: reloading `/vendors?vendor_type=INBOUND&vendor_status=ACTIVE`
      produces the same results
