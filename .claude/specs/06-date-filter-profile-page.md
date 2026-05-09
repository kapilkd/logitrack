# Spec: Date Filter For Profile Page

## Overview

This feature adds a date-range filter to the profile page so users can narrow the
transaction history, summary stats, and category breakdown to a specific period.
A compact filter bar will sit above the stats row with quick-select presets
(This Month, Last Month, Last 3 Months, All Time) and a custom from/to date
input pair. All three data sections — stats, transactions, and category breakdown —
must update together when the filter changes, keeping the page coherent.
The filter state is passed as query-string parameters so results are bookmarkable
and survive a page refresh.

## Depends on

- Step 04 — Profile Page (UI layout)
- Step 05 — Backend Routes for Profile Page (live queries in `database/queries.py`)

## Routes

- `GET /profile?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD` — filtered profile view — logged-in only

Both parameters are optional; omitting them is equivalent to "All Time".

## Database changes

No new tables or columns. The `expenses.date` column (TEXT, YYYY-MM-DD format)
already exists and will be used in WHERE clauses.

## Templates

- **Modify:** `templates/profile.html`
  - Add a filter bar section between the page heading and the stats row
  - Filter bar contains: four quick-select preset buttons and a custom date range
    form with `from_date` / `to_date` inputs that submit via GET to `/profile`
  - Highlight the active preset button (or "Custom" label) based on current filter
  - Pass `from_date`, `to_date`, and `active_preset` from the route so the template
    can render the correct active state without JS

## Files to change

- `database/queries.py` — update `get_summary_stats`, `get_recent_transactions`,
  and `get_category_breakdown` to accept optional `from_date` and `to_date`
  keyword arguments and apply them as parameterised WHERE clauses
- `app.py` — update `/profile` route to read `from_date` and `to_date` from
  `request.args`, validate/sanitise them, resolve which preset is active,
  and forward them to all three query functions
- `templates/profile.html` — add filter bar (see Templates section)
- `static/css/style.css` — add styles for filter bar, preset buttons, and active state

## Files to create

No new files.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never interpolate dates directly into SQL strings
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Passwords hashed with werkzeug (unchanged, for completeness)
- Date inputs use `type="date"` HTML5 inputs — no JS date-picker libraries
- Filter form must use `method="get"` so the URL reflects the active filter
- Preset buttons must be `<a>` tags linking to `/profile?from_date=...&to_date=...`
  so they work without JavaScript
- If `from_date` or `to_date` is present but not a valid YYYY-MM-DD string,
  ignore it silently and fall back to no bound on that side
- The `limit=10` cap on `get_recent_transactions` must still apply after filtering
- When no filter is active, queries must behave identically to Step 05 (no regression)

## Definition of done

- [ ] Visiting `/profile` with no query params shows all-time data (same as Step 05)
- [ ] Visiting `/profile?from_date=2025-01-01&to_date=2025-12-31` shows only
      expenses within that range in the transaction table, stats, and category breakdown
- [ ] The "This Month" preset button links to the current calendar month and is
      highlighted when that range is active
- [ ] The "Last Month" preset button links to the previous calendar month correctly
- [ ] The "Last 3 Months" preset button covers the correct 90-day window
- [ ] The "All Time" preset button strips date params from the URL and is highlighted
      when no filter is active
- [ ] The custom date inputs are pre-populated with the current `from_date` / `to_date`
      values when a custom range is active
- [ ] Submitting the custom date form navigates to the correct filtered URL
- [ ] An invalid date in the query string (e.g. `from_date=notadate`) does not
      raise an error — the filter is silently ignored for that bound
- [ ] A date range that matches zero expenses shows "No transactions found" (or
      equivalent) in the transaction table and zeros in the stats row
- [ ] No raw SQL strings contain f-string interpolation of user-supplied values
