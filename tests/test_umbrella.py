"""Tests for umbrella sizing, the attachment gate, and the pass-throughs."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import auto, property as P, umbrella as U  # noqa: E402

FAILING_AUTO = {
    "bodily_injury": {"per_person": 100_000, "per_accident": 300_000},
    "property_damage": {"per_accident": 50_000},
    "um_uim_bodily_injury": {"per_person": 30_000, "per_accident": 60_000},
}
PASSING_AUTO = {
    "bodily_injury": {"per_person": 300_000, "per_accident": 500_000},
    "property_damage": {"per_accident": 100_000},
    "um_uim_bodily_injury": {"per_person": 300_000, "per_accident": 500_000},
}
FAILING_PROP = {"personal_liability": 100_000}
PASSING_PROP = {"personal_liability": 500_000}

BASE = dict(
    auto_coverage=PASSING_AUTO,
    property_coverage=PASSING_PROP,
    property_exclusions=None,
    dependents=[],
    balance_sheet=[],
    in_force=None,
)


# ── sizing ──────────────────────────────────────────────────────────────────


def test_size_floors_at_one_million():
    assert U.size(20_000, 40_000) == 1_000_000


def test_size_rounds_up_not_to_nearest():
    """$1.01M of exposure needs $2M; you cannot buy $1.1M."""
    assert U.size(1_010_000, 0) == 2_000_000


def test_size_counts_future_earnings_not_just_assets():
    assets_only = U.size(900_000, 0)
    with_income = U.size(900_000, 394_000)
    assert assets_only == 1_000_000
    assert with_income == 2_000_000


def test_size_excludes_retirement_by_taking_attachable_not_net_worth():
    """Caller passes attachable; this documents the consequence."""
    net_worth_ish = U.size(1_937_000, 394_400)
    attachable = U.size(1_022_000, 394_400)
    assert net_worth_ish == 3_000_000
    assert attachable == 2_000_000


# ── cost ────────────────────────────────────────────────────────────────────


def test_cost_of_first_million():
    assert U.cost(1_000_000) == U.FIRST_MILLION_COST


def test_additional_millions_are_cheaper_per_dollar():
    lo1, hi1 = U.cost(1_000_000)
    lo3, hi3 = U.cost(3_000_000)
    assert lo3 / 3 < lo1 and hi3 / 3 < hi1


def test_two_million_cost_band():
    assert U.cost(2_000_000) == (225, 450)


# ── attachment gate ─────────────────────────────────────────────────────────


def test_gate_uses_the_same_constants_as_the_underlying_skills():
    """A duplicated threshold is a threshold that drifts. These must be
    the identical objects the other two modules test against."""
    gate = {(g.policy, g.coverage): g.required
            for g in U.check_gate(PASSING_AUTO, PASSING_PROP)}
    assert gate[("auto", "bodily injury per person")] == auto.UMBRELLA_ATTACHMENT["bi_per_person"]
    assert gate[("auto", "property damage")] == auto.UMBRELLA_ATTACHMENT["pd"]
    assert gate[("property", "personal liability")] == P.UMBRELLA_ATTACHMENT_LIABILITY


def test_gate_fails_on_the_rivera_shape():
    a = U.assess(attachable_assets=113_000, household_income=180_000,
                 **{**BASE, "auto_coverage": FAILING_AUTO,
                    "property_coverage": FAILING_PROP})
    assert not a.can_bind
    assert len(a.failures) == 4


def test_gate_passes_when_underlying_qualifies():
    a = U.assess(attachable_assets=113_000, household_income=180_000, **BASE)
    assert a.can_bind
    assert a.failures == []


def test_partial_failure_names_only_the_failing_items():
    a = U.assess(attachable_assets=113_000, household_income=180_000,
                 **{**BASE, "property_coverage": FAILING_PROP})
    assert [f.coverage for f in a.failures] == ["personal liability"]


# ── in force ────────────────────────────────────────────────────────────────


def test_shortfall_when_underinsured():
    a = U.assess(attachable_assets=1_022_000, household_income=394_400,
                 **{**BASE, "in_force": 1_000_000})
    assert a.recommended == 2_000_000
    assert a.shortfall == 1_000_000


def test_no_shortfall_when_adequately_covered():
    a = U.assess(attachable_assets=1_022_000, household_income=394_400,
                 **{**BASE, "in_force": 3_000_000})
    assert a.shortfall == 0


# ── the gap people assume is closed ─────────────────────────────────────────


def test_um_uim_is_always_flagged_as_not_extended():
    a = U.assess(attachable_assets=113_000, household_income=180_000, **BASE)
    note = next(n for n in a.notes if "UM/UIM" in n)
    assert "does not extend" in note
    assert "separate election" in note


def test_um_uim_note_quotes_the_actual_underlying_limit():
    a = U.assess(attachable_assets=113_000, household_income=180_000,
                 **{**BASE, "auto_coverage": FAILING_AUTO})
    assert "$30,000" in next(n for n in a.notes if "UM/UIM" in n)


def test_sir_is_always_mentioned():
    a = U.assess(attachable_assets=113_000, household_income=180_000, **BASE)
    assert any("self-insured retention" in n for n in a.notes)


def test_very_large_limits_warn_about_nonlinear_pricing():
    a = U.assess(attachable_assets=8_000_000, household_income=500_000, **BASE)
    assert a.recommended > U.LINEAR_PRICING_CEILING
    assert any("re-underwrite" in n for n in a.notes)


def test_ordinary_limits_do_not_warn():
    a = U.assess(attachable_assets=113_000, household_income=180_000, **BASE)
    assert not any("re-underwrite" in n for n in a.notes)


# ── pass-throughs and riders ────────────────────────────────────────────────


def test_underlying_exclusions_pass_through():
    a = U.assess(attachable_assets=113_000, household_income=180_000,
                 **{**BASE, "property_exclusions": ["canine", "trampoline"]})
    assert a.exclusions_passed_through == ["canine", "trampoline"]


def test_driving_age_dependents_must_be_disclosed():
    a = U.assess(attachable_assets=113_000, household_income=180_000,
                 **{**BASE, "dependents": [{"age": 16}, {"age": 20}, {"age": 8}]})
    r = next(r for r in a.riders if "driving age" in r)
    assert "16, 20" in r


def test_young_children_produce_no_driver_rider():
    a = U.assess(attachable_assets=113_000, household_income=180_000,
                 **{**BASE, "dependents": [{"age": 8}, {"age": 5}]})
    assert not any("driving age" in r for r in a.riders)


def test_rental_property_on_the_balance_sheet_needs_scheduling():
    a = U.assess(attachable_assets=113_000, household_income=180_000,
                 **{**BASE, "balance_sheet": [
                     {"name": "rental_duplex", "value": 400_000, "tier": "illiquid"}]})
    assert any("Landlord liability" in r for r in a.riders)


def test_business_interest_is_flagged_as_out_of_scope():
    a = U.assess(attachable_assets=113_000, household_income=180_000,
                 **{**BASE, "balance_sheet": [
                     {"name": "business_llc", "value": 200_000, "tier": "illiquid"}]})
    assert any("commercial liability" in r for r in a.riders)


def test_board_service_and_rideshare_always_raised():
    a = U.assess(attachable_assets=113_000, household_income=180_000, **BASE)
    assert any("D&O" in r for r in a.riders)
    assert any("Rideshare" in r for r in a.riders)


# ── where to buy ────────────────────────────────────────────────────────────


def test_failing_gate_says_do_not_call_yet():
    assert "Do not call for a quote yet" in U.where_to_buy(True)[0]


def test_passing_gate_leads_with_the_bundling_option():
    assert "existing auto carrier" in U.where_to_buy(False)[0]


def test_life_adviser_is_ruled_out_either_way():
    for fails in (True, False):
        assert any("life or disability adviser" in s for s in U.where_to_buy(fails))
