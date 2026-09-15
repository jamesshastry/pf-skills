"""Tests for the renters / homeowners review. Synthetic fixtures only."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import property as P  # noqa: E402

RIVERA = {
    "form": "renters",
    "monthly_rent": 2400,
    "coverage": {
        "personal_property": 10_000,
        "loss_of_use": 3_000,
        "personal_liability": 100_000,
        "medical_payments_to_others": 1_000,
        "deductible": 250,
    },
    "settlement_basis": "replacement_cost",
    "scheduled_items": [],
    "exclusions": ["trampoline"],
    "premium_annual": 180,
}

KW = dict(people=4, liquid_assets=85_000, attachable_assets=113_000, umbrella_in_force=None)


def by_key(a, key):
    return next(f for f in a.findings if f.key == key)


# ── derivations ─────────────────────────────────────────────────────────────


def test_contents_scales_with_people():
    assert P.contents_benchmark(4) == (72_000, 124_000)
    assert P.contents_benchmark(1) == (18_000, 31_000)


def test_ale_is_the_difference_not_the_gross():
    """The coverage pays the *increase* over rent already being paid. A skill
    that budgets gross temporary rent overstates the need by ~2x."""
    low, high = P.ale_monthly(2400, 4)
    gross_low = 2400 * P.TEMP_HOUSING_MULTIPLE[0]
    assert low < gross_low
    assert low == pytest.approx(2400 * 0.8 + 600)
    assert high == pytest.approx(2400 * 1.4 + 600)


def test_ale_uplift_scales_with_household_size():
    assert P.ale_monthly(2400, 1)[0] < P.ale_monthly(2400, 4)[0]


def test_zero_rent_produces_no_loss_of_use_finding():
    a = P.assess(dict(RIVERA, monthly_rent=None), **KW)
    assert not any(f.key == "loss_of_use" for f in a.findings)


# ── the fixture ─────────────────────────────────────────────────────────────


def test_liability_below_attachment_is_a_blocker():
    a = P.assess(RIVERA, **KW)
    f = by_key(a, "personal_liability")
    assert f.severity == "blocker"
    assert "$300,000" in f.detail
    assert len(a.blockers) == 1


def test_personal_property_gap_reports_the_shortfall_as_a_share():
    a = P.assess(RIVERA, **KW)
    f = by_key(a, "personal_property")
    assert f.severity == "gap"
    assert "14%" in f.detail  # 10,000 / 72,000
    assert "weakest input" in f.detail


def test_loss_of_use_reports_months_funded_not_just_dollars():
    a = P.assess(RIVERA, **KW)
    f = by_key(a, "loss_of_use")
    assert f.severity == "gap"
    # $3,000 against $2,520–$3,960/mo ALE ≈ 0.8–1.2 months
    assert "0.8–1.2 months" in f.detail


def test_replacement_cost_basis_is_ok():
    a = P.assess(RIVERA, **KW)
    assert by_key(a, "settlement_basis").severity == "ok"


def test_acv_basis_is_a_blocker():
    a = P.assess(dict(RIVERA, settlement_basis="actual_cash_value"), **KW)
    assert by_key(a, "settlement_basis").severity == "blocker"
    assert len(a.blockers) == 2


def test_missing_basis_is_a_gap_not_an_assumption():
    p = dict(RIVERA)
    del p["settlement_basis"]
    a = P.assess(p, **KW)
    assert by_key(a, "settlement_basis").severity == "gap"


def test_unscheduled_items_warns_about_sublimits_inside_the_limit():
    a = P.assess(RIVERA, **KW)
    f = by_key(a, "scheduled_items")
    assert "inside" in f.detail and "$1,500" in f.detail


def test_scheduling_something_silences_the_sublimit_note():
    a = P.assess(dict(RIVERA, scheduled_items=[{"item": "ring", "value": 8000}]), **KW)
    assert not any(f.key == "scheduled_items" for f in a.findings)


def test_each_exclusion_is_surfaced_against_the_umbrella():
    a = P.assess(dict(RIVERA, exclusions=["canine", "pool", "trampoline"]), **KW)
    excs = [f for f in a.findings if f.key.startswith("exclusion:")]
    assert len(excs) == 3
    assert all("umbrella" in f.detail for f in excs)


# ── deductible ──────────────────────────────────────────────────────────────


def test_small_deductible_suggests_raising_it():
    a = P.assess(RIVERA, **KW)
    f = by_key(a, "deductible")
    assert f.severity == "ok"
    assert "raising it" in f.detail


def test_deductible_large_against_liquid_is_a_gap():
    kw = dict(KW, liquid_assets=5_000)
    a = P.assess(dict(RIVERA, coverage=dict(RIVERA["coverage"], deductible=2_500)), **kw)
    assert by_key(a, "deductible").severity == "gap"


# ── the fixed version ───────────────────────────────────────────────────────


def test_a_corrected_policy_clears_every_blocker_and_gap():
    fixed = {
        "form": "renters",
        "monthly_rent": 2400,
        "coverage": {
            "personal_property": 90_000,
            "loss_of_use": 25_000,
            "personal_liability": 500_000,
            "medical_payments_to_others": 5_000,
            "deductible": 1_000,
        },
        "settlement_basis": "replacement_cost",
        "scheduled_items": [{"item": "ring", "value": 8_000}],
        "exclusions": [],
    }
    a = P.assess(fixed, **KW)
    assert a.blockers == []
    assert [f for f in a.findings if f.severity == "gap"] == []


# ── homeowners ──────────────────────────────────────────────────────────────


def test_renters_has_no_schema_gaps():
    assert P.assess(RIVERA, **KW).schema_gaps == []


def test_homeowners_names_what_it_cannot_review():
    a = P.assess(dict(RIVERA, form="homeowners"), **KW)
    assert a.schema_gaps
    assert any("coverage_a" in g for g in a.schema_gaps)
    assert any("flood" in g for g in a.schema_gaps)
    # The shared sections still run.
    assert by_key(a, "personal_liability").severity == "blocker"


def test_condo_also_flags_the_gaps():
    assert P.assess(dict(RIVERA, form="condo"), **KW).schema_gaps


# ── sequencing ──────────────────────────────────────────────────────────────


def test_blockers_produce_a_sequencing_warning():
    a = P.assess(RIVERA, **KW)
    assert any("before quoting an umbrella" in s for s in P.sequencing(a, None))


def test_existing_umbrella_triggers_an_attachment_recheck():
    a = P.assess(RIVERA, **KW)
    lines = P.sequencing(a, 2_000_000)
    assert any("already in force" in s for s in lines)
