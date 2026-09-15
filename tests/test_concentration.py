"""Cluster 6 — employer concentration and equity comp. Synthetic only."""

import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import concentration as C  # noqa: E402

TODAY = dt.date(2026, 8, 31)
BASE = dict(employer="Northwind", income_from_employer=180_000,
            total_income=180_000, held_value=22_000, unvested_value=41_000,
            investable=423_000, liquid=85_000, monthly_spending=8_000,
            sell_at_vest=False)


def test_shares_are_computed_against_the_right_denominators():
    e = C.assess_exposure(**BASE)
    assert e.income_share == 1.0
    assert e.asset_share == pytest.approx(22_000 / 423_000)


def test_unvested_counts_as_exposure_but_not_as_an_asset():
    """It is contingent on the employment that the scenario removes."""
    e = C.assess_exposure(**BASE)
    assert e.total_at_risk == 22_000 + 41_000 + 180_000
    assert e.investable == 423_000  # unvested excluded


def test_asset_severity_bands():
    assert C.assess_exposure(**{**BASE, "held_value": 20_000}).asset_severity == "within_guideline"
    assert C.assess_exposure(**{**BASE, "held_value": 60_000}).asset_severity == "elevated"
    assert C.assess_exposure(**{**BASE, "held_value": 200_000}).asset_severity == "severe"


def test_income_severity_is_scored_independently():
    lo = C.assess_exposure(**{**BASE, "income_from_employer": 50_000,
                              "total_income": 200_000})
    mid = C.assess_exposure(**{**BASE, "income_from_employer": 140_000,
                               "total_income": 200_000})
    assert lo.income_severity == "within_guideline"
    assert mid.income_severity == "elevated"
    assert C.assess_exposure(**BASE).income_severity == "severe"


def test_overall_severity_is_the_worse_of_the_two():
    """A diversified portfolio does not pay the mortgage when the salary
    stops. An earlier version scored assets only, and labelled a household
    with 100% income concentration 'within guideline'."""
    e = C.assess_exposure(**{**BASE, "held_value": 20_000})
    assert e.asset_severity == "within_guideline"
    assert e.income_severity == "severe"
    assert e.severity == "severe"


def test_income_concentration_is_named_as_the_binding_constraint():
    e = C.assess_exposure(**{**BASE, "held_value": 20_000})
    assert any("binding constraint" in f for f in e.findings)
    assert any("not fixable by selling" in f for f in e.findings)


def test_joint_scenario_combines_all_three_losses():
    e = C.assess_exposure(**BASE)
    s = C.joint_scenario(e)
    assert s.stock_loss == 11_000
    assert s.income_loss == 180_000
    assert s.unvested_loss == 41_000
    assert s.total_loss == 232_000


def test_joint_loss_exceeds_either_leg_alone():
    """The whole reason the scenario is modelled jointly."""
    e = C.assess_exposure(**BASE)
    s = C.joint_scenario(e)
    assert s.total_loss > s.stock_loss
    assert s.total_loss > s.income_loss


def test_runway_is_measured_after_the_share_decline():
    e = C.assess_exposure(**BASE)
    s = C.joint_scenario(e)
    assert s.liquid_after == 85_000 - 11_000
    assert s.runway_months == pytest.approx((85_000 - 11_000) / 8_000)


def test_runway_cannot_go_negative():
    e = C.assess_exposure(**{**BASE, "held_value": 500_000, "liquid": 100_000})
    assert C.joint_scenario(e).liquid_after == 0


def test_the_single_bet_finding_fires_on_income_alone():
    """Gating it on the asset share too suppressed it for exactly the
    household that needs it: diversified portfolio, one income."""
    e = C.assess_exposure(**{**BASE, "held_value": 5_000})
    assert e.asset_severity == "within_guideline"
    assert any("not two" in f for f in e.findings)


def test_the_single_bet_finding_needs_some_employer_equity():
    e = C.assess_exposure(**{**BASE, "held_value": 0, "unvested_value": 0})
    assert not any("not two" in f for f in e.findings)


def test_no_sell_at_vest_policy_is_called_out_with_the_buy_today_framing():
    e = C.assess_exposure(**BASE)
    joined = " ".join(e.findings)
    assert "No sell-at-vest policy" in joined
    assert "immediately buying" in joined
    assert "would not be bought today" in joined


def test_policy_in_force_is_endorsed():
    e = C.assess_exposure(**{**BASE, "sell_at_vest": True})
    assert any("is in force" in f for f in e.findings)


def test_unknown_policy_is_distinguished_from_absent():
    e = C.assess_exposure(**{**BASE, "sell_at_vest": None})
    assert any("not recorded" in f for f in e.findings)


def test_diversifying_is_always_framed_as_not_a_market_call():
    for policy in (True, False, None):
        e = C.assess_exposure(**{**BASE, "sell_at_vest": policy})
        assert any("not a market call" in f for f in e.findings)


# ── vesting ─────────────────────────────────────────────────────────────────

GRANTS = [
    {"id": "g2023", "annual_value": 9_000, "completes": "2027-02-28"},
    {"id": "g2024", "annual_value": 11_000, "completes": "2028-02-28"},
    {"id": "g2025", "annual_value": 5_000, "completes": "2029-02-28"},
]


def test_run_rate_sums_every_grant():
    o = C.vesting_outlook(GRANTS, today=TODAY)
    assert o.run_rate == 25_000


def test_steady_state_excludes_grants_completing_in_the_horizon():
    o = C.vesting_outlook(GRANTS, today=TODAY)
    assert o.delta == 20_000       # g2023 + g2024 within 24 months
    assert o.steady_state == 5_000
    assert o.next_cliff == dt.date(2027, 2, 28)


def test_horizon_changes_what_counts_as_near_term():
    short = C.vesting_outlook(GRANTS, today=TODAY, horizon_months=12)
    assert short.delta == 9_000
    assert short.steady_state == 16_000


def test_multiple_expiries_are_described_as_steps_not_as_one_date():
    """$20K does not all go on the first cliff date — the wording must not
    imply it does."""
    o = C.vesting_outlook(GRANTS, today=TODAY)
    joined = " ".join(o.findings)
    assert "in 2 steps" in joined
    assert "$9,000" in joined  # the first step, separately


def test_single_expiry_names_the_date_directly():
    o = C.vesting_outlook(GRANTS[:1], today=TODAY)
    assert "on 2027-02-28" in " ".join(o.findings)


def test_no_near_term_cliff_says_the_run_rate_is_durable():
    o = C.vesting_outlook([GRANTS[2]], today=TODAY)
    assert o.delta == 0
    assert any("durable" in f for f in o.findings)


def test_refresh_dependence_is_named_as_optimistic():
    o = C.vesting_outlook(GRANTS, today=TODAY)
    joined = " ".join(o.findings)
    assert "discretionary decision by someone else" in joined
    assert "least likely" in joined


def test_no_grants_asks_for_the_schedule():
    o = C.vesting_outlook([], today=TODAY)
    assert o.run_rate == 0
    assert any("record the vest schedule" in f for f in o.findings)


def test_unparseable_completion_date_is_ignored_not_crashed():
    o = C.vesting_outlook([{"id": "x", "annual_value": 1_000,
                            "completes": "next spring"}], today=TODAY)
    assert o.run_rate == 1_000
    assert o.delta == 0


def test_already_completed_grants_do_not_count_as_upcoming_cliffs():
    past = [{"id": "old", "annual_value": 5_000, "completes": "2020-01-01"}]
    o = C.vesting_outlook(past, today=TODAY)
    assert o.delta == 0
