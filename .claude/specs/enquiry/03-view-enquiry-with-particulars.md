# Spec: View Enquiry With Particulars

## Overview

This feature adds a dedicated read-focused detail page for an enquiry at
`GET /enquiries/<id>`. It surfaces every field stored on the enquiry record
(customer info, cargo details, financial info, dates, notes) together with
the full particulars table and grand total in one place. The "View" button
in the enquiries listing currently links to `#` — this spec wires it to the
new route. An inline status-update action is also included so the user can
move an enquiry through its lifecycle without opening the full edit form.

## Depends on

- Step 01 — enquiries listing page and sidebar section
- Step 02 — new enquiry form (all enquiry fields must exist in the DB)

## Routes

- `GET /enquiries/<int:enquiry_id>` — enquiry detail view — logged-in, ownership check
- `POST /enquiries/<int:enquiry_id>/status` — inline status update, returns `{"ok": true, "status": "..."}` — logged-in, ownership check

## Database changes

No database changes. All required data is available via:
- `get_enquiry_by_id(enquiry_id)` in `database/db.py`
- `get_particulars_by_enquiry(enquiry_id)` in `database/db.py`

## Templates

- **Create:** `templates/enquiry_detail.html` — full detail view
- **Modify:** `templates/enquiries.html` — replace `href="#"` on the View button (lines 86 and 151) with `url_for('enquiry_detail', enquiry_id=e.id)`

## Files to change

- `app.py` — add `enquiry_detail` route (GET) and `enquiry_status` route (POST)
- `templates/enquiries.html` — wire View button to the new route

## Files to create

- `templates/enquiry_detail.html`
- `static/css/enquiry_detail.css`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use `get_enquiry_by_id` and `get_particulars_by_enquiry` from `database/db.py`
- Parameterised queries only
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Pass `active_section="enquiries"` to `render_template()` on every route in this spec
- Ownership check: after the 404 check, verify `enq["user_id"] == session["user_id"]` and `abort(403)` if not
- Status POST route must return JSON `{"ok": true, "status": "..."}` — not a redirect
- Valid status values come from the `ENQUIRY_STATUSES` constant already defined in `app.py`

## Page layout — enquiry_detail.html

The page uses the standard two-column shell (`.profile-shell` with `_sidebar.html`).
Inside `.profile-container`:

1. **Page header** — enquiry number as title, Back to Enquiries link on the right
2. **Action bar** — row with Edit button, Manage Particulars button, and inline status dropdown
3. **Info cards row** — two or three cards side-by-side:
   - *Customer* card: name, email, phone
   - *Cargo* card: commodity, consignment type, shipment terms, weight + unit, packages, MAWB, HAWB, origin → destination, incoterms
   - *Enquiry* card: enquiry date, follow-up date, priority badge, currency, ex.rate, estimated value
4. **Particulars card** — full-width card titled "Particulars":
   - If particulars exist: the same table shown in `enquiry_particulars.html` (read-only, no delete button, no add form)
   - Grand total row in `<tfoot>`
   - "Manage Particulars" link below the table
   - If none: empty-state message with a link to the particulars page
5. **Notes card** — shown only if `enq.notes` is non-empty; plain text block

## Inline status update

The action bar contains a `<select id="statusSelect">` pre-selected to the current status.
On `change`, JavaScript POSTs `{"status": value}` to `/enquiries/<id>/status`
and updates the displayed badge without a full page reload.
The status badge in the page header also updates.

A status badge helper: `<span class="status-badge status-badge--{{ status | lower | replace('_', '-') }}">{{ status }}</span>` — reuse the same CSS already used in `enquiries.html`.

## Definition of done

- [ ] Clicking "View" on any row in the enquiries listing navigates to `/enquiries/<id>`
- [ ] The detail page displays all enquiry fields: customer info, cargo, dates, priority, ex.rate, currency, estimated value, notes
- [ ] The particulars table is visible with all columns and the grand total row when particulars exist
- [ ] "Edit" button navigates to `/enquiries/<id>/edit`
- [ ] "Manage Particulars" button navigates to `/enquiries/<id>/particulars`
- [ ] Changing the inline status dropdown updates the status badge on the page without a full reload
- [ ] Navigating to `/enquiries/<id>` for an enquiry owned by a different user returns 403
- [ ] Navigating to `/enquiries/99999` (non-existent) returns 404
- [ ] Page renders correctly when the enquiry has no particulars and no notes
