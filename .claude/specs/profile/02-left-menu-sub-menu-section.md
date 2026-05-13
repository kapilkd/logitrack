# Spec: Left Menu Sub Menu Section

## Overview

The profile sidebar currently shows a flat list of top-level navigation links. This feature introduces expandable accordion sub-menus for sidebar sections that have real sub-pages (Shipments, Vendors, Billing, Notifications). Clicking a group header toggles its sub-items open or closed with a smooth CSS transition. Groups that have no meaningful sub-pages (Overview, Emails, Reports, Settings) remain simple single links. The active group stays expanded on page load, and the active sub-link is highlighted. This gives users direct one-click access to sub-sections without leaving the current page.

## Depends on

- Step 01 (profile) — Left Menu Links Working URLs: sidebar links must point to real `url_for()` routes before sub-menus can refine them.

## Routes

No new routes.

## Database changes

No database changes.

## Templates

- **Modify:**
  - `templates/profile.html` — restructure the sidebar `<nav>` to use accordion group markup for Shipments, Vendors, Billing, and Notifications; keep Overview, Emails, Reports, and Settings as flat `sidebar-link` anchors; pass a `active_section` template variable so the correct group is expanded on load.
  - `templates/shipments.html` — extend the shared sidebar partial if extracted, otherwise inherit the updated sidebar markup via `base.html` or include.
  - `templates/placeholder.html` — same as above; ensure the active section variable is passed from every route that renders it.

## Files to change

- `app.py` — pass `active_section` (string, e.g. `"shipments"`, `"vendors"`, `"billing"`, `"notifications"`) to every route that renders a page using the shared sidebar so the correct group is expanded on page load.
- `templates/profile.html` — replace flat sidebar links for grouped sections with accordion markup (see Rules).
- `static/css/profile.css` — add CSS for `.sidebar-group`, `.sidebar-group-toggle`, `.sidebar-sub-nav`, `.sidebar-sub-link`, `.sidebar-toggle-arrow`, and the `is-open` expanded state.
- `static/js/profile.js` — add accordion toggle logic (click handler on `.sidebar-group-toggle`); preserve existing modal logic.

## Files to create

No new files.

## New dependencies

No new dependencies.

## Accordion group structure

The following sidebar items become accordion groups with sub-links:

| Group         | Sub-links                                                                                                                                                          |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Overview      | Dashboard → `/profile`; Recent Activity → `/profile`; Quick Summary → `/profile`                                                                                   |
| Shipments     | All Shipments → `/shipments`; Create Shipment → opens Add Shipment modal; Tracking & Delivery → `/shipments/tracking`; Shipment Documents → `/shipments/documents` |
| Vendors       | Vendor List → `/vendors`; Vendor Ledger → `/vendors/ledger`; Vendor Payments → `/vendors/payments`                                                                 |
| Billing       | Invoices → `/billing`; Payables & Receivables → `/billing/accounts`; Expenses → `/billing/expenses`                                                                |
| Emails        | Inbox → `/emails`; Shipment Emails → `/emails/shipments`; Templates → `/emails/templates`                                                                          |
| Notifications | Shipment Alerts → `/notifications`; Payment Alerts → `/notifications/payments`; System Alerts → `/notifications/system`                                            |
| Reports       | Shipment Reports → `/reports/shipments`; Financial Reports → `/reports/financial`; Vendor Reports → `/reports/vendors`                                             |
| Settings      | User Management → `/settings/users`; System Settings → `/settings/system`; Notification Settings → `/settings/notifications`                                       |

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (not applicable here, included for completeness)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Accordion toggle is pure vanilla JS — no jQuery, no Alpine, no external libraries
- Use `<button>` (not `<a>`) for group headers that only expand/collapse and do not navigate
- Sub-links use `<a class="sidebar-sub-link">` with `url_for()` hrefs — never hardcode paths
- The `is-open` class is toggled on the `.sidebar-group` element; CSS drives the visual transition
- On page load, the group matching `active_section` must be pre-expanded (add `is-open` server-side via Jinja `{% if active_section == 'shipments' %}is-open{% endif %}`)
- The active sub-link receives `sidebar-sub-link--active` based on `request.endpoint`
- Sidebar width (220 px) must not change — sub-items appear within the existing sidebar, not as a flyout
- Sub-nav collapse/expand must use a CSS `max-height` transition (not `display: none` toggle) so the animation is smooth
- Arrow icon rotates 180° when group is open — use CSS `transform: rotate()` on `.sidebar-toggle-arrow`

## Definition of done

- [ ] Clicking "Shipments" in the sidebar toggles a sub-menu containing "All Shipments" and "Add Shipment"
- [ ] Clicking "Vendors" in the sidebar toggles a sub-menu containing "All Vendors" and "Internal Contacts"
- [ ] Clicking "Billing" in the sidebar toggles a sub-menu containing "Dashboard"
- [ ] Clicking "Notifications" in the sidebar toggles a sub-menu containing "Recent Alerts"
- [ ] Overview, Emails, Reports, and Settings remain flat single links (no accordion)
- [ ] The toggle arrow rotates when a group is expanded and back when collapsed
- [ ] The correct group is pre-expanded on page load (e.g. visiting `/shipments` opens the Shipments group)
- [ ] The active sub-link is visually highlighted (`sidebar-sub-link--active`) on the current page
- [ ] Clicking "Add Shipment" opens the Add Expense modal (same behaviour as the existing button)
- [ ] Multiple groups can be open simultaneously (non-exclusive accordion)
- [ ] The sidebar width remains 220 px — no horizontal overflow
- [ ] Sub-menu expand/collapse is animated (not an instant toggle)
- [ ] No sidebar link uses `href="#"` unless it is an intentional placeholder noted in this spec
