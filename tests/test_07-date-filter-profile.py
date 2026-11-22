"""Tests for the date-filter profile feature (spec `.claude/specs/07-date-filter-profile.md`).

The feature extends ``GET /profile`` (logged-in only) so it also shows the
current user's expenses, filterable by an optional ``start``/``end`` date
range passed as GET query params (ISO ``YYYY-MM-DD``). Covered here:

* happy path — all expenses shown when no filter is applied
* date-range narrowing (``date >= start AND date <= end``)
* start-only / end-only filters
* blank and whitespace-only params behave like no filter
* invalid dates are silently dropped (no 500) and can't inject SQL
* friendly empty state for ranges with no expenses
* filter values are echoed back into the form inputs
* logged-out access redirects to ``/login`` (auth guard)
* ownership — one user never sees another user's rows
"""

import datetime
import re

import pytest


# --------------------------------------------------------------------------- #
# Test-local helper — counts rendered expense rows by a template landmark.     #
# --------------------------------------------------------------------------- #

_EXPENSE_ROW_RE = re.compile(r'<li class="expense-row">')


def _count_rows(html_text):
    """Count rendered expense rows in the profile HTML."""
    return len(_EXPENSE_ROW_RE.findall(html_text))


# --------------------------------------------------------------------------- #
# No filter applied                                                            #
# --------------------------------------------------------------------------- #

class TestProfileUnfiltered:
    """GET /profile without query params shows all of the user's expenses."""

    def test_profile_renders_with_empty_filter_form(self, client):
        """Happy path (Def-o-Done #2): profile loads, filter inputs exist and are empty."""
        client.post(
            "/login",
            data={"email": "demo@spendly.com", "password": "demo123"},
        )
        response = client.get("/profile")
        assert response.status_code == 200, "Profile page should load for a logged-in user"

        assert b'id="start"' in response.data, "Filter form must have a 'start' date input"
        assert b'name="start"' in response.data
        assert b'id="end"' in response.data, "Filter form must have an 'end' date input"
        assert b'name="end"' in response.data
        assert b'value=""' in response.data, (
            "Filter inputs must be empty when no filter was submitted"
        )

    def test_no_filter_shows_all_demo_expenses(self, demo_client):
        """No filter param -> all 8 seeded expenses are visible."""
        response = demo_client.get("/profile")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        # The 8 seeded amounts (each rendered as "$X.XX") appear exactly once.
        for amount in ("12.50", "3.25", "85.00", "24.00", "15.00", "49.99", "8.75", "6.40"):
            assert f"${amount}" in html_text, f"Missing seeded expense amount ${amount}"
        assert "No expenses in this date range." not in html_text, (
            "Empty state must not appear when expenses exist"
        )

    def test_blank_params_show_all_expenses(self, demo_client):
        """Blank query params are treated as no filter (spec: absent/blank -> all)."""
        response = demo_client.get("/profile?start=&end=")
        assert response.status_code == 200
        for amount in ("12.50", "85.00", "49.99"):
            assert f"${amount}" in response.data.decode("utf-8")

    def test_whitespace_params_are_treated_as_blank(self, demo_client):
        """Whitespace-only start/end are stripped to blank -> no filter applied."""
        response = demo_client.get("/profile?start=+&end=%20%20")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        assert "$12.50" in html_text and "$49.99" in html_text


# --------------------------------------------------------------------------- #
# Date-range filtering                                                         #
# --------------------------------------------------------------------------- #

class TestProfileFiltering:
    """Date-range narrowing via start/end query params."""

    def test_range_spanning_today_narrows_and_echoes_values(self, demo_client):
        """Def-o-Done #3: start+end over today narrows the list and the values persist."""
        today = datetime.date.today().isoformat()
        response = demo_client.get(f"/profile?start={today}&end={today}")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")

        # Seeded spread is today..today-7, so exactly 1 row lands on today.
        assert _count_rows(html_text) == 1, (
            "Exactly one seeded expense is dated today; range should show only it"
        )
        assert f'value="{today}"' in html_text, (
            "Submitted start date must be echoed back into the filter input"
        )

    def test_start_only_filter(self, demo_client):
        """Only start given -> only expenses dated on/after start are shown."""
        today = datetime.date.today().isoformat()
        response = demo_client.get(f"/profile?start={today}")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        assert 1 <= _count_rows(html_text) <= 8
        assert f'value="{today}"' in html_text, "start must be echoed when only it is set"

    def test_end_only_filter_empty_for_past_end(self, demo_client):
        """Only an ancient end given -> all seeded (recent) expenses are excluded."""
        response = demo_client.get("/profile?end=2000-01-01")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        assert "No expenses in this date range." in html_text

    def test_future_start_only_filter_empty(self, demo_client):
        """Only a far-future start given -> all seeded expenses are excluded."""
        future = (datetime.date.today() + datetime.timedelta(days=3650)).isoformat()
        response = demo_client.get(f"/profile?start={future}")
        assert response.status_code == 200
        assert "No expenses in this date range." in response.data.decode("utf-8")

    def test_generous_window_keeps_all_rows(self, demo_client):
        """A window spanning the whole seeded spread keeps all 8 rows."""
        today = datetime.date.today().isoformat()
        response = demo_client.get(f"/profile?start=2000-01-01&end={today}")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        for amount in ("12.50", "3.25", "85.00", "24.00", "15.00", "49.99", "8.75", "6.40"):
            assert f"${amount}" in html_text

    def test_zero_padded_dates_are_echoed_preserved(self, demo_client):
        """Echoed values must preserve zero-padded ISO dates (e.g. month '01')."""
        response = demo_client.get("/profile?start=2000-01-01&end=2000-01-31")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        assert 'value="2000-01-01"' in html_text
        assert 'value="2000-01-31"' in html_text


# --------------------------------------------------------------------------- #
# Invalid dates                                                                #
# --------------------------------------------------------------------------- #

class TestProfileInvalidDates:
    """Invalid date params must be dropped — treated as no filter, never a 500."""

    @pytest.mark.parametrize(
        "query",
        [
            "?start=not-a-date",
            "?end=not-a-date",
            "?start=not-a-date&end=not-a-date",
            "?start=2025-13-01",   # month out of range
            "?end=2025-00-10",     # zero month
            "?start=2025-01-1",    # non-padded day
            "?end=2025/01/01",     # wrong separator
            "?start=1",            # partial value
        ],
    )
    def test_invalid_dates_are_dropped_and_all_expenses_show(self, demo_client, query):
        """Def-o-Done #5: invalid dates are ignored (no filter), all expenses render."""
        response = demo_client.get(f"/profile{query}")
        assert response.status_code == 200, "Invalid dates must never 500"
        html_text = response.data.decode("utf-8")
        for amount in ("12.50", "85.00", "49.99"):
            assert f"${amount}" in html_text, (
                f"All expenses should show when the filter value is invalid ({query!r})"
            )
        assert "No expenses in this date range." not in html_text

    def test_invalid_date_not_echoed_back(self, demo_client):
        """The dropped invalid value must not be echoed into the inputs."""
        response = demo_client.get("/profile?start=not-a-date")
        assert response.status_code == 200
        assert b'value="not-a-date"' not in response.data
        assert b'value=""' in response.data

    def test_sql_injection_start_value_is_neutralized(self, demo_client):
        """A malicious start value must not inject or break the query.

        The profile query must be parameterised (spec rule); a raw
        interpolated ``OR '1'='1`` inside ``start`` would either 500 or
        silently return garbage. The value is invalid, so per spec it is
        dropped (treated as no filter): the page renders 200 with all
        expenses, and the evil value is never echoed back.
        """
        evil = "2024-01-01' OR '1'='1"
        response = demo_client.get("/profile", query_string={"start": evil})
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        assert "No expenses in this date range." not in html_text, (
            "Invalid dates must be dropped, not treated as an empty filter window"
        )
        for amount in ("12.50", "85.00", "49.99"):
            assert f"${amount}" in html_text, (
                "All expenses should show when the invalid value is dropped"
            )
        assert b'value="2024-01-01' not in response.data, (
            "The neutralized value must not be echoed into the input"
        )

    def test_empty_end_with_invalid_start_still_renders(self, demo_client):
        """Parts of the range that are valid survive while invalid parts are dropped."""
        today = datetime.date.today().isoformat()
        response = demo_client.get(f"/profile?start=garbage&end={today}")
        assert response.status_code == 200
        # start is dropped, leaving the end-only filter ``date <= today``, which
        # every seeded expense (dated today-7 .. today) satisfies.
        assert _count_rows(response.data.decode("utf-8")) == 8, (
            "When start is dropped, the valid end alone must remain the filter; "
            "all 8 seeded expenses are dated on or before today"
        )
        assert "No expenses in this date range." not in response.data.decode("utf-8")


# --------------------------------------------------------------------------- #
# Empty state                                                                  #
# --------------------------------------------------------------------------- #

class TestProfileEmptyState:
    """A filter window containing no expenses shows the friendly empty state."""

    def test_no_expenses_in_range_shows_empty_state(self, demo_client):
        """Def-o-Done #4: past window -> friendly message, never a blank/erroring section."""
        response = demo_client.get("/profile?start=1990-01-01&end=1990-12-31")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        assert "No expenses in this date range." in html_text, (
            "Friendly empty state must be shown when the range has no expenses"
        )
        assert "$12.50" not in html_text
        assert "$85.00" not in html_text

    def test_empty_state_keeps_account_details_visible(self, demo_client):
        """The empty state must not replace the account-details section."""
        response = demo_client.get("/profile?start=1990-01-01&end=1990-12-31")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        assert "Account details" in html_text
        assert "Member since" in html_text


# --------------------------------------------------------------------------- #
# Auth guard                                                                   #
# --------------------------------------------------------------------------- #

class TestProfileAuthGuard:
    """Logging out and visiting /profile must redirect to /login (Def-o-Done #6)."""

    def test_logged_out_profile_redirects_to_login(self, client):
        response = client.get("/profile")
        assert response.status_code == 302, "Anonymous /profile must redirect, not render"
        assert "/login" in response.headers.get("Location", "")

    def test_logged_out_filtered_profile_redirects_to_login(self, client):
        """The guard must also protect the filtered variant."""
        response = client.get("/profile?start=2025-01-01&end=2025-12-31")
        assert response.status_code == 302
        assert "/login" in response.headers.get("Location", "")

    def test_logout_then_profile_redirects_to_login(self, client):
        """After logging out the profile page is no longer reachable."""
        client.post(
            "/login",
            data={"email": "demo@spendly.com", "password": "demo123"},
        )
        client.get("/logout", follow_redirects=False)
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.headers.get("Location", "")


# --------------------------------------------------------------------------- #
# Ownership                                                                    #
# --------------------------------------------------------------------------- #

class TestProfileOwnership:
    """One user must never see another user's expense rows (spec rule)."""

    def test_second_user_sees_no_demo_expenses(self, auth_client):
        """Def-o-Done #7: a fresh user owns no expenses, so the empty state shows."""
        response = auth_client.get("/profile")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        for amount in ("12.50", "3.25", "85.00", "24.00", "15.00", "49.99", "8.75", "6.40"):
            assert f"${amount}" not in html_text, (
                f"New user's profile must not leak demo expense amount ${amount}"
            )
        assert "No expenses in this date range." in html_text

    def test_second_user_demo_descriptions_absent(self, auth_client):
        """Even with no filter, no demo descriptions leak to a fresh user."""
        response = auth_client.get("/profile")
        html_text = response.data.decode("utf-8")
        assert "Lunch at the canteen" not in html_text
        assert "New headphones" not in html_text

    def test_second_user_filter_returns_empty_state(self, auth_client):
        """Filtering as a fresh user over any range still shows no demo rows."""
        response = auth_client.get("/profile?start=2000-01-01&end=2100-01-01")
        assert response.status_code == 200
        html_text = response.data.decode("utf-8")
        assert "No expenses in this date range." in html_text
        assert "$49.99" not in html_text

    def test_demo_seeded_row_renders_at_most_once(self, demo_client):
        """Sanity anchor: a seeded amount can never appear twice on one page."""
        today = datetime.date.today().isoformat()
        response = demo_client.get(f"/profile?start={today}&end={today}")
        html_text = response.data.decode("utf-8")
        assert html_text.count("$49.99") <= 1, "A single expense row appears at most once"