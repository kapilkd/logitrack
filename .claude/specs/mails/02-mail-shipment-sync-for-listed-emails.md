# Spec: Mail Shipment Sync For Listed Emails

## Overview

This feature enriches the email inbox list view (`/emails`) so that each email row
displays a linked shipment badge when a shipment reference has been extracted by AI
processing. Users can see at a glance which shipment a given email relates to and click
directly through to that shipment's detail page without leaving the inbox.

The `email_ai_processing` table already stores `shipment_reference` as a text string
(e.g. `"SHP-2026-001"`) after the user runs AI processing on an individual email.
This feature resolves that string to an actual `shipments` row at list-render time and
surfaces a clickable badge beside each email entry. No new database tables are required.

## Depends on

- `mails/01-gmail-integration` — emails table, email_ai_processing table, and the
  `/emails` inbox route must already be implemented and working.
- `shipments/01-vendor-shipments-alignments` — the shipments table and
  `get_shipment_by_number()` helper must already exist.

## Routes

No new routes. The existing `GET /emails` route is modified to enrich its context.

## Database changes

No new tables or columns.

A new read-only query function `get_emails_with_shipment_links(user_id)` is added to
`database/queries.py`. It performs a single LEFT JOIN across `emails`,
`email_ai_processing`, and `shipments` so the inbox list can be rendered in one
database round-trip instead of N+1 lookups:

```sql
SELECT
    e.id,
    e.gmail_message_id,
    e.gmail_thread_id,
    e.direction,
    e.from_email,
    e.from_name,
    e.to_email,
    e.subject,
    e.snippet,
    e.received_at,
    e.sent_at,
    e.synced_at,
    eap.shipment_reference,
    eap.processing_status    AS ai_status,
    s.id                     AS linked_shipment_id,
    s.shipment_number        AS linked_shipment_number,
    s.status                 AS linked_shipment_status,
    s.origin                 AS linked_shipment_origin,
    s.destination            AS linked_shipment_destination
FROM emails e
LEFT JOIN email_ai_processing eap ON eap.email_id = e.id
LEFT JOIN shipments s
       ON s.shipment_number = eap.shipment_reference
      AND s.user_id = ?
WHERE e.user_id = ?
ORDER BY COALESCE(e.received_at, e.sent_at, e.synced_at) DESC
LIMIT 100
```

## Templates

- **Modify:** `templates/emails.html`
  - Each email row gets a new `.email-shipment-badge` element after the date/direction
    area.
  - If `linked_shipment_id` is set: render a pill badge showing the shipment number
    and status, wrapped in an `<a href="{{ url_for('shipment_detail', id=email.linked_shipment_id) }}">`.
  - If `ai_status == 'DONE'` but no shipment was resolved: show a muted "no match"
    indicator (small grey dash or tooltip).
  - If AI has not processed the email yet (`ai_status` is NULL): show nothing (empty
    state is fine — don't clutter unprocessed rows).

## Files to change

- `database/queries.py` — add `get_emails_with_shipment_links(user_id)`
- `app.py` — update the `GET /emails` route to call
  `get_emails_with_shipment_links()` instead of `get_emails_by_user()`; thread-group
  logic must be updated to carry the new shipment fields through to the template
- `templates/emails.html` — add shipment badge markup in the email row
- `static/css/emails.css` — add `.email-shipment-badge` styles (pill shape, status
  colour variants using CSS variables)

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw SQL with `?` placeholders only
- Parameterised queries only — never f-strings in SQL
- The JOIN in `get_emails_with_shipment_links` must filter `s.user_id = ?` to prevent
  one user's emails from resolving to another user's shipments
- The template badge must use `url_for('shipment_detail', id=...)` — never hardcode URLs
- Badge status colours must use CSS variables from `:root` in `style.css` — never
  hardcode hex values
- All templates extend `base.html`
- The existing thread-grouping logic in `GET /emails` must continue to work correctly;
  the new query returns one row per email, so thread grouping must still be applied in
  Python before passing to the template
- The `GET /emails` route must remain login-required
- The feature must degrade gracefully: if `email_ai_processing` has no row for an
  email, the badge area simply renders empty — never raise an error

## Definition of done

- `GET /emails` renders without error for a user with no AI-processed emails (no
  badges shown, no exceptions).
- For an email that has been AI-processed with a valid `shipment_reference` that
  matches an existing shipment, the inbox row shows a clickable shipment badge
  displaying the shipment number and status.
- Clicking the shipment badge navigates to `/shipments/<id>` (the correct shipment
  detail page).
- For an AI-processed email whose `shipment_reference` does not match any shipment,
  the badge area shows a muted "no match" indicator.
- For an unprocessed email, the badge area is empty.
- Thread grouping still works correctly — emails sharing a `gmail_thread_id` are still
  grouped, and each email in the group carries its own shipment badge (or none).
- Shipment badge colours visually distinguish statuses (e.g. DELIVERED vs IN_TRANSIT
  vs DRAFT) using CSS variables.
- No N+1 database queries — the inbox loads with a single query.
- Ownership is enforced: a user cannot see shipment links belonging to another user.
