"""
tests/test_06-date-filter-profile-page.py

Spec: Date Filter For Profile Page (Step 06)

Covers:
- Auth guard (unauthenticated access redirects to /login)
- No-query-param default (all-time data, active_preset == 'all')
- Valid date-range filter scopes transactions, stats, and categories
- Zero-match date range shows empty-state messages in both table and category section
- Invalid date params (not YYYY-MM-DD) are silently ignored — no 500 error
- Partially invalid params (one valid, one invalid) apply only the valid bound
- Preset detection for this_month, last_month, last_3_months, all, custom
- Custom date inputs are pre-populated with current from_date / to_date
- Filter bar rendered with all four preset button labels
- Transaction limit=10 cap still applies when filtering
- Stats (total_spent, transaction_count, top_category) correctly reflect date filter
- Category breakdown reflects date filter (empty list for no-match range)
- No f-string interpolation of user-supplied values in queries.py SQL strings

Design note on isolation:
  database/db.py and database/queries.py call get_db() with no arguments, which
  falls back to the module-level DB_PATH constant.  To keep tests isolated each
  fixture patches database.db.DB_PATH to a per-test temporary file so every
  get_db() call — in routes, helpers, and query functions — hits the test DB.
"""

import re
import os
import pytest
from datetime import date, timedelta

import database.db as db_module
from app import app as flask_app
from database.db import init_db, get_db


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def app(tmp_path, monkeypatch):
    """
    Isolated Flask app whose every get_db() call routes to a fresh
    per-test SQLite file via monkeypatching of database.db.DB_PATH.
    """
    db_file = str(tmp_path / "test.db")

    # Patch the module-level constant so all internal get_db() calls
    # (in db.py helpers and queries.py functions) use the test DB.
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-06',
        'WTF_CSRF_ENABLED': False,
    })

    with flask_app.app_context():
        # Initialise schema in the patched test DB
        init_db(path=db_file)
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ------------------------------------------------------------------ #
# Private helpers                                                      #
# ------------------------------------------------------------------ #

def _register_and_login(client, name="Alice", email="alice@test.com", password="password123"):
    """Register a fresh user and log in via the test client."""
    client.post('/register', data={'name': name, 'email': email, 'password': password})
    client.post('/login', data={'email': email, 'password': password})


def _get_user_id(email):
    """Return the id for a user already registered in the (monkeypatched) DB."""
    conn = get_db()      # DB_PATH is already monkeypatched at this point
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    assert row is not None, f"User '{email}' not found in test DB"
    return row["id"]


def _insert_expense(user_id, amount, category, expense_date, description=""):
    """Insert a single expense row directly into the (monkeypatched) test DB."""
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, expense_date, description),
    )
    conn.commit()
    conn.close()


def _preset_dates():
    """Return the expected preset date ranges computed from today's date."""
    today = date.today()
    first_this_month = today.replace(day=1)
    last_month_end = first_this_month - timedelta(days=1)
    first_last_month = last_month_end.replace(day=1)
    last_3m_start = today - timedelta(days=89)
    return {
        "this_month":    (first_this_month.isoformat(), today.isoformat()),
        "last_month":    (first_last_month.isoformat(), last_month_end.isoformat()),
        "last_3_months": (last_3m_start.isoformat(), today.isoformat()),
    }


# ------------------------------------------------------------------ #
# Auth guard                                                           #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    def test_unauthenticated_get_profile_redirects_to_login(self, client):
        response = client.get('/profile')
        assert response.status_code == 302, "Expected redirect for unauthenticated /profile"
        assert '/login' in response.headers['Location'], (
            "Redirect target should be /login"
        )

    def test_unauthenticated_get_profile_with_date_params_redirects_to_login(self, client):
        response = client.get('/profile?from_date=2025-01-01&to_date=2025-12-31')
        assert response.status_code == 302, (
            "Date params should not bypass the auth guard"
        )
        assert '/login' in response.headers['Location'], (
            "Redirect target should be /login even when date params are supplied"
        )


# ------------------------------------------------------------------ #
# Default (all-time) view                                              #
# ------------------------------------------------------------------ #

class TestAllTimeDefault:
    def test_no_query_params_returns_200(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        assert response.status_code == 200, (
            "Authenticated /profile with no params should return 200"
        )

    def test_no_query_params_renders_profile_page(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')
        assert 'profile' in data.lower(), "Response should contain profile page content"

    def test_no_query_params_shows_user_name(self, client):
        _register_and_login(client, name="Alice")
        response = client.get('/profile')
        assert b'Alice' in response.data, "Profile page should display the logged-in user's name"

    def test_no_query_params_all_time_button_has_active_class(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')

        # Split the HTML on the 'All Time' label text; the active CSS class must
        # appear in the fragment that belongs to that button (immediately before the label).
        parts = data.split('All Time')
        assert len(parts) >= 2, "'All Time' button must exist in the filter bar"
        assert 'filter-preset-btn--active' in parts[0], (
            "'All Time' button must carry the active CSS class when no filter is active"
        )

    def test_no_query_params_other_presets_not_active(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')

        for label in ['This Month', 'Last Month', 'Last 3 Months']:
            parts = data.split(label)
            assert len(parts) >= 2, f"'{label}' button must exist in the filter bar"
            assert 'filter-preset-btn--active' not in parts[0], (
                f"'{label}' button must NOT be active when no filter params are given"
            )

    def test_no_query_params_custom_date_inputs_have_empty_values(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')

        assert 'name="from_date"' in data, "from_date input must be present"
        assert 'name="to_date"' in data, "to_date input must be present"
        # Both inputs should carry empty value attributes when no range is active
        assert 'value=""' in data, (
            "Date inputs should have empty value='' when no filter is active"
        )


# ------------------------------------------------------------------ #
# Date range filtering — happy path                                    #
# ------------------------------------------------------------------ #

class TestDateRangeFilter:
    def test_valid_date_range_returns_200(self, client):
        _register_and_login(client)
        response = client.get('/profile?from_date=2020-01-01&to_date=2020-12-31')
        assert response.status_code == 200, "Valid date range filter should return 200"

    def test_date_range_shows_in_range_expenses(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 100.00, "Freight", "2024-03-15", "In range expense")
        _insert_expense(uid, 200.00, "Customs", "2023-01-10", "Out of range expense")

        response = client.get('/profile?from_date=2024-01-01&to_date=2024-12-31')
        data = response.data.decode('utf-8')

        assert 'In range expense' in data, (
            "Expense within the date range should appear in the transaction table"
        )
        assert 'Out of range expense' not in data, (
            "Expense outside the date range must NOT appear in the transaction table"
        )

    def test_date_range_categories_scoped_to_range(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 400.00, "Insurance", "2024-05-10", "In range cat")
        _insert_expense(uid, 800.00, "Demurrage", "2023-01-01", "Out of range cat")

        response = client.get('/profile?from_date=2024-01-01&to_date=2024-12-31')
        data = response.data.decode('utf-8')

        assert 'Insurance' in data, (
            "In-range category should appear in the category breakdown"
        )
        assert 'Demurrage' not in data, (
            "Out-of-range category must NOT appear in the category breakdown"
        )

    def test_date_range_stats_exclude_out_of_range_expenses(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 1000.00, "Freight", "2024-06-01", "In range stat")
        _insert_expense(uid, 5000.00, "Customs", "2023-01-01", "Out of range stat")

        response = client.get('/profile?from_date=2024-01-01&to_date=2024-12-31')
        data = response.data.decode('utf-8')

        assert 'Out of range stat' not in data, (
            "Out-of-range expense description must not appear when date filter is active"
        )

    def test_only_from_date_filters_lower_bound(self, client):
        """from_date with no to_date should exclude expenses before that date."""
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 150.00, "Port", "2025-01-15", "After from date")
        _insert_expense(uid, 250.00, "Port", "2024-12-31", "Before from date")

        response = client.get('/profile?from_date=2025-01-01')
        data = response.data.decode('utf-8')

        assert 'After from date' in data, "Expense on or after from_date should appear"
        assert 'Before from date' not in data, "Expense before from_date must NOT appear"

    def test_only_to_date_filters_upper_bound(self, client):
        """to_date with no from_date should exclude expenses after that date."""
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 150.00, "Port", "2024-12-01", "Before to date")
        _insert_expense(uid, 250.00, "Port", "2025-06-01", "After to date")

        response = client.get('/profile?to_date=2025-01-01')
        data = response.data.decode('utf-8')

        assert 'Before to date' in data, "Expense on or before to_date should appear"
        assert 'After to date' not in data, "Expense after to_date must NOT appear"


# ------------------------------------------------------------------ #
# Zero-match date range — empty states                                 #
# ------------------------------------------------------------------ #

class TestZeroMatchRange:
    def test_no_match_range_returns_200(self, client):
        _register_and_login(client)
        response = client.get('/profile?from_date=2000-01-01&to_date=2000-12-31')
        assert response.status_code == 200, (
            "A date range with no matching expenses should still return 200"
        )

    def test_no_match_range_shows_empty_transaction_message(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 100.00, "Freight", "2024-06-01", "Existing expense")

        response = client.get('/profile?from_date=2000-01-01&to_date=2000-12-31')
        data = response.data.decode('utf-8')

        assert 'No transactions found' in data, (
            "Empty-state message should appear in transaction table for zero-match range"
        )

    def test_no_match_range_shows_empty_category_message(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 100.00, "Freight", "2024-06-01", "Existing expense")

        response = client.get('/profile?from_date=2000-01-01&to_date=2000-12-31')
        data = response.data.decode('utf-8')

        assert 'No spending data' in data, (
            "Empty-state message should appear in category section for zero-match range"
        )

    def test_no_match_range_transaction_count_is_zero(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 100.00, "Freight", "2024-06-01", "Existing expense")

        response = client.get('/profile?from_date=2000-01-01&to_date=2000-12-31')
        data = response.data.decode('utf-8')

        # The stat-value span for transaction count should render as 0
        assert re.search(r'<span[^>]*class="stat-value"[^>]*>\s*0\s*</span>', data), (
            "Transaction count stat should be 0 for a zero-match date range"
        )

    def test_no_match_range_with_fresh_user_shows_empty_states(self, client):
        """Even when the user has no expenses at all the page should load cleanly."""
        _register_and_login(client)
        response = client.get('/profile?from_date=2000-01-01&to_date=2000-12-31')
        assert response.status_code == 200, (
            "Zero-expense user with date filter should return 200"
        )
        data = response.data.decode('utf-8')
        assert 'No transactions found' in data
        assert 'No spending data' in data


# ------------------------------------------------------------------ #
# Invalid date params — silently ignored                               #
# ------------------------------------------------------------------ #

class TestInvalidDateParams:
    def test_invalid_from_date_does_not_cause_500(self, client):
        _register_and_login(client)
        response = client.get('/profile?from_date=notadate')
        assert response.status_code == 200, (
            "Invalid from_date must be silently ignored — must not raise a 500 error"
        )

    def test_invalid_to_date_does_not_cause_500(self, client):
        _register_and_login(client)
        response = client.get('/profile?to_date=badvalue')
        assert response.status_code == 200, (
            "Invalid to_date must be silently ignored — must not raise a 500 error"
        )

    def test_both_invalid_dates_return_200_with_all_time_data(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 100.00, "Freight", "2024-06-01", "Visible all time")

        response = client.get('/profile?from_date=notadate&to_date=alsobad')
        assert response.status_code == 200, (
            "Both invalid date params should not raise a 500 error"
        )
        data = response.data.decode('utf-8')
        assert 'Visible all time' in data, (
            "When both date params are invalid, all-time data (no filter) should be shown"
        )

    def test_invalid_from_date_valid_to_date_applies_upper_bound_only(self, client):
        """Invalid from_date is silently dropped; the valid to_date still applies."""
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 100.00, "Freight", "2024-01-01", "Old expense visible")
        _insert_expense(uid, 200.00, "Customs", "2026-06-01", "Future expense excluded")

        response = client.get('/profile?from_date=notadate&to_date=2025-01-01')
        assert response.status_code == 200, (
            "Partially invalid params must not raise a 500 error"
        )
        data = response.data.decode('utf-8')
        assert 'Old expense visible' in data, (
            "Expense before valid to_date should appear when from_date is invalid"
        )
        assert 'Future expense excluded' not in data, (
            "Expense after valid to_date should be excluded even when from_date is invalid"
        )

    def test_valid_from_date_invalid_to_date_applies_lower_bound_only(self, client):
        """Valid from_date is applied; invalid to_date is silently dropped."""
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 100.00, "Freight", "2024-01-01", "Before from excluded")
        _insert_expense(uid, 200.00, "Customs", "2025-06-01", "After from visible")

        response = client.get('/profile?from_date=2025-01-01&to_date=notadate')
        assert response.status_code == 200, (
            "Partially invalid params must not raise a 500 error"
        )
        data = response.data.decode('utf-8')
        assert 'After from visible' in data, (
            "Expense on or after from_date should appear when to_date is invalid"
        )
        assert 'Before from excluded' not in data, (
            "Expense before from_date should be excluded even when to_date is invalid"
        )

    def test_sql_injection_in_date_param_handled_safely(self, client):
        """An SQL injection string in the date param must not cause a 500 error."""
        _register_and_login(client)
        # URL-encoding of the injection string is handled by the test client automatically
        response = client.get("/profile?from_date=2024-01-01' OR '1'%3D'1")
        assert response.status_code in (200, 400), (
            "SQL injection attempt in date param must not cause a 500 error"
        )

    def test_invalid_date_not_echoed_in_html(self, client):
        """Invalid date values must not be rendered back into the HTML inputs."""
        _register_and_login(client)
        response = client.get('/profile?from_date=notadate&to_date=alsobad')
        data = response.data.decode('utf-8')
        assert 'notadate' not in data, (
            "Invalid from_date value must not appear in the rendered HTML"
        )
        assert 'alsobad' not in data, (
            "Invalid to_date value must not appear in the rendered HTML"
        )


# ------------------------------------------------------------------ #
# Preset detection                                                     #
# ------------------------------------------------------------------ #

class TestPresetDetection:
    def test_all_time_active_with_no_params(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')

        parts = data.split('All Time')
        assert len(parts) >= 2, "'All Time' button must exist"
        assert 'filter-preset-btn--active' in parts[0], (
            "'All Time' button must be active when no filter params are given"
        )

    def test_this_month_preset_active_for_current_month_range(self, client):
        _register_and_login(client)
        fd, td = _preset_dates()["this_month"]

        response = client.get(f'/profile?from_date={fd}&to_date={td}')
        data = response.data.decode('utf-8')

        parts = data.split('This Month')
        assert len(parts) >= 2, "'This Month' button must exist"
        assert 'filter-preset-btn--active' in parts[0], (
            "'This Month' button must be highlighted for the current-month date range"
        )

    def test_last_month_preset_active_for_last_month_range(self, client):
        _register_and_login(client)
        fd, td = _preset_dates()["last_month"]

        response = client.get(f'/profile?from_date={fd}&to_date={td}')
        data = response.data.decode('utf-8')

        parts = data.split('Last Month')
        assert len(parts) >= 2, "'Last Month' button must exist"
        assert 'filter-preset-btn--active' in parts[0], (
            "'Last Month' button must be highlighted for the last-calendar-month range"
        )

    def test_last_3_months_preset_active_for_90_day_window(self, client):
        _register_and_login(client)
        fd, td = _preset_dates()["last_3_months"]

        response = client.get(f'/profile?from_date={fd}&to_date={td}')
        data = response.data.decode('utf-8')

        parts = data.split('Last 3 Months')
        assert len(parts) >= 2, "'Last 3 Months' button must exist"
        assert 'filter-preset-btn--active' in parts[0], (
            "'Last 3 Months' button must be highlighted for the 90-day window"
        )

    def test_custom_range_activates_no_preset_button(self, client):
        """A range that matches no known preset must leave all preset buttons inactive."""
        _register_and_login(client)

        response = client.get('/profile?from_date=2022-03-15&to_date=2022-04-20')
        data = response.data.decode('utf-8')

        for label in ['All Time', 'This Month', 'Last Month', 'Last 3 Months']:
            parts = data.split(label)
            if len(parts) >= 2:
                assert 'filter-preset-btn--active' not in parts[0], (
                    f"'{label}' must NOT be marked active for a custom date range"
                )

    def test_this_month_not_active_when_no_filter(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')

        parts = data.split('This Month')
        assert len(parts) >= 2, "'This Month' button must exist"
        assert 'filter-preset-btn--active' not in parts[0], (
            "'This Month' must NOT be active when no filter params are given"
        )

    def test_last_month_not_active_when_no_filter(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')

        parts = data.split('Last Month')
        assert len(parts) >= 2, "'Last Month' button must exist"
        assert 'filter-preset-btn--active' not in parts[0], (
            "'Last Month' must NOT be active when no filter params are given"
        )

    def test_last_3_months_not_active_when_no_filter(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')

        parts = data.split('Last 3 Months')
        assert len(parts) >= 2, "'Last 3 Months' button must exist"
        assert 'filter-preset-btn--active' not in parts[0], (
            "'Last 3 Months' must NOT be active when no filter params are given"
        )

    def test_all_time_not_active_when_this_month_range_active(self, client):
        _register_and_login(client)
        fd, td = _preset_dates()["this_month"]

        response = client.get(f'/profile?from_date={fd}&to_date={td}')
        data = response.data.decode('utf-8')

        parts = data.split('All Time')
        assert len(parts) >= 2, "'All Time' button must exist"
        assert 'filter-preset-btn--active' not in parts[0], (
            "'All Time' must NOT be active when 'This Month' range is selected"
        )


# ------------------------------------------------------------------ #
# Custom date input pre-population                                     #
# ------------------------------------------------------------------ #

class TestCustomDateInputPrePopulation:
    def test_from_date_input_prepopulated_with_valid_range(self, client):
        _register_and_login(client)
        response = client.get('/profile?from_date=2024-03-01&to_date=2024-03-31')
        data = response.data.decode('utf-8')
        assert 'value="2024-03-01"' in data, (
            "from_date input should be pre-populated with the active from_date value"
        )

    def test_to_date_input_prepopulated_with_valid_range(self, client):
        _register_and_login(client)
        response = client.get('/profile?from_date=2024-03-01&to_date=2024-03-31')
        data = response.data.decode('utf-8')
        assert 'value="2024-03-31"' in data, (
            "to_date input should be pre-populated with the active to_date value"
        )

    def test_both_inputs_prepopulated_for_custom_range(self, client):
        _register_and_login(client)
        response = client.get('/profile?from_date=2023-06-01&to_date=2023-08-31')
        data = response.data.decode('utf-8')
        assert 'value="2023-06-01"' in data, "from_date input must carry the active from value"
        assert 'value="2023-08-31"' in data, "to_date input must carry the active to value"

    def test_date_inputs_empty_when_no_filter_active(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')
        assert 'value=""' in data, (
            "Date inputs should have empty value='' when no filter is active"
        )

    def test_invalid_date_values_not_echoed_in_inputs(self, client):
        """Invalid date strings must not be passed through to the template inputs."""
        _register_and_login(client)
        response = client.get('/profile?from_date=notadate&to_date=alsobad')
        data = response.data.decode('utf-8')
        assert 'notadate' not in data, (
            "Invalid from_date value must not appear in rendered input value"
        )
        assert 'alsobad' not in data, (
            "Invalid to_date value must not appear in rendered input value"
        )

    def test_preset_dates_prepopulated_when_preset_active(self, client):
        """When a preset is active the date inputs should still carry those dates."""
        _register_and_login(client)
        fd, td = _preset_dates()["this_month"]
        response = client.get(f'/profile?from_date={fd}&to_date={td}')
        data = response.data.decode('utf-8')
        assert f'value="{fd}"' in data, (
            "from_date input should be pre-populated even when a preset range is active"
        )
        assert f'value="{td}"' in data, (
            "to_date input should be pre-populated even when a preset range is active"
        )


# ------------------------------------------------------------------ #
# Filter bar HTML structure                                            #
# ------------------------------------------------------------------ #

class TestFilterBarStructure:
    def test_filter_bar_contains_all_four_preset_labels(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')
        for label in ['All Time', 'This Month', 'Last Month', 'Last 3 Months']:
            assert label in data, f"Filter bar must contain '{label}' button label"

    def test_custom_date_form_uses_method_get(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')
        assert 'method="get"' in data, (
            "Custom date form must use method='get' so the URL reflects filter state"
        )

    def test_filter_form_has_from_date_input(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')
        assert 'name="from_date"' in data, "Filter form must include a from_date input"

    def test_filter_form_has_to_date_input(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')
        assert 'name="to_date"' in data, "Filter form must include a to_date input"

    def test_date_inputs_are_html5_type_date(self, client):
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')
        assert 'type="date"' in data, (
            "Date inputs should use HTML5 type='date' — no JS date-picker libraries"
        )

    def test_preset_buttons_are_anchor_tags_linking_to_profile(self, client):
        """
        Spec requires preset buttons to be <a> tags so they work without JS.
        At least the 'All Time' button should be an anchor linking to /profile.
        """
        _register_and_login(client)
        response = client.get('/profile')
        data = response.data.decode('utf-8')
        assert re.search(
            r'<a\s[^>]*href=["\'][^"\']*profile[^"\']*["\'][^>]*>\s*All Time',
            data
        ), "The 'All Time' preset must be an <a> tag with href pointing to /profile"


# ------------------------------------------------------------------ #
# Transaction limit cap                                                #
# ------------------------------------------------------------------ #

class TestTransactionLimit:
    def test_at_most_10_transactions_shown_with_date_filter(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")

        for i in range(15):
            _insert_expense(uid, 10.00 + i, "Freight", "2024-06-01", f"Txn {i:02d}")

        response = client.get('/profile?from_date=2024-01-01&to_date=2024-12-31')
        data = response.data.decode('utf-8')

        count = len(re.findall(r'Txn \d{2}', data))
        assert count <= 10, (
            f"At most 10 transactions should appear with a date filter active, got {count}"
        )

    def test_at_most_10_transactions_shown_without_date_filter(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")

        for i in range(15):
            _insert_expense(uid, 10.00 + i, "Freight", "2024-06-01", f"Item {i:02d}")

        response = client.get('/profile')
        data = response.data.decode('utf-8')

        count = len(re.findall(r'Item \d{2}', data))
        assert count <= 10, (
            f"At most 10 transactions should appear without a date filter, got {count}"
        )


# ------------------------------------------------------------------ #
# Stats accuracy with filtered data                                    #
# ------------------------------------------------------------------ #

class TestStatsAccuracy:
    def test_total_spent_reflects_only_in_range_expenses(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 1000.00, "Freight", "2024-06-01", "In range")
        _insert_expense(uid, 5000.00, "Customs", "2023-01-01", "Out of range")

        response = client.get('/profile?from_date=2024-01-01&to_date=2024-12-31')
        data = response.data.decode('utf-8')

        # Formatted as ₹1,000.00 by the query function
        assert '1,000.00' in data, (
            "Total spent should include only in-range expenses (₹1,000.00)"
        )
        # ₹5,000.00 from the out-of-range expense must not appear in stats
        assert '5,000.00' not in data, (
            "Out-of-range expense amount must not appear in stats"
        )

    def test_top_category_comes_from_filtered_range(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 2000.00, "Insurance", "2024-05-01", "In range top cat")
        _insert_expense(uid, 9000.00, "Demurrage", "2023-01-01", "Out of range top cat")

        response = client.get('/profile?from_date=2024-01-01&to_date=2024-12-31')
        data = response.data.decode('utf-8')

        assert 'Insurance' in data, (
            "Top category in stats should be derived from within the filtered range"
        )

    def test_transaction_count_matches_filtered_expenses(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 100.00, "Freight", "2024-06-01", "In range A")
        _insert_expense(uid, 200.00, "Customs", "2024-07-15", "In range B")
        _insert_expense(uid, 300.00, "Port",    "2023-01-01", "Out of range")

        response = client.get('/profile?from_date=2024-01-01&to_date=2024-12-31')
        data = response.data.decode('utf-8')

        # Expect transaction count stat = 2
        assert re.search(r'<span[^>]*class="stat-value"[^>]*>\s*2\s*</span>', data), (
            "Transaction count stat should be 2 for two in-range expenses"
        )

    def test_all_time_stats_include_all_user_expenses(self, client):
        _register_and_login(client)
        uid = _get_user_id("alice@test.com")
        _insert_expense(uid, 100.00, "Freight", "2022-01-01", "Old expense")
        _insert_expense(uid, 200.00, "Customs", "2024-06-01", "Recent expense")

        response = client.get('/profile')
        data = response.data.decode('utf-8')

        # Both expenses exist; transaction count should be 2
        assert re.search(r'<span[^>]*class="stat-value"[^>]*>\s*2\s*</span>', data), (
            "All-time view should count all user expenses in the stats"
        )


# ------------------------------------------------------------------ #
# Parameterised queries — no f-string SQL interpolation                #
# ------------------------------------------------------------------ #

class TestParameterisedQueries:
    def test_queries_py_contains_no_fstring_sql_interpolation(self):
        """
        Static analysis: queries.py must not use f-string interpolation to
        embed user-supplied values inside SQL strings.  Only the ? placeholder
        pattern with a separate params tuple is allowed.
        """
        queries_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database", "queries.py",
        )
        with open(queries_path, "r", encoding="utf-8") as fh:
            source = fh.read()

        # Detect f-strings that contain SQL keywords alongside curly-brace
        # interpolation — these are the dangerous patterns.
        fstring_sql_pattern = re.findall(
            r'f["\'].*?(?:SELECT|INSERT|UPDATE|DELETE|WHERE|AND|OR).*?\{.*?\}.*?["\']',
            source,
            re.IGNORECASE | re.DOTALL,
        )
        assert len(fstring_sql_pattern) == 0, (
            "queries.py must not interpolate values into SQL strings via f-strings. "
            f"Suspicious patterns found: {fstring_sql_pattern}"
        )

    def test_db_py_contains_no_fstring_sql_interpolation(self):
        """
        Static analysis: database/db.py must also use only parameterised queries.
        """
        db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "database", "db.py",
        )
        with open(db_path, "r", encoding="utf-8") as fh:
            source = fh.read()

        fstring_sql_pattern = re.findall(
            r'f["\'].*?(?:SELECT|INSERT|UPDATE|DELETE|WHERE|AND|OR).*?\{.*?\}.*?["\']',
            source,
            re.IGNORECASE,
        )
        assert len(fstring_sql_pattern) == 0, (
            "db.py must not interpolate values into SQL strings via f-strings. "
            f"Suspicious patterns found: {fstring_sql_pattern}"
        )
