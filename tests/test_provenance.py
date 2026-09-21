"""Cluster 5a — does the repository know when its own facts went stale?

One test here is designed to start failing on a date. That is deliberate: see
`test_the_current_year_is_present_in_the_limits_table`.
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import jurisdiction as J, limits as L, provenance as P  # noqa: E402

TODAY = dt.date(2026, 8, 31)


# ── the forcing function ────────────────────────────────────────────────────


def test_the_current_year_is_present_in_the_limits_table():
    """THIS TEST IS SUPPOSED TO FAIL EVENTUALLY.

    Statutory limits change annually and are published the preceding autumn.
    If this fails, the table has not been updated for the current year: run
    the `reference-data-refresh` skill.

    It is a hard failure rather than a warning because a warning in a test
    suite is a warning nobody reads. The skills themselves degrade safely —
    they return UNKNOWN and refuse to answer — so this is a maintenance
    signal, not a functional break.
    """
    year = dt.date.today().year
    assert year in L.years_available(), (
        f"{year} is missing from lib/pf/limits.py. Every skill that reads "
        f"statutory limits will refuse to answer for the current year until "
        f"it is added. Run the reference-data-refresh skill; source is "
        f"irs.gov's annual cost-of-living adjustments."
    )


def test_a_missing_current_year_is_reported_as_a_blocker():
    """The same condition, checked against a future date so the assertion is
    stable regardless of when the suite runs."""
    future = dt.date(max(L.years_available()) + 1, 1, 2)
    blockers = P.blockers(future)
    assert len(blockers) == 1
    assert "is missing from" in blockers[0].detail


def test_a_requested_future_year_can_be_checked_before_january():
    future_year = max(L.years_available()) + 1
    blockers = P.blockers(TODAY, required_year=future_year)
    assert len(blockers) == 1
    assert blockers[0].key == str(future_year)


def test_no_blockers_while_the_current_year_is_present():
    present = dt.date(max(L.years_available()), 6, 1)
    assert P.blockers(present) == []


# ── registry ────────────────────────────────────────────────────────────────


def test_registry_covers_every_table_that_can_expire():
    modules = {t.module for t in P.registry()}
    assert "lib/pf/limits.py" in modules
    assert "lib/pf/jurisdiction.py" in modules


def test_table_names_are_unique_so_issues_can_be_attributed():
    names = [t.name for t in P.registry()]
    assert len(names) == len(set(names))


def test_every_table_names_an_authority_and_a_cadence():
    for t in P.registry():
        assert t.authority and t.holds
        assert t.cadence in P.MAX_AGE_DAYS


def test_registry_has_one_entry_per_year_and_per_state():
    tables = {t.name: t for t in P.registry()}
    assert ({e.key for e in tables["statutory contribution limits"].entries}
            == {str(y) for y in L.years_available()})
    assert ({e.key for e in tables["state auto insurance rules"].entries}
            == set(J.states_available()))


# ── staleness ───────────────────────────────────────────────────────────────


def test_unverified_entries_are_reported_as_such():
    """Both tables currently ship unverified. This test documents that
    honestly rather than pretending otherwise."""
    issues = P.check(TODAY)
    assert issues, "the report should not be silent while nothing is verified"
    assert all(i.severity == "unverified" for i in issues)
    total_entries = sum(len(t.entries) for t in P.registry())
    assert len(issues) == total_entries


def test_unverified_marker_is_recognised():
    on, unver = P._parse("unverified — check against irs.gov")
    assert on is None and unver


def test_a_real_date_parses():
    on, unver = P._parse("2026-01-15")
    assert on == dt.date(2026, 1, 15) and not unver


def test_missing_verification_is_treated_as_unverified_not_as_current():
    on, unver = P._parse(None)
    assert on is None and unver


def test_unparseable_date_does_not_pass_as_verified():
    on, unver = P._parse("last spring")
    assert on is None and unver


def test_annual_data_goes_stale_faster_than_legislative():
    assert P.MAX_AGE_DAYS[P.ANNUAL] < P.MAX_AGE_DAYS[P.LEGISLATIVE]


# ── the fields the refresh procedure depends on ─────────────────────────────


def test_every_limits_year_carries_a_source():
    for y in L.years_available():
        assert L.for_year(y).source


def test_every_known_state_carries_a_source_and_a_verification_field():
    for code in J.states_available():
        r = J.rules_for(code)
        assert r.source, code
        assert r.verified_on, code


# ── the verification checklist ──────────────────────────────────────────────


def test_every_entry_carries_its_asserted_values():
    """The checklist is generated from these. A hand-written checklist
    silently omits whatever was added to a table after it was written."""
    for tb in P.registry():
        for e in tb.entries:
            assert e.values, f"{tb.name}/{e.key} asserts no values"


def test_every_table_names_where_to_go_and_check():
    for tb in P.registry():
        assert tb.url or tb.authority
        if tb.url:
            assert tb.url.startswith("http")


def test_the_checklist_covers_a_meaningful_number_of_values():
    total = sum(len(e.values) for tb in P.registry() for e in tb.entries)
    assert total >= 45


def test_contribution_limits_expose_every_field_a_skill_reads():
    tb = next(t for t in P.registry() if t.name == "statutory contribution limits")
    for e in tb.entries:
        for field_name in ("elective_deferral", "total_additions",
                           "ira_contribution", "hsa_family"):
            assert field_name in e.values
