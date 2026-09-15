"""Cluster 14 — portfolio policy. Synthetic only; no fixture, no market data."""

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import portfolio as P  # noqa: E402

TODAY = dt.date(2026, 8, 30)

TARGET = {"us_equity": 0.50, "intl_equity": 0.20, "bond": 0.25, "cash": 0.05}

ROWS = [
    {"name": "checking", "value": 40_000, "tier": "liquid",
     "account_type": "taxable", "asset_class": "cash"},
    {"name": "brokerage", "value": 45_000, "tier": "liquid",
     "account_type": "taxable", "asset_class": "cash"},
    {"name": "401k", "value": 310_000, "tier": "age_restricted",
     "account_type": "tax_deferred",
     "holdings": [{"asset_class": "us_equity", "value": 200_000},
                  {"asset_class": "intl_equity", "value": 50_000},
                  {"asset_class": "bond", "value": 60_000}]},
    {"name": "529", "value": 28_000, "tier": "illiquid",
     "account_type": "education"},
]


# ── inventory ───────────────────────────────────────────────────────────────


def test_a_row_with_holdings_expands_into_one_entry_per_class():
    inv = P.inventory(ROWS)
    assert inv.by_class() == {"cash": 85_000, "us_equity": 200_000,
                              "intl_equity": 50_000, "bond": 60_000}
    assert inv.total == 395_000


def test_earmarked_accounts_are_excluded_from_the_denominator():
    """A 529 is committed to a dated obligation. Counting it as household
    equity overstates the risk the household can actually carry."""
    inv = P.inventory(ROWS)
    assert inv.earmarked == [("529", 28_000)]
    assert 28_000 not in [h.value for h in inv.holdings]


def test_pending_rows_are_excluded_like_every_other_tier_total():
    rows = ROWS + [{"name": "unsettled", "value": 50_000, "pending": True,
                    "account_type": "taxable", "asset_class": "us_equity"}]
    assert P.inventory(rows).total == 395_000


def test_unclassified_holdings_are_excluded_from_the_denominator_not_bucketed():
    """Unknown is not 'other'. Absorbing it would make the table tidy and
    wrong in a direction no reader can see."""
    rows = ROWS + [{"name": "mystery", "value": 100_000, "account_type": "taxable"}]
    inv = P.inventory(rows)
    assert inv.total == 395_000
    assert inv.unclassified == [("mystery", 100_000)]
    assert "other" not in inv.by_class()


def test_sub_holdings_that_do_not_sum_to_the_row_are_reported():
    rows = [{"name": "401k", "value": 300_000, "account_type": "tax_deferred",
             "holdings": [{"asset_class": "bond", "value": 60_000}]}]
    assert P.inventory(rows).mismatched == [("401k", 300_000, 60_000)]


def test_a_holding_without_an_account_type_is_flagged_but_still_allocated():
    rows = [{"name": "somewhere", "value": 10_000, "asset_class": "bond"}]
    inv = P.inventory(rows)
    assert inv.total == 10_000
    assert inv.untyped == [("somewhere", 10_000)]


# ── bands ───────────────────────────────────────────────────────────────────


def test_the_tighter_of_the_two_bands_applies():
    assert P.band_for(0.50) == P.ABSOLUTE_BAND          # relative would be 12.5pp
    assert P.band_for(0.05) == pytest.approx(0.0125)    # absolute could never fire
    assert P.band_for(0.20) == P.ABSOLUTE_BAND


def test_a_small_sleeve_is_unmanageable_under_the_absolute_band_alone():
    """The reason RELATIVE_BAND exists: a 5% class going to zero is a 5pp
    move, which never exceeds a 5pp absolute band."""
    s = P.Sleeve("reit", target=0.05, value=0.0, share=0.0)
    assert abs(s.drift) == 0.05
    assert not abs(s.drift) > P.ABSOLUTE_BAND
    assert s.breached
    assert s.which_band == "relative"


def test_band_boundary_is_exclusive():
    at = P.Sleeve("us_equity", target=0.50, value=55.0, share=0.55)
    over = P.Sleeve("us_equity", target=0.50, value=55.1, share=0.551)
    assert not at.breached
    assert over.breached


# ── allocation ──────────────────────────────────────────────────────────────


def test_both_branches_are_present_in_the_reference_mix():
    """One class in band, three outside — the fixture shape."""
    a = P.review_allocation(ROWS, TARGET)
    by = {s.asset_class: s for s in a.sleeves}
    assert not by["us_equity"].breached
    assert {s.asset_class for s in a.breached} == {"intl_equity", "bond", "cash"}


def test_drift_is_signed_so_over_and_underweight_are_distinguishable():
    a = P.review_allocation(ROWS, TARGET)
    by = {s.asset_class: s for s in a.sleeves}
    assert by["cash"].drift > 0
    assert by["bond"].drift < 0
    assert by["cash"].share == pytest.approx(85_000 / 395_000)


def test_a_target_that_does_not_sum_to_one_is_reported_and_not_renormalised():
    a = P.review_allocation(ROWS, {"us_equity": 0.60, "bond": 0.20})
    assert a.target_sum == pytest.approx(0.80)
    assert any("not 100%" in f for f in a.findings)
    by = {s.asset_class: s for s in a.sleeves}
    assert by["us_equity"].target == 0.60  # untouched


def test_a_class_in_the_target_but_absent_from_holdings_still_appears():
    a = P.review_allocation(ROWS, {**TARGET, "reit": 0.0})
    assert "reit" in {s.asset_class for s in a.sleeves}


def test_an_in_band_portfolio_says_so_rather_than_staying_silent():
    rows = [{"name": "b", "value": 50_000, "account_type": "taxable",
             "asset_class": "us_equity"},
            {"name": "c", "value": 50_000, "account_type": "taxable",
             "asset_class": "bond"}]
    a = P.review_allocation(rows, {"us_equity": 0.50, "bond": 0.50})
    assert not a.breached
    assert any("inside its band" in f for f in a.findings)


# ── glide path ──────────────────────────────────────────────────────────────


def test_horizon_is_computed_from_the_planned_age_not_assumed():
    assert P.years_to_retirement(60, 41) == 19
    assert P.years_to_retirement(None, 41) is None
    assert P.years_to_retirement(60, None) is None
    assert P.years_to_retirement(60, 65) == 0  # never negative


def test_an_unknown_horizon_refuses_rather_than_defaulting():
    g = P.glide_path(years=None, actual_equity=0.60)
    assert not g.known
    assert g.reference is None
    assert any("cannot be determined" in f for f in g.findings)


def test_the_reference_is_a_band_and_the_equity_share_is_placed_in_it():
    g = P.glide_path(years=19, actual_equity=0.633)
    assert g.reference == pytest.approx(0.78)
    assert (g.low, g.high) == (pytest.approx(0.68), pytest.approx(0.88))
    assert g.within is False  # below the band
    assert any("below the band" in f for f in g.findings)


def test_the_glide_path_is_clamped_at_both_ends():
    assert P.glide_path(years=60, actual_equity=0.5).reference == P.MAX_EQUITY_SHARE
    assert P.glide_path(years=0, actual_equity=0.5).reference == P.GLIDE_BASE_EQUITY


def test_sequence_risk_is_raised_only_near_the_target_date():
    near = P.glide_path(years=P.NEAR_RETIREMENT_YEARS, actual_equity=0.60)
    far = P.glide_path(years=P.NEAR_RETIREMENT_YEARS + 1, actual_equity=0.60)
    assert any("sequence-of-returns" in f.lower() for f in near.findings)
    assert not any("sequence-of-returns" in f.lower() for f in far.findings)


# ── asset location ──────────────────────────────────────────────────────────


def test_bonds_in_taxable_against_equity_in_tax_deferred_is_the_swap_finding():
    rows = [{"name": "brokerage", "value": 100_000, "account_type": "taxable",
             "asset_class": "bond"},
            {"name": "401k", "value": 150_000, "account_type": "tax_deferred",
             "asset_class": "us_equity"}]
    loc = P.review_location(P.inventory(rows))
    assert any("straight swap" in f for f in loc.findings)
    assert any("$100,000" in f for f in loc.findings)


def test_correct_placement_is_confirmed_rather_than_left_unsaid():
    loc = P.review_location(P.inventory(ROWS))
    assert any("correct placement" in f.lower() for f in loc.findings)


def test_absent_roth_and_hsa_is_named_as_a_location_gap():
    loc = P.review_location(P.inventory(ROWS))
    assert any("No Roth or HSA" in f for f in loc.findings)


def test_a_roth_holding_bonds_is_the_wrong_way_round():
    rows = [{"name": "roth", "value": 50_000, "account_type": "roth",
             "asset_class": "bond"},
            {"name": "brokerage", "value": 50_000, "account_type": "taxable",
             "asset_class": "us_equity"}]
    loc = P.review_location(P.inventory(rows))
    assert any("least likely to grow" in f for f in loc.findings)


def test_missing_account_types_are_named_as_the_weakest_input():
    rows = [{"name": "somewhere", "value": 10_000, "asset_class": "bond"}]
    loc = P.review_location(P.inventory(rows))
    assert any("weakest input" in f for f in loc.findings)


# ── rebalancing ─────────────────────────────────────────────────────────────


def plan(**kw):
    a = P.review_allocation(kw.pop("rows", ROWS), kw.pop("target", TARGET))
    kw.setdefault("policy", P.POLICY_BANDS)
    kw.setdefault("as_of", TODAY)
    return P.rebalance_plan(a, **kw)


def test_trades_are_signed_and_sum_to_zero():
    p = plan()
    assert p.buys == pytest.approx(p.sells)
    assert sum(t.amount for t in p.trades) == pytest.approx(0.0, abs=1e-6)


def test_cash_sales_realise_nothing_wherever_they_are_held():
    """Cash basis is its value. Selling it is free even in a taxable account."""
    p = plan()
    cash = next(t for t in p.trades if t.asset_class == "cash")
    assert cash.amount < 0
    assert cash.free_to_sell == pytest.approx(85_000)


def test_a_correction_funded_by_cash_needs_no_taxable_sale():
    p = plan()
    assert p.triggered
    assert p.taxable_sale_needed == 0
    assert any("without realising a taxable gain" in f for f in p.findings)


def test_a_correction_that_must_come_from_a_taxable_sale_is_sized():
    rows = [{"name": "brokerage", "value": 200_000, "account_type": "taxable",
             "asset_class": "us_equity"},
            {"name": "ira", "value": 50_000, "account_type": "roth",
             "asset_class": "us_equity"}]
    p = plan(rows=rows, target={"us_equity": 0.50, "bond": 0.50})
    assert p.taxable_sale_needed > 0
    assert any("taxable sale" in f for f in p.findings)


def test_contributions_reduce_the_taxable_sale_before_anything_else_does():
    rows = [{"name": "brokerage", "value": 200_000, "account_type": "taxable",
             "asset_class": "us_equity"}]
    target = {"us_equity": 0.90, "bond": 0.10}
    without = plan(rows=rows, target=target)
    with_ = plan(rows=rows, target=target, annual_contributions=30_000)
    assert with_.taxable_sale_needed < without.taxable_sale_needed
    assert any("without selling anything" in f for f in with_.findings)


def test_sheltered_sales_count_as_free_capacity():
    rows = [{"name": "401k", "value": 100_000, "account_type": "tax_deferred",
             "asset_class": "us_equity"},
            {"name": "brokerage", "value": 100_000, "account_type": "taxable",
             "asset_class": "bond"}]
    p = plan(rows=rows, target={"us_equity": 0.30, "bond": 0.70})
    assert p.free_capacity > 0
    assert p.taxable_sale_needed == 0


def test_an_in_band_portfolio_produces_no_instruction():
    rows = [{"name": "b", "value": 50_000, "account_type": "taxable",
             "asset_class": "us_equity"},
            {"name": "c", "value": 50_000, "account_type": "tax_deferred",
             "asset_class": "bond"}]
    p = plan(rows=rows, target={"us_equity": 0.50, "bond": 0.50})
    assert not p.triggered
    assert any("do nothing" in f for f in p.findings)


def test_no_recorded_policy_is_itself_the_finding():
    p = plan(policy=None)
    assert any("No rebalancing policy is recorded" in f for f in p.findings)


def test_the_cadence_depends_on_the_policy_chosen():
    band = plan(policy=P.POLICY_BANDS, last_reviewed=dt.date(2026, 6, 1))
    cal = plan(policy=P.POLICY_CALENDAR, last_reviewed=dt.date(2026, 6, 1))
    assert band.next_review.on == dt.date(2026, 9, 1)
    assert cal.next_review.on == dt.date(2027, 6, 1)


def test_an_overdue_review_is_dated_not_merely_asserted():
    p = plan(policy=P.POLICY_CALENDAR, last_reviewed=dt.date(2024, 1, 15))
    assert p.next_review.passed
    assert any("overdue" in f for f in p.findings)


def test_an_unrecorded_review_date_cannot_be_determined():
    p = plan(last_reviewed=None)
    assert p.next_review is None
    assert any("cannot be determined" in f for f in p.findings)


# ── wash sale policy ────────────────────────────────────────────────────────


EXCL = [
    {"ticker": "XOM", "reason": "harvested_loss", "sold_on": "2026-08-18",
     "source": "direct_index"},
    {"ticker": "PFE", "reason": "harvested_loss", "sold_on": "2026-05-02",
     "source": "direct_index"},
    {"ticker": "KO", "reason": "harvested_loss", "source": "direct_index"},
]

WS_ROWS = [
    {"name": "taxable_di", "account_type": "taxable",
     "wash_sale_policy_applied": True},
    {"name": "roth_ira", "account_type": "roth",
     "wash_sale_policy_applied": False},
    {"name": "401k", "account_type": "tax_deferred",
     "wash_sale_policy_applied": None},
]


def policy(**kw):
    kw.setdefault("as_of", TODAY)
    return P.wash_sale_policy(kw.pop("excluded", EXCL), kw.pop("rows", WS_ROWS), **kw)


def test_the_window_is_stated_as_sixty_one_days_not_thirty():
    assert P.WASH_SALE_TOTAL_DAYS == 2 * P.WASH_SALE_WINDOW_DAYS + 1
    p = policy()
    assert any("61 days" in f for f in p.findings)
    assert any("before the sale" in f for f in p.findings)


def test_an_uncovered_ira_is_the_headline_finding():
    p = policy()
    assert {a.name for a in p.retirement_gaps} == {"roth_ira", "401k"}
    assert any("permanently" in f for f in p.findings)
    assert any("no basis adjustment" in f.lower() for f in p.findings)


def test_unknown_coverage_counts_as_a_gap_not_as_probably_fine():
    """`null` means nobody looked, which is the state the expensive mistake
    happens in."""
    p = policy(rows=[{"name": "401k", "account_type": "tax_deferred",
                      "wash_sale_policy_applied": None}])
    assert p.gaps
    assert any("unknown" in f.lower() for f in p.findings)


def test_full_coverage_is_confirmed_rather_than_silent():
    rows = [{"name": "t", "account_type": "taxable", "wash_sale_policy_applied": True},
            {"name": "r", "account_type": "roth", "wash_sale_policy_applied": True}]
    p = policy(rows=rows)
    assert not p.gaps
    assert any("All 2 recorded account(s) are covered" in f for f in p.findings)


def test_accounts_without_a_type_or_a_flag_are_not_invented():
    p = policy(rows=[{"name": "cash", "value": 1000, "tier": "liquid"}])
    assert p.accounts == []
    assert any("No account coverage is recorded" in f for f in p.findings)


def test_substantially_identical_is_stated_as_the_test():
    assert any("substantially identical" in f for f in policy().findings)


def test_the_rule_is_stated_as_spanning_every_account_and_both_spouses():
    fs = policy().findings
    assert any("every account the household controls" in f for f in fs)
    assert any("spouse" in f.lower() for f in fs)


def test_an_uncovered_spouse_account_is_called_out():
    p = policy(spouse_accounts_covered=False)
    assert any("A spouse's accounts are recorded as not covered" in f
               for f in p.findings)


def test_continuous_harvesting_makes_every_exclusion_standing():
    p = policy(continuous=True, provider="Meridian Direct")
    assert all(e.clear_on(continuous=True) is None for e in p.exclusions)
    assert any("Meridian Direct" in f and "permanently unbuyable" in f for f in p.findings)


def test_a_dated_exclusion_clears_the_day_after_the_window():
    e = P.Exclusion("XOM", "harvested_loss", dt.date(2026, 8, 18), "direct_index")
    assert e.clear_on(continuous=False) == dt.date(2026, 9, 18)


def test_cleared_and_live_exclusions_are_separated_when_harvesting_is_not_continuous():
    p = policy(continuous=False)
    assert any("1 of 2 dated exclusion(s) are still inside" in f for f in p.findings)


def test_an_undated_exclusion_stays_on_the_list():
    p = policy(continuous=False)
    assert any("no `sold_on` date" in f for f in p.findings)
    assert any("an exclusion of unknown age is an exclusion" in f.lower()
               for f in p.findings)


def test_an_empty_exclusion_list_is_reported_rather_than_read_as_safe():
    p = policy(excluded=[])
    assert any("No excluded securities are recorded" in f for f in p.findings)


def test_the_boundary_with_a_portfolio_tool_is_stated_in_the_output():
    p = policy()
    assert any("does not identify losses" in f for f in p.findings)


def test_the_statutory_citation_is_present_and_honest_about_verification():
    assert "Rev. Rul. 2008-5" in P.WASH_SALE_SOURCE
    assert P.WASH_SALE_VERIFIED_ON.startswith("unverified")
    assert P.WASH_SALE_VALUES["ira_basis_adjustment_available"] is False


# ── the boundary ────────────────────────────────────────────────────────────


def test_nothing_in_the_module_reads_the_clock():
    """Dates come from meta.as_of via the caller, never from today()."""
    src = (Path(__file__).resolve().parents[1] / "lib/pf/portfolio.py").read_text()
    assert "date.today" not in src
    assert "datetime.now" not in src
