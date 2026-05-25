# Spec: Develop New Enquiry

## Overview

This step builds the "New Enquiry" add form for the Enquiries module. It covers the GET/POST
`/enquiries/add` routes, a structured multi-section form (`add_enquiry.html`) with all enquiry
fields, and the `GET /enquiries/forex-rate` endpoint that auto-fetches the live USD → INR
T.T. Selling rate from the HDFC Bank treasury forex PDF. When submitted, the customer info is
auto-saved as an INACTIVE vendor in the `vendors` table (via the existing `create_enquiry`
DB helper). The "New Enquiry" placeholder link in `enquiries.html` is wired to the real route.

## Depends on

- Enquiry step 01 must be complete: `enquiries` table, `create_enquiry`, all enquiry constants,
  and the `/enquiries` listing route must exist
- Vendors module must be complete (`create_vendor`, `get_vendor_by_code` in `database/db.py`)

## Routes

- `GET  /enquiries/add` — render the new enquiry form — logged-in
- `POST /enquiries/add` — validate and create the enquiry (+ auto-create vendor) — logged-in
- `GET  /enquiries/forex-rate` — fetch live USD TT Selling rate from HDFC PDF, return JSON — logged-in

## Database changes

No new tables or columns. All required schema (`enquiries` table, `create_enquiry`,
`generate_customer_vendor_code`, `ENQUIRY_STATUSES`, `ENQUIRY_PRIORITIES`, `WEIGHT_UNITS`,
`CONSIGNMENT_TYPES`, `INCOTERMS`, `CURRENCIES`) are already in `database/db.py` from step 01.

## Templates

- **Create:** `templates/add_enquiry.html` — new enquiry form
- **Modify:** `templates/enquiries.html` — change "+ New Enquiry" `href="#"` to
  `href="{{ url_for('add_enquiry') }}"`

## Files to change

- `app.py` — add `GET/POST /enquiries/add` and `GET /enquiries/forex-rate` routes
- `templates/enquiries.html` — wire the "New Enquiry" button
- `requirements.txt` — add `pdfplumber`

## Files to create

- `templates/add_enquiry.html` — new enquiry form template
- `static/css/add_enquiry.css` — form-specific styles
- `forex_utils.py` — HDFC PDF fetch utility (`fetch_hdfc_usd_tt_selling_rate()`)

## New dependencies

`pdfplumber` — PDF text extraction for HDFC forex rate fetch. Add to `requirements.txt`.

## Form sections (add_enquiry.html)

The form has three clearly labelled sections:

### Section 1 — Customer Information
| Field | Input | Required |
|-------|-------|----------|
| Customer Name | text | No |
| Customer Email | email | No |
| Customer Phone | text | No |

### Section 2 — Cargo Details
| Field | Input | Required |
|-------|-------|----------|
| Commodity | text | No |
| Consignment Type | select (`CONSIGNMENT_TYPES`) | No |
| Shipment Terms | text | No |
| Weight | number (step 0.01) | No |
| Weight Unit | select (`WEIGHT_UNITS`) | No |
| Packages | number (integer) | No |
| MAWB | text | No |
| HAWB | text | No |
| Origin | text | No |
| Destination | text | No |
| Ex.rate (USD→INR) | number (step 0.01) + "Fetch Rate" button | No |

### Section 3 — Enquiry Details
| Field | Input | Required |
|-------|-------|----------|
| Status | select (`ENQUIRY_STATUSES`) | Yes (default OPEN) |
| Priority | select (`ENQUIRY_PRIORITIES`) | Yes (default NORMAL) |
| Incoterms | select (`INCOTERMS`) | No |
| Currency | select (`CURRENCIES`) | Yes (default INR) |
| Estimated Value | number (step 0.01) | No |
| Enquiry Date | date | Yes |
| Follow-up Date | date | No |
| Notes | textarea | No |

## forex_utils.py

```python
FOREX_AVAILABLE = False   # set True when pdfplumber import succeeds

def fetch_hdfc_usd_tt_selling_rate():
    """Download HDFC treasury forex PDF and return USD T.T. Selling (O/w Rem) rate as float.
    Returns None on any error."""
    ...
```

Implementation:
1. Download the PDF with `urllib.request.urlopen` (stdlib — no new package)
2. Open with `pdfplumber.open(io.BytesIO(data))`
3. Iterate pages, extract words, find row containing "United States Dollar"
4. In that row, locate the "T.T. Selling" column value
5. Return `float(value)` or `None`
6. Wrap everything in try/except — never crash the route

## app.py route outlines

### GET/POST /enquiries/add

```
GET  → render add_enquiry.html with all constants, today's date, active_section="enquiries"
POST → extract all form fields via _f() helper
       validate: enquiry_date is required
       call create_enquiry(uid, data)
       log_alert(uid, "enquiry", new_row["id"], new_row["enquiry_number"], "created", ...)
       redirect to url_for("enquiries")
       on error: re-render form with error= and form=request.form
```

### GET /enquiries/forex-rate

```
→ call fetch_hdfc_usd_tt_selling_rate() from forex_utils
→ if rate: return jsonify({"ok": True, "rate": rate})
→ else:    return jsonify({"ok": False, "error": "Could not fetch rate"}), 502
```

## "Fetch Rate" button behaviour (JS in add_enquiry.html)

- Inline `<script>` in the template (no separate .js file needed)
- On click: `fetch('/enquiries/forex-rate')` → on success populate `#ex_rate` input
- Show a spinner on the button while fetching; restore on completion
- On error: show a brief inline message next to the field

## Rules for implementation

- No SQLAlchemy or ORMs — raw psycopg2 with `%s` placeholders only
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with werkzeug (not applicable here)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Always pass `active_section="enquiries"` to `render_template()`
- Follow the `_f(key)` helper pattern from `/shipments/add` for form field extraction
- `forex_utils.py` must set `FOREX_AVAILABLE = False` if `pdfplumber` import fails, and the
  route must return a graceful error JSON rather than crashing
- The "Fetch Rate" button JS must be inline in `add_enquiry.html` — no separate .js file
- Form must re-populate all fields on validation error (pass `form=request.form`)
- `log_alert` must be called on successful enquiry creation

## Definition of done

- [ ] `GET /enquiries/add` renders the form without errors when logged in
- [ ] Navigating to `/enquiries/add` while logged out redirects to `/login`
- [ ] The form shows three labelled sections: Customer Information, Cargo Details, Enquiry Details
- [ ] Submitting the form with only `enquiry_date` filled creates an enquiry and redirects to `/enquiries`
- [ ] The new enquiry appears in the listing with an auto-generated `ENQ-<year>-NNN` number
- [ ] Submitting with `customer_name` filled creates an INACTIVE vendor in the vendors table
  with `vendor_type=INBOUND`, `vendor_category=CUSTOMER`, code `CUST-<year>-NNN`
- [ ] Submitting without `enquiry_date` re-renders the form with an error message and all
  previously entered values preserved
- [ ] "Fetch Rate" button calls `GET /enquiries/forex-rate` and populates the Ex.rate field
- [ ] `GET /enquiries/forex-rate` returns JSON `{"ok": true, "rate": <float>}` on success
- [ ] `GET /enquiries/forex-rate` returns `{"ok": false, "error": "..."}` if fetch fails
- [ ] The "+ New Enquiry" button on the listing page navigates to `/enquiries/add`
- [ ] `pdfplumber` is listed in `requirements.txt`
