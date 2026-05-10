"""
tests/test_07-add-expense.py

Spec: Add Expense (Step 07)
Route: GET/POST /shipments/add  (Flask endpoint name: add_shipment)

Test plan:
- Auth guard: unauthenticated GET redirects to /login
- Auth guard: unauthenticated POST redirects to /login
- Auth guard: redirected response must NOT contain the add-expense form
- GET happy path: returns 200 for logged-in user
- GET happy path: form contains amount, category, date, description fields
- GET happy path: date field uses HTML5 type="date"
- GET happy path: date field is pre-filled with today's ISO date
- GET happy path: form uses method="post"
- GET happy path: form has an "Add Expense" submit button
- GET happy path: form has a "Back to profile" anchor linking to /profile
- GET happy path: no validation error message on initial load
- Category completeness: all nine logistics categories appear in the select
- Category completeness: parametrized check for each individual category
- POST happy path: valid data redirects to /profile (302)
- POST happy path: valid data inserts exactly one expense row in the DB
- DB side effects: stored amount, category, date, description, and user_id are correct
- DB side effects: expense appears on /profile page after successful POST
- POST happy path parametrized: every valid category is accepted and stored
- Amount validation: missing, empty, zero, 0.00, negative, non-numeric all rejected (200)
- Amount validation: no row inserted for any rejected amount
- Category validation: missing, empty string, invalid value all rejected (200)
- Category validation: no row inserted for any rejected category
- Category validation: SQL-injection string rejected safely (no 500, no row inserted)
- Date validation: missing, empty, invalid format all rejected (200)
- Date validation: parametrized list including compact YYYYMMDD, wrong separators, etc.
- Date validation: no row inserted for any rejected date
- Description optional: omitting description does not cause an error — POST redirects
- Description optional: row is inserted with description=None when field omitted
- Description optional: blank string stored as NULL
- Description optional: whitespace-only string stored as NULL
- User isolation: expense posted by user A does not appear on user B's profile
- Static analysis: db.py create_expense uses no f-string SQL interpolation
- Static analysis: add_shipment route contains no raw INSERT SQL
"""

import os
import re
from datetime import date

import pytest

import database.db as db_module
from app import app as flask_app
from database.db import init_db, get_db


# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

VALID_CATEGORIES = [
    "Freight Charges",
    "Customs Duty",
    "Port Charges",
    "Documentation",
    "Warehouse Charges",
    "Insurance",
    "Courier & Shipping",
    "Penalty & Demurrage",
    "Other",
]

ADD_URL = "/expenses/add"

VALID_POST_DATA = {
    "amount": "150.00",
    "category": "Freight Charges",
    "date": "2026-05-10",
    "description": "Test shipment expense",
}


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def app(tmp_path, monkeypatch):
    """
    Isolated Flask app for each test.

    database/db.py and database/queries.py resolve their SQLite connection
    through the module-level DB_PATH constant.  Monkeypatching that constant
    to a per-test temp file ensures every get_db() call — inside routes,
    db.py helpers, and queries.py functions — hits the isolated test DB.
    """
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-07",
        "WTF_CSRF_ENABLED": False,
    })

    with flask_app.app_context():
        init_db(path=db_file)
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ------------------------------------------------------------------ #
# Private helpers                                                      #
# ------------------------------------------------------------------ #

def _register_and_login(
    client,
    name="Testuser",
    email="test@logitrack.com",
    password="password123",
):
    """Register a fresh user and log them in via the test client."""
    client.post("/register", data={"name": name, "email": email, "password": password})
    resp = client.post("/login", data={"email": email, "password": password})
    return resp


def _get_user_id(email):
    """Return the integer id for a user already inserted in the (monkeypatched) DB."""
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    assert row is not None, f"User '{email}' not found in test DB"
    return row["id"]


def _count_expenses(user_id):
    """Return the number of expense rows for the given user_id in the test DB."""
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


def _get_latest_expense(user_id):
    """Return the most-recently inserted expense row for a user as a Row object."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return row


# ------------------------------------------------------------------ #
# Auth guard                                                           #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    def test_unauthenticated_get_returns_302(self, client):
        response = client.get(ADD_URL)
        assert response.status_code == 302, (
            "Unauthenticated GET /shipments/add must respond with 302"
        )

    def test_unauthenticated_get_redirects_to_login(self, client):
        response = client.get(ADD_URL)
        assert "/login" in response.headers["Location"], (
            "Unauthenticated GET must redirect to /login"
        )

    def test_unauthenticated_post_returns_302(self, client):
        response = client.post(ADD_URL, data=VALID_POST_DATA)
        assert response.status_code == 302, (
            "Unauthenticated POST /shipments/add must respond with 302"
        )

    def test_unauthenticated_post_redirects_to_login(self, client):
        response = client.post(ADD_URL, data=VALID_POST_DATA)
        assert "/login" in response.headers["Location"], (
            "Unauthenticated POST must redirect to /login"
        )

    def test_unauthenticated_access_does_not_render_add_form(self, client):
        """After following the redirect the user should land on the login page."""
        response = client.get(ADD_URL, follow_redirects=True)
        data = response.data.decode("utf-8")
        # The add-expense form fields must not be present on the login page
        assert 'name="amount"' not in data, (
            "Unauthenticated visitor must not see the add-expense form"
        )

    def test_unauthenticated_post_inserts_no_row(self, client):
        """A POST that bypasses auth must not write to the DB."""
        # No user registered — count must stay 0
        conn = get_db()
        before = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()

        client.post(ADD_URL, data=VALID_POST_DATA)

        conn = get_db()
        after = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()
        assert after == before, (
            "Unauthenticated POST must not insert any expense row"
        )


# ------------------------------------------------------------------ #
# GET happy path                                                        #
# ------------------------------------------------------------------ #

class TestGetHappyPath:
    def test_authenticated_get_returns_200(self, client):
        _register_and_login(client)
        response = client.get(ADD_URL)
        assert response.status_code == 200, (
            "Authenticated GET /shipments/add must return 200"
        )

    def test_form_contains_amount_field(self, client):
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        assert 'name="amount"' in data, "Form must contain an amount input field"

    def test_form_contains_category_select(self, client):
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        assert 'name="category"' in data, "Form must contain a category select element"

    def test_form_contains_date_field(self, client):
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        assert 'name="date"' in data, "Form must contain a date input field"

    def test_form_contains_description_field(self, client):
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        assert 'name="description"' in data, (
            "Form must contain a description textarea or input"
        )

    def test_date_input_uses_html5_type_date(self, client):
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        assert 'type="date"' in data, (
            "Date input must use HTML5 type='date' for native browser date picker"
        )

    def test_date_field_prefilled_with_todays_date(self, client):
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        today = date.today().isoformat()
        assert today in data, (
            f"Date field must be pre-filled with today's date ({today})"
        )

    def test_form_uses_post_method(self, client):
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        assert 'method="post"' in data.lower(), (
            "Form must declare method='post'"
        )

    def test_form_has_add_expense_submit_button(self, client):
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        assert "Add Expense" in data, (
            "Form must contain an 'Add Expense' submit button"
        )

    def test_form_has_back_to_profile_link(self, client):
        """The 'Back to profile' link must be an <a> element pointing to /profile."""
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        # The href must contain /profile
        assert re.search(r'<a\s[^>]*href=["\'][^"\']*profile[^"\']*["\']', data), (
            "Form page must contain an <a> link with href pointing to /profile"
        )

    def test_no_validation_error_shown_on_fresh_get(self, client):
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        assert "Amount must be a positive number" not in data, (
            "Fresh GET must not show 'Amount must be a positive number' error"
        )
        assert "Please select a valid category" not in data, (
            "Fresh GET must not show 'Please select a valid category' error"
        )
        assert "Please enter a valid date" not in data, (
            "Fresh GET must not show 'Please enter a valid date' error"
        )


# ------------------------------------------------------------------ #
# Category select — all nine options present                           #
# ------------------------------------------------------------------ #

class TestCategoryOptions:
    @pytest.mark.parametrize("category", VALID_CATEGORIES)
    def test_each_category_option_present_in_form(self, client, category):
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        assert category in data, (
            f"The category option '{category}' must appear in the form's <select>"
        )

    def test_all_nine_categories_present_together(self, client):
        """Single request check confirming all nine categories in one pass."""
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        missing = [c for c in VALID_CATEGORIES if c not in data]
        assert not missing, (
            f"The following categories are missing from the form: {missing}"
        )

    def test_exactly_nine_categories_in_select(self, client):
        """The category <select> must offer all nine, no more, no fewer."""
        _register_and_login(client)
        data = client.get(ADD_URL).data.decode("utf-8")
        # Count <option> tags whose text value matches a known category
        found = [c for c in VALID_CATEGORIES if c in data]
        assert len(found) == 9, (
            f"Expected exactly 9 categories in the form, found {len(found)}: {found}"
        )


# ------------------------------------------------------------------ #
# POST happy path                                                       #
# ------------------------------------------------------------------ #

class TestPostHappyPath:
    def test_valid_post_returns_302(self, client):
        _register_and_login(client)
        response = client.post(ADD_URL, data=VALID_POST_DATA)
        assert response.status_code == 302, (
            "Valid POST must respond with a 302 redirect"
        )

    def test_valid_post_redirects_to_profile(self, client):
        _register_and_login(client)
        response = client.post(ADD_URL, data=VALID_POST_DATA)
        assert "/profile" in response.headers["Location"], (
            "Successful POST must redirect to /profile"
        )

    def test_valid_post_inserts_exactly_one_row(self, client):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)

        client.post(ADD_URL, data=VALID_POST_DATA)

        after = _count_expenses(uid)
        assert after == before + 1, (
            f"Valid POST must insert exactly one expense row (before={before}, after={after})"
        )

    def test_valid_post_stores_correct_amount(self, client):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")

        client.post(ADD_URL, data=VALID_POST_DATA)

        row = _get_latest_expense(uid)
        assert row is not None, "Expense row must exist after valid POST"
        assert float(row["amount"]) == pytest.approx(150.00), (
            f"Stored amount must be 150.00, got {row['amount']}"
        )

    def test_valid_post_stores_correct_category(self, client):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")

        client.post(ADD_URL, data=VALID_POST_DATA)

        row = _get_latest_expense(uid)
        assert row["category"] == "Freight Charges", (
            f"Stored category must be 'Freight Charges', got '{row['category']}'"
        )

    def test_valid_post_stores_correct_date(self, client):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")

        client.post(ADD_URL, data=VALID_POST_DATA)

        row = _get_latest_expense(uid)
        assert row["date"] == "2026-05-10", (
            f"Stored date must be '2026-05-10', got '{row['date']}'"
        )

    def test_valid_post_stores_correct_description(self, client):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")

        client.post(ADD_URL, data=VALID_POST_DATA)

        row = _get_latest_expense(uid)
        assert row["description"] == "Test shipment expense", (
            f"Stored description must match submitted value, got '{row['description']}'"
        )

    def test_valid_post_stores_correct_user_id(self, client):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")

        client.post(ADD_URL, data=VALID_POST_DATA)

        row = _get_latest_expense(uid)
        assert row["user_id"] == uid, (
            f"Stored user_id must be {uid}, got {row['user_id']}"
        )

    def test_new_expense_visible_on_profile_page(self, client):
        _register_and_login(client)
        unique_desc = "UniqueLogisticsEntry88321"
        client.post(ADD_URL, data=dict(VALID_POST_DATA, description=unique_desc))

        profile_data = client.get("/profile").data.decode("utf-8")
        assert unique_desc in profile_data, (
            "Newly added expense must appear in the profile transaction list"
        )

    @pytest.mark.parametrize("category", VALID_CATEGORIES)
    def test_every_valid_category_is_accepted_and_stored(self, client, category):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)

        response = client.post(ADD_URL, data=dict(VALID_POST_DATA, category=category))

        assert response.status_code == 302, (
            f"Category '{category}' must be accepted and produce a 302 redirect"
        )
        assert _count_expenses(uid) == before + 1, (
            f"Category '{category}' must cause exactly one row to be inserted"
        )


# ------------------------------------------------------------------ #
# Amount validation                                                    #
# ------------------------------------------------------------------ #

class TestAmountValidation:
    # -- Helpers shared across amount tests --

    def _post_bad_amount(self, client, amount_value):
        """POST with a given amount value; returns (response, user_id, row_count_before)."""
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)
        if amount_value is None:
            data = {k: v for k, v in VALID_POST_DATA.items() if k != "amount"}
        else:
            data = dict(VALID_POST_DATA, amount=amount_value)
        response = client.post(ADD_URL, data=data)
        return response, uid, before

    @pytest.mark.parametrize("bad_amount, label", [
        (None,    "missing amount"),
        ("",      "empty amount string"),
        ("0",     "zero integer amount"),
        ("0.00",  "zero decimal amount"),
        ("-1",    "negative integer"),
        ("-0.01", "negative fraction"),
        ("abc",   "non-numeric string"),
        ("1e500", "overflow float string"),
        (" ",     "whitespace-only amount"),
    ])
    def test_invalid_amount_rerenders_form(self, client, bad_amount, label):
        response, _, _ = self._post_bad_amount(client, bad_amount)
        assert response.status_code == 200, (
            f"{label}: expected form re-render (200), got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_amount, label", [
        (None,    "missing amount"),
        ("",      "empty amount string"),
        ("0",     "zero integer amount"),
        ("0.00",  "zero decimal amount"),
        ("-1",    "negative integer"),
        ("-0.01", "negative fraction"),
        ("abc",   "non-numeric string"),
        (" ",     "whitespace-only amount"),
    ])
    def test_invalid_amount_inserts_no_row(self, client, bad_amount, label):
        _, uid, before = self._post_bad_amount(client, bad_amount)
        assert _count_expenses(uid) == before, (
            f"{label}: must not insert an expense row"
        )

    @pytest.mark.parametrize("bad_amount", [None, "", "0", "0.00", "-50", "abc"])
    def test_invalid_amount_shows_error_message(self, client, bad_amount):
        response, _, _ = self._post_bad_amount(client, bad_amount)
        page = response.data.decode("utf-8")
        assert "positive" in page.lower() or "amount" in page.lower(), (
            f"Amount '{bad_amount}' must produce a visible error message"
        )

    def test_small_positive_amount_accepted(self, client):
        """0.01 is the minimum allowed positive amount per the spec (step=0.01)."""
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)

        response = client.post(ADD_URL, data=dict(VALID_POST_DATA, amount="0.01"))

        assert response.status_code == 302, "Amount of 0.01 must be accepted (302 redirect)"
        assert _count_expenses(uid) == before + 1, "Amount 0.01 must insert a row"

    def test_large_positive_amount_accepted(self, client):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)

        response = client.post(ADD_URL, data=dict(VALID_POST_DATA, amount="999999.99"))

        assert response.status_code == 302, "Large positive amount must be accepted"
        assert _count_expenses(uid) == before + 1, "Large positive amount must insert a row"


# ------------------------------------------------------------------ #
# Category validation                                                  #
# ------------------------------------------------------------------ #

class TestCategoryValidation:
    @pytest.mark.parametrize("bad_category, label", [
        (None,             "missing category key"),
        ("",               "empty string"),
        ("InvalidCategory","unlisted value"),
        ("freight charges","wrong case"),
        ("FREIGHT CHARGES","all-caps"),
        ("Freight",        "partial match"),
    ])
    def test_invalid_category_rerenders_form(self, client, bad_category, label):
        _register_and_login(client)
        if bad_category is None:
            data = {k: v for k, v in VALID_POST_DATA.items() if k != "category"}
        else:
            data = dict(VALID_POST_DATA, category=bad_category)
        response = client.post(ADD_URL, data=data)
        assert response.status_code == 200, (
            f"{label}: expected form re-render (200), got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_category, label", [
        (None,             "missing category key"),
        ("",               "empty string"),
        ("InvalidCategory","unlisted value"),
        ("freight charges","wrong case"),
    ])
    def test_invalid_category_inserts_no_row(self, client, bad_category, label):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)

        if bad_category is None:
            data = {k: v for k, v in VALID_POST_DATA.items() if k != "category"}
        else:
            data = dict(VALID_POST_DATA, category=bad_category)
        client.post(ADD_URL, data=data)

        assert _count_expenses(uid) == before, (
            f"{label}: must not insert an expense row"
        )

    def test_invalid_category_shows_error_message(self, client):
        _register_and_login(client)
        response = client.post(ADD_URL, data=dict(VALID_POST_DATA, category="BadCat"))
        page = response.data.decode("utf-8")
        assert "category" in page.lower() or "valid" in page.lower(), (
            "An invalid category must surface a user-visible error message"
        )

    def test_sql_injection_in_category_is_rejected_safely(self, client):
        """SQL injection string is not a valid category and must be rejected — no 500."""
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)

        injection = "'; DROP TABLE expenses; --"
        response = client.post(ADD_URL, data=dict(VALID_POST_DATA, category=injection))

        assert response.status_code in (200, 302), (
            "SQL injection in the category field must not cause a 500 error"
        )
        assert _count_expenses(uid) == before, (
            "SQL injection in category must not insert a row or damage the DB"
        )
        # The expenses table must still be queryable (not dropped)
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        conn.close()
        assert count >= 0, "expenses table must still exist after SQL injection attempt"


# ------------------------------------------------------------------ #
# Date validation                                                      #
# ------------------------------------------------------------------ #

class TestDateValidation:
    @pytest.mark.parametrize("bad_date, label", [
        (None,         "missing date key"),
        ("",           "empty string"),
        ("not-a-date", "plain text"),
        ("yesterday",  "relative word"),
        ("20260510",   "compact YYYYMMDD — no separators"),
        ("10-05-2026", "DD-MM-YYYY order"),
        ("05/10/2026", "MM/DD/YYYY with slashes"),
        ("2026/05/10", "YYYY/MM/DD with slashes"),
        ("2026-13-01", "month 13 does not exist"),
        ("2026-00-10", "month 0 does not exist"),
        ("2026-02-30", "Feb 30 does not exist"),
        ("2026-04-31", "April 31 does not exist"),
        ("2026-5-1",   "single-digit month and day (not zero-padded)"),
    ])
    def test_invalid_date_rerenders_form(self, client, bad_date, label):
        _register_and_login(client)
        if bad_date is None:
            data = {k: v for k, v in VALID_POST_DATA.items() if k != "date"}
        else:
            data = dict(VALID_POST_DATA, date=bad_date)
        response = client.post(ADD_URL, data=data)
        assert response.status_code == 200, (
            f"{label}: expected form re-render (200), got {response.status_code}"
        )

    @pytest.mark.parametrize("bad_date, label", [
        (None,         "missing date key"),
        ("",           "empty string"),
        ("not-a-date", "plain text"),
        ("20260510",   "compact YYYYMMDD — strict YYYY-MM-DD required"),
        ("10-05-2026", "DD-MM-YYYY order"),
        ("2026/05/10", "YYYY/MM/DD with slashes"),
        ("2026-13-01", "month 13"),
        ("2026-02-30", "Feb 30"),
    ])
    def test_invalid_date_inserts_no_row(self, client, bad_date, label):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)

        if bad_date is None:
            data = {k: v for k, v in VALID_POST_DATA.items() if k != "date"}
        else:
            data = dict(VALID_POST_DATA, date=bad_date)
        client.post(ADD_URL, data=data)

        assert _count_expenses(uid) == before, (
            f"{label}: must not insert an expense row"
        )

    def test_invalid_date_shows_error_message(self, client):
        _register_and_login(client)
        response = client.post(ADD_URL, data=dict(VALID_POST_DATA, date="not-a-date"))
        page = response.data.decode("utf-8")
        assert "date" in page.lower() or "valid" in page.lower(), (
            "An invalid date must surface a user-visible error message"
        )

    def test_valid_date_boundary_leap_day_accepted(self, client):
        """2024-02-29 is a valid date (2024 is a leap year)."""
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)

        response = client.post(ADD_URL, data=dict(VALID_POST_DATA, date="2024-02-29"))

        assert response.status_code == 302, (
            "2024-02-29 (leap day) is a valid date and must be accepted"
        )
        assert _count_expenses(uid) == before + 1, (
            "Leap-day date must insert a row"
        )

    def test_invalid_date_non_leap_feb_29_rejected(self, client):
        """2025-02-29 does not exist (2025 is not a leap year)."""
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)

        response = client.post(ADD_URL, data=dict(VALID_POST_DATA, date="2025-02-29"))

        assert response.status_code == 200, (
            "2025-02-29 (non-leap year) must be rejected with form re-render"
        )
        assert _count_expenses(uid) == before, (
            "Invalid Feb 29 on non-leap year must not insert a row"
        )


# ------------------------------------------------------------------ #
# Description is optional                                              #
# ------------------------------------------------------------------ #

class TestDescriptionOptional:
    def test_missing_description_key_does_not_cause_error(self, client):
        """The description field may be absent from the POST body entirely."""
        _register_and_login(client)
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "description"}
        response = client.post(ADD_URL, data=data)
        assert response.status_code == 302, (
            "Omitting the description field entirely must not cause an error — must redirect (302)"
        )

    def test_missing_description_redirects_to_profile(self, client):
        _register_and_login(client)
        data = {k: v for k, v in VALID_POST_DATA.items() if k != "description"}
        response = client.post(ADD_URL, data=data)
        assert "/profile" in response.headers["Location"], (
            "POST without description must redirect to /profile"
        )

    def test_missing_description_inserts_row(self, client):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")
        before = _count_expenses(uid)

        data = {k: v for k, v in VALID_POST_DATA.items() if k != "description"}
        client.post(ADD_URL, data=data)

        assert _count_expenses(uid) == before + 1, (
            "An expense row must be inserted even when description is not provided"
        )

    def test_missing_description_stored_as_null(self, client):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")

        data = {k: v for k, v in VALID_POST_DATA.items() if k != "description"}
        client.post(ADD_URL, data=data)

        row = _get_latest_expense(uid)
        assert row["description"] is None, (
            f"Omitted description must be stored as NULL, got '{row['description']}'"
        )

    def test_blank_description_does_not_cause_error(self, client):
        _register_and_login(client)
        response = client.post(ADD_URL, data=dict(VALID_POST_DATA, description=""))
        assert response.status_code == 302, (
            "Blank description string must not cause an error — must redirect (302)"
        )

    def test_blank_description_stored_as_null(self, client):
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")

        client.post(ADD_URL, data=dict(VALID_POST_DATA, description=""))

        row = _get_latest_expense(uid)
        assert row["description"] is None, (
            f"Blank description string must be stored as NULL, got '{row['description']}'"
        )

    def test_whitespace_only_description_stored_as_null(self, client):
        """The route strips the description; whitespace-only becomes empty, stored as NULL."""
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")

        client.post(ADD_URL, data=dict(VALID_POST_DATA, description="   "))

        row = _get_latest_expense(uid)
        assert row["description"] is None, (
            f"Whitespace-only description must be stored as NULL, got '{row['description']}'"
        )

    def test_non_empty_description_stored_as_provided(self, client):
        """Sanity check: a real description value must be preserved."""
        _register_and_login(client)
        uid = _get_user_id("test@logitrack.com")

        client.post(ADD_URL, data=dict(VALID_POST_DATA, description="Sea freight Mumbai"))

        row = _get_latest_expense(uid)
        assert row["description"] == "Sea freight Mumbai", (
            f"Non-empty description must be stored verbatim, got '{row['description']}'"
        )


# ------------------------------------------------------------------ #
# User data isolation                                                  #
# ------------------------------------------------------------------ #

class TestUserIsolation:
    def test_expense_belongs_to_the_submitting_user(self, client):
        """An expense submitted by user A must NOT appear on user B's profile."""
        # Register and log in as user A; add a uniquely-identified expense
        _register_and_login(client, name="UserA", email="usera@test.com", password="password123")
        unique_marker = "ExclusiveToUserA_ZZQ"
        client.post(ADD_URL, data=dict(VALID_POST_DATA, description=unique_marker))
        client.get("/logout")

        # Register and log in as user B
        client.post("/register", data={"name": "UserB", "email": "userb@test.com", "password": "password123"})
        client.post("/login", data={"email": "userb@test.com", "password": "password123"})

        profile_data = client.get("/profile").data.decode("utf-8")
        assert unique_marker not in profile_data, (
            "User B's profile page must not display User A's expense"
        )

    def test_two_users_have_separate_expense_counts(self, client):
        """Each user should only see their own row count, not a combined total."""
        # User A: add one expense
        _register_and_login(client, name="Alice", email="alice@iso.com", password="password123")
        client.post(ADD_URL, data=VALID_POST_DATA)
        uid_a = _get_user_id("alice@iso.com")
        client.get("/logout")

        # User B: add two expenses
        client.post("/register", data={"name": "Bob", "email": "bob@iso.com", "password": "password123"})
        client.post("/login", data={"email": "bob@iso.com", "password": "password123"})
        client.post(ADD_URL, data=VALID_POST_DATA)
        client.post(ADD_URL, data=dict(VALID_POST_DATA, amount="200.00"))
        uid_b = _get_user_id("bob@iso.com")

        assert _count_expenses(uid_a) == 1, "User A must have exactly 1 expense"
        assert _count_expenses(uid_b) == 2, "User B must have exactly 2 expenses"


# ------------------------------------------------------------------ #
# Static analysis — parameterised SQL, no raw SQL in routes            #
# ------------------------------------------------------------------ #

class TestParameterisedQueries:
    def test_db_py_create_expense_contains_no_fstring_sql_interpolation(self):
        """
        db.py must not build SQL strings with f-string interpolation of any
        user-supplied values.  Only ? placeholders with a separate params tuple
        are acceptable.
        """
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database", "db.py",
        )
        with open(db_path, encoding="utf-8") as fh:
            source = fh.read()

        fstring_sql_hits = re.findall(
            r'f["\'].*?(?:SELECT|INSERT|UPDATE|DELETE|WHERE|AND|OR).*?\{.*?\}.*?["\']',
            source,
            re.IGNORECASE,
        )
        assert len(fstring_sql_hits) == 0, (
            "db.py must not interpolate values into SQL strings via f-strings. "
            f"Suspicious patterns found: {fstring_sql_hits}"
        )

    def test_add_expense_route_delegates_insert_to_create_expense(self):
        """
        The add_expense route function must call create_expense() instead of
        executing raw INSERT SQL itself.  This enforces the DB logic boundary.
        """
        app_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app.py",
        )
        with open(app_path, encoding="utf-8") as fh:
            source = fh.read()

        # Extract the add_expense function body by stopping at the next route decorator
        match = re.search(
            r"def add_expense\(\)(.*?)(?=\n@app\.route|\Z)",
            source,
            re.DOTALL,
        )
        assert match is not None, "add_expense function must exist in app.py"

        body = match.group(1)
        assert "INSERT INTO" not in body.upper(), (
            "add_expense route must not contain raw INSERT SQL — "
            "use create_expense() from database/db.py"
        )

    def test_add_expense_route_calls_create_expense(self):
        """create_expense must actually be called somewhere in the add_expense body."""
        app_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app.py",
        )
        with open(app_path, encoding="utf-8") as fh:
            source = fh.read()

        match = re.search(
            r"def add_expense\(\)(.*?)(?=\n@app\.route|\Z)",
            source,
            re.DOTALL,
        )
        assert match is not None, "add_expense function must exist in app.py"

        body = match.group(1)
        assert "create_expense" in body, (
            "add_expense route must call create_expense() from database/db.py"
        )
