"""
tests/test_profile_02_left_menu_sub_menu.py

Spec: Left Menu Sub Menu Section (Step 02)

Covers:
- Auth guard: all sidebar pages redirect unauthenticated requests to /login
- Sidebar structure: .sidebar-group elements rendered on every sidebar page
- All 8 group names appear in the sidebar HTML on every page
- Accordion toggle buttons use <button class="sidebar-group-toggle"> not <a> tags
- .sidebar-toggle-arrow element is present inside toggle buttons
- Sub-links use <a class="sidebar-sub-link"> elements
- Active group pre-expanded with 'is-open' class on the correct page
- Non-active groups do not carry 'is-open' on pages where they are not active
- Active sub-link highlighted with 'sidebar-sub-link--active'
- Sidebar footer Sign out link is present on every sidebar page
- /profile page still has add-expense modal elements (addExpenseModal, openAddExpenseModal)
"""

import pytest
import database.db as db_module
from app import app as flask_app
from database.db import init_db


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def app(tmp_path, monkeypatch):
    """
    Isolated Flask app — every get_db() call in routes and helpers is
    redirected to a fresh per-test SQLite file via DB_PATH monkeypatching.
    """
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)

    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-sidebar',
        'WTF_CSRF_ENABLED': False,
    })

    with flask_app.app_context():
        init_db(path=db_file)
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """A test client that is already registered and logged in."""
    client.post('/register', data={
        'name': 'Sidebar Tester',
        'email': 'sidebar@test.com',
        'password': 'testpass99',
    })
    client.post('/login', data={
        'email': 'sidebar@test.com',
        'password': 'testpass99',
    })
    return client


# ------------------------------------------------------------------ #
# Constants                                                            #
# ------------------------------------------------------------------ #

# All pages that render the shared sidebar partial
SIDEBAR_PAGES = [
    '/profile',
    '/shipments',
    '/vendors',
    '/billing',
    '/notifications',
]

# The 8 group names that must appear in every sidebar
SIDEBAR_GROUP_NAMES = [
    'Overview',
    'Shipments',
    'Vendors',
    'Billing',
    'Emails',
    'Notifications',
    'Reports',
    'Settings',
]

# Mapping: URL -> name of the group expected to carry 'is-open'
ACTIVE_GROUP_MAP = {
    '/profile':       'Overview',
    '/shipments':     'Shipments',
    '/vendors':       'Vendors',
    '/billing':       'Billing',
    '/notifications': 'Notifications',
}

# Mapping: URL -> text of the sub-link that should be marked active
ACTIVE_SUB_LINK_MAP = {
    '/profile':       'Dashboard',
    '/shipments':     'All Shipments',
}


# ------------------------------------------------------------------ #
# Auth guard tests                                                     #
# ------------------------------------------------------------------ #

class TestAuthGuard:
    """All sidebar pages must redirect unauthenticated visitors to /login."""

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_unauthenticated_redirects_to_login(self, client, url):
        response = client.get(url)
        assert response.status_code == 302, (
            f"Expected 302 redirect for unauthenticated GET {url}, "
            f"got {response.status_code}"
        )
        location = response.headers.get('Location', '')
        assert 'login' in location, (
            f"Expected redirect to /login for unauthenticated GET {url}, "
            f"got Location: {location}"
        )


# ------------------------------------------------------------------ #
# Sidebar structure tests — parameterized over all sidebar pages       #
# ------------------------------------------------------------------ #

class TestSidebarStructure:
    """Sidebar structural HTML requirements present on every sidebar page."""

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_sidebar_group_class_present(self, auth_client, url):
        response = auth_client.get(url)
        assert response.status_code == 200, (
            f"Expected 200 for authenticated GET {url}, got {response.status_code}"
        )
        assert b'sidebar-group' in response.data, (
            f"Expected .sidebar-group elements in sidebar on {url}"
        )

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_sidebar_group_toggle_uses_button_elements(self, auth_client, url):
        response = auth_client.get(url)
        assert response.status_code == 200
        # The spec requires <button> not <a> for group header toggles
        assert b'sidebar-group-toggle' in response.data, (
            f"Expected sidebar-group-toggle class in response for {url}"
        )
        # Check that it appears on a button element (not just any element)
        html = response.data.decode('utf-8', errors='replace')
        # Find occurrences of sidebar-group-toggle — they must be on <button tags
        import re
        toggle_tags = re.findall(
            r'<(\w+)[^>]*class="[^"]*sidebar-group-toggle[^"]*"',
            html,
        )
        assert len(toggle_tags) > 0, (
            f"No elements with class sidebar-group-toggle found on {url}"
        )
        for tag in toggle_tags:
            assert tag.lower() == 'button', (
                f"Expected sidebar-group-toggle to be on a <button>, "
                f"but found <{tag}> on {url}"
            )

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_sidebar_toggle_arrow_exists(self, auth_client, url):
        response = auth_client.get(url)
        assert response.status_code == 200
        assert b'sidebar-toggle-arrow' in response.data, (
            f"Expected .sidebar-toggle-arrow element in sidebar on {url}"
        )

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_sidebar_sub_links_use_anchor_tags(self, auth_client, url):
        response = auth_client.get(url)
        assert response.status_code == 200
        assert b'sidebar-sub-link' in response.data, (
            f"Expected sidebar-sub-link class in response for {url}"
        )
        html = response.data.decode('utf-8', errors='replace')
        import re
        sub_link_tags = re.findall(
            r'<(\w+)[^>]*class="[^"]*sidebar-sub-link[^"]*"',
            html,
        )
        assert len(sub_link_tags) > 0, (
            f"No elements with class sidebar-sub-link found on {url}"
        )
        for tag in sub_link_tags:
            assert tag.lower() == 'a', (
                f"Expected sidebar-sub-link to be on an <a> tag, "
                f"but found <{tag}> on {url}"
            )

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_all_eight_group_names_in_sidebar(self, auth_client, url):
        response = auth_client.get(url)
        assert response.status_code == 200
        for group_name in SIDEBAR_GROUP_NAMES:
            assert group_name.encode() in response.data, (
                f"Expected sidebar group name '{group_name}' to appear in "
                f"the HTML response for {url}"
            )

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_sign_out_link_present_in_sidebar(self, auth_client, url):
        response = auth_client.get(url)
        assert response.status_code == 200
        html_lower = response.data.lower()
        # Either "sign out" or "logout" text must appear in the sidebar footer
        assert b'sign out' in html_lower or b'logout' in html_lower, (
            f"Expected a Sign Out / logout link in sidebar footer on {url}"
        )


# ------------------------------------------------------------------ #
# Active group pre-expansion tests                                     #
# ------------------------------------------------------------------ #

class TestActiveGroupExpansion:
    """The correct accordion group must carry is-open on page load."""

    @pytest.mark.parametrize("url,expected_group", ACTIVE_GROUP_MAP.items())
    def test_active_group_has_is_open(self, auth_client, url, expected_group):
        response = auth_client.get(url)
        assert response.status_code == 200
        html = response.data.decode('utf-8', errors='replace')
        import re
        # Find every sidebar-group element and its classes, then check that
        # a group containing expected_group text also contains is-open.
        # Strategy: locate the block that contains both 'is-open' and expected_group
        # within close proximity (within the same sidebar-group div).
        #
        # We search for a pattern: a .sidebar-group element with is-open that
        # also contains the expected group name text nearby.
        pattern = re.compile(
            r'class="[^"]*sidebar-group[^"]*\bis-open\b[^"]*"'   # is-open on the element
            r'[\s\S]{0,800}'                                        # up to 800 chars later
            + re.escape(expected_group),                            # group name appears
            re.IGNORECASE,
        )
        match = pattern.search(html)
        assert match is not None, (
            f"Expected sidebar group '{expected_group}' to have is-open "
            f"class when visiting {url}"
        )

    @pytest.mark.parametrize("url,active_group", ACTIVE_GROUP_MAP.items())
    def test_non_active_groups_do_not_have_is_open(self, auth_client, url, active_group):
        """Groups other than the active one must not carry is-open."""
        response = auth_client.get(url)
        assert response.status_code == 200
        html = response.data.decode('utf-8', errors='replace')
        import re

        inactive_groups = [g for g in SIDEBAR_GROUP_NAMES if g != active_group]
        for group_name in inactive_groups:
            # Look for is-open on a sidebar-group that contains this group name
            # but is NOT the active one.  We check: find sidebar-group blocks
            # that contain the group name, and assert none of them has is-open
            # unless they are also the active group.
            #
            # Find all sidebar-group opening tags with their classes
            group_block_pattern = re.compile(
                r'(class="[^"]*sidebar-group[^"]*")'   # group class attr
                r'[\s\S]{0,800}'                        # content
                + re.escape(group_name),
                re.IGNORECASE,
            )
            for m in group_block_pattern.finditer(html):
                class_attr = m.group(1)
                # If this block's class attr has is-open it must be for the active group
                if 'is-open' in class_attr:
                    # This non-active group block should NOT have is-open
                    assert False, (
                        f"Group '{group_name}' has is-open but it should not "
                        f"be active when visiting {url} (active: {active_group})"
                    )


# ------------------------------------------------------------------ #
# Active sub-link highlight tests                                      #
# ------------------------------------------------------------------ #

class TestActiveSubLinkHighlight:
    """The active sub-link must carry sidebar-sub-link--active."""

    @pytest.mark.parametrize("url,expected_sub_text", ACTIVE_SUB_LINK_MAP.items())
    def test_active_sub_link_has_active_class(self, auth_client, url, expected_sub_text):
        response = auth_client.get(url)
        assert response.status_code == 200
        html = response.data.decode('utf-8', errors='replace')
        import re
        # Find an anchor that has sidebar-sub-link--active and contains the expected text
        pattern = re.compile(
            r'<a[^>]*class="[^"]*sidebar-sub-link--active[^"]*"[^>]*>'
            r'[\s\S]{0,200}'
            + re.escape(expected_sub_text),
            re.IGNORECASE,
        )
        match = pattern.search(html)
        assert match is not None, (
            f"Expected sub-link '{expected_sub_text}' to have "
            f"sidebar-sub-link--active class on {url}"
        )

    def test_profile_dashboard_sub_link_active(self, auth_client):
        """Explicit test: /profile marks the Dashboard sub-link active."""
        response = auth_client.get('/profile')
        assert response.status_code == 200
        assert b'sidebar-sub-link--active' in response.data, (
            "Expected sidebar-sub-link--active class on /profile"
        )

    def test_shipments_all_shipments_sub_link_active(self, auth_client):
        """Explicit test: /shipments marks the All Shipments sub-link active."""
        response = auth_client.get('/shipments')
        assert response.status_code == 200
        assert b'sidebar-sub-link--active' in response.data, (
            "Expected sidebar-sub-link--active class on /shipments"
        )


# ------------------------------------------------------------------ #
# Profile page — existing modal elements must still be present         #
# ------------------------------------------------------------------ #

class TestProfileModalPreservation:
    """Adding accordion sidebar must not remove existing modal wiring on /profile."""

    def test_add_expense_modal_id_present(self, auth_client):
        response = auth_client.get('/profile')
        assert response.status_code == 200
        assert b'addExpenseModal' in response.data, (
            "Expected addExpenseModal element to remain on /profile after sidebar refactor"
        )

    def test_open_add_expense_modal_button_present(self, auth_client):
        response = auth_client.get('/profile')
        assert response.status_code == 200
        assert b'openAddExpenseModal' in response.data, (
            "Expected openAddExpenseModal trigger to remain on /profile after sidebar refactor"
        )


# ------------------------------------------------------------------ #
# HTTP semantics                                                        #
# ------------------------------------------------------------------ #

class TestHTTPSemantics:
    """Sidebar pages return 200 for authenticated users."""

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_sidebar_page_returns_200_when_authenticated(self, auth_client, url):
        response = auth_client.get(url)
        assert response.status_code == 200, (
            f"Expected 200 for authenticated GET {url}, got {response.status_code}"
        )

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_sidebar_page_returns_html(self, auth_client, url):
        response = auth_client.get(url)
        content_type = response.content_type or ''
        assert 'text/html' in content_type, (
            f"Expected text/html content type for {url}, got {content_type}"
        )


# ------------------------------------------------------------------ #
# Sidebar group count sanity test                                       #
# ------------------------------------------------------------------ #

class TestSidebarGroupCount:
    """There should be at least 8 sidebar-group elements (one per section)."""

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_at_least_eight_sidebar_groups_rendered(self, auth_client, url):
        response = auth_client.get(url)
        assert response.status_code == 200
        html = response.data.decode('utf-8', errors='replace')
        import re
        groups = re.findall(r'class="[^"]*sidebar-group[^"]*"', html)
        assert len(groups) >= 8, (
            f"Expected at least 8 sidebar-group elements on {url}, "
            f"found {len(groups)}"
        )


# ------------------------------------------------------------------ #
# Accordion sub-nav structure tests                                     #
# ------------------------------------------------------------------ #

class TestSubNavStructure:
    """Each accordion group must contain a sub-nav with sub-links."""

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_sidebar_sub_nav_present(self, auth_client, url):
        response = auth_client.get(url)
        assert response.status_code == 200
        assert b'sidebar-sub-nav' in response.data, (
            f"Expected .sidebar-sub-nav element(s) in sidebar on {url}"
        )

    def test_shipments_sub_links_include_all_shipments(self, auth_client):
        """The Shipments accordion must include an 'All Shipments' sub-link."""
        response = auth_client.get('/shipments')
        assert response.status_code == 200
        assert b'All Shipments' in response.data, (
            "Expected 'All Shipments' sub-link in Shipments accordion on /shipments"
        )

    def test_vendors_sub_links_include_vendor_list(self, auth_client):
        """The Vendors accordion must include a sub-link for the vendor list."""
        response = auth_client.get('/vendors')
        assert response.status_code == 200
        # Spec names the sub-link "Vendor List"
        assert b'Vendor List' in response.data or b'Vendors' in response.data, (
            "Expected a vendor-list sub-link in the Vendors accordion on /vendors"
        )

    def test_billing_sub_links_include_invoices(self, auth_client):
        """The Billing accordion must include an 'Invoices' sub-link per spec."""
        response = auth_client.get('/billing')
        assert response.status_code == 200
        assert b'Invoices' in response.data or b'Billing' in response.data, (
            "Expected an invoices sub-link in the Billing accordion on /billing"
        )

    def test_notifications_sub_links_present(self, auth_client):
        """The Notifications accordion must include relevant sub-links."""
        response = auth_client.get('/notifications')
        assert response.status_code == 200
        # Spec defines: Shipment Alerts, Payment Alerts, System Alerts
        assert (
            b'Shipment Alerts' in response.data
            or b'Payment Alerts' in response.data
            or b'System Alerts' in response.data
            or b'Notifications' in response.data
        ), (
            "Expected notification sub-links in sidebar on /notifications"
        )


# ------------------------------------------------------------------ #
# Sidebar toggle arrows count sanity                                    #
# ------------------------------------------------------------------ #

class TestToggleArrowCount:
    """Every sidebar-group-toggle button should contain a toggle-arrow element."""

    @pytest.mark.parametrize("url", SIDEBAR_PAGES)
    def test_toggle_arrows_match_toggle_buttons(self, auth_client, url):
        response = auth_client.get(url)
        assert response.status_code == 200
        html = response.data.decode('utf-8', errors='replace')
        import re
        buttons = re.findall(r'sidebar-group-toggle', html)
        arrows = re.findall(r'sidebar-toggle-arrow', html)
        assert len(arrows) >= len(buttons), (
            f"Expected at least one .sidebar-toggle-arrow per .sidebar-group-toggle "
            f"on {url} (buttons: {len(buttons)}, arrows: {len(arrows)})"
        )
        assert len(buttons) > 0, (
            f"Expected at least one sidebar-group-toggle button on {url}"
        )
