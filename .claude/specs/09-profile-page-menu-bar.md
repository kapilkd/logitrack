# Spec: Profile Sidebar Menu

## Overview

This feature upgrades the existing profile page into a professional logistics dashboard layout by adding a fixed left sidebar navigation menu. The sidebar contains grouped navigation sections for Shipments, Vendors, Billing, Email Center, Reports, Notifications, and Admin modules. This is a UI-only enhancement — no backend logic, database changes, or new APIs are required.

All menu links are temporary dummy links (`#`) except already existing routes like `/profile` and `/logout`.

The existing profile content area must remain functional and render beside the new sidebar layout.

## Depends on

- Step 03 (authenticated session handling)
- Step 04 / Step 05 (existing profile page)
- Existing base layout and CSS variables

## Routes

No new routes.

Existing routes only:

- `/profile`
- `/logout`

All other menu items use dummy links (`#`).

## Database changes

No database changes.

## Templates

- **Modify:** `templates/profile.html`
  - Add fixed left sidebar layout
  - Keep existing profile/dashboard content
  - Add grouped sidebar navigation sections
  - Add collapsible submenu structure
  - Add mobile hamburger button

## Files to change

- `templates/profile.html`
  - Add sidebar navigation structure
  - Add submenu wrappers
  - Add active menu classes
  - Add mobile sidebar toggle button

- `static/css/profile.css`
  - Add sidebar layout styles
  - Add responsive dashboard grid
  - Add submenu styles
  - Add active/hover states
  - Add mobile sidebar behavior
  - Use existing CSS variables only

- `static/js/profile.js`
  - Add sidebar open/close logic
  - Add submenu expand/collapse logic
  - Close sidebar on outside click (mobile)
  - Toggle `aria-expanded`

## Files to create

No new files.

## New dependencies

No new dependencies.

## Sidebar Structure

Dashboard

- Overview

Shipments

- All Shipments
- Create Shipment
- Tracking Status
- Delivery History

Vendors

- Vendor List
- Add Vendor
- Vendor Payments
- Vendor Ledger

Billing

- Invoices
- Generate Invoice
- Pending Payments
- Expense Management

Email Center

- Gmail Inbox
- Shipment Replies
- Templates
- Auto Responses

Reports

- Shipment Reports
- Billing Reports
- Vendor Reports
- Analytics

Notifications

- Alerts
- Email Notifications
- System Logs

Admin

- User Management
- Roles & Permissions
- System Settings
- Production Settings

Bottom Section

- Logout

## Rules for implementation

- No backend changes
- No SQL changes
- No new APIs
- No placeholder backend logic
- All non-existing routes must use `href="#"`
- Use semantic HTML structure
- Use existing CSS variables only
- No hardcoded colors
- Sidebar width around 260px
- Keep layout responsive
- Mobile sidebar must slide in/out
- Submenus must support collapse/expand
- Add `aria-expanded` support
- Sidebar must not break existing profile functionality
- Keep implementation minimal and clean
- Do not explore unrelated files

## Definition of done

- [ ] Profile page shows fixed professional sidebar
- [ ] Existing profile/dashboard content still works
- [ ] Sidebar contains all required grouped menu items
- [ ] Submenus expand/collapse correctly
- [ ] Mobile hamburger menu works
- [ ] Outside click closes mobile sidebar
- [ ] Active menu state is visible
- [ ] Sidebar is responsive
- [ ] No console JS errors
- [ ] Existing routes continue working
- [ ] Logout link works correctly
