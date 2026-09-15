"""Cluster 8 — rent vs buy and mortgage review. Synthetic only."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import housing as H  # noqa: E402

PURCHASE = {"price": 520_000, "down_payment": 104_000, "mortgage_rate": 0.0645,
            "term_years": 30, "property_tax_rate": 0.0185,
            "insurance_annual": 1_800, "hoa_monthly": 0,
            "maintenance_rate": 0.01}


# ── amortisation ────────────────────────────────────────────────────────────


def test_payment_matches_the_standard_formula():
    assert H.monthly_payment(416_000, 0.0645, 30) == pytest.approx(2_615.9, abs=1)


def test_zero_rate_payment_is_straight_line():
    assert H.monthly_payment(120_000, 0.0, 10) == 1_000


def test_zero_principal_has_no_payment():
    assert H.monthly_payment(0, 0.06, 30) == 0


def test_amortisation_splits_interest_and_principal():
    i, p, bal = H.amortise(416_000, 0.0645, 30, 12)
    assert i > p                       # early years are mostly interest
    assert bal == pytest.approx(416_000 - p, abs=1)


def test_amortisation_stops_at_the_term_not_the_requested_months():
    _, _, bal = H.amortise(100_000, 0.05, 10, 600)
    assert bal == 0


# ── the nominal/real trap ───────────────────────────────────────────────────


def test_default_appreciation_equals_rent_growth_ie_zero_real():
    """Setting nominal appreciation to 0 would silently assume houses fall in
    real terms every year, which decides the answer on its own."""
    assert H.DEFAULT_APPRECIATION == H.DEFAULT_RENT_GROWTH


def test_the_report_states_the_real_appreciation_implied():
    c = H.compare(PURCHASE, monthly_rent=2_400, years=7)
    assert any("+0.0% real" in f or "0.0% real" in f for f in c.findings)


def test_a_real_appreciation_assumption_is_flagged_as_supplied():
    c = H.compare(PURCHASE, monthly_rent=2_400, years=7, appreciation=0.06)
    assert any("supplied assumption" in f for f in c.findings)


def test_treating_a_nominal_return_as_real_destroys_the_answer():
    """The defect that shipped briefly: a nominal 7% return applied against
    zero NOMINAL appreciation, which assumes houses fall in real terms every
    year. Kept as a regression guard."""
    wrong = H.compare(PURCHASE, monthly_rent=2_400, years=15,
                      investment_return=0.07, appreciation=0.0)
    right = H.compare(PURCHASE, monthly_rent=2_400, years=15)
    assert wrong.difference > right.difference * 1.5


def test_the_crossover_sits_near_the_conventional_price_to_rent_boundary():
    """Calibration guard. Price-to-rent around 15 is the widely used
    buy/rent boundary; a model that lands far from it is miscalibrated and
    will look biased whichever way it leans."""
    def verdict(rent):
        return H.compare(PURCHASE, monthly_rent=rent, years=15,
                         investment_return=0.07, appreciation=0.03,
                         rent_growth=0.03).owning_cheaper

    # P/R 18.1 -> rent; P/R 12.7 -> buy. The flip is between them.
    assert not verdict(2_400)
    assert verdict(3_400)


def test_a_very_high_price_to_rent_ratio_says_rent_decisively():
    """Validated against a hand analysis at P/R 30, which reached the same
    conclusion independently."""
    c = H.compare({**PURCHASE, "price": 1_200_000, "down_payment": 240_000,
                   "mortgage_rate": 0.065, "property_tax_rate": 0.0125,
                   "insurance_annual": 2_400},
                  monthly_rent=3_300, years=15, investment_return=0.07,
                  appreciation=0.04, rent_growth=0.035)
    assert not c.owning_cheaper
    assert c.breakeven_years is None


# ── the comparison ──────────────────────────────────────────────────────────


def test_principal_returns_through_terminal_equity_rather_than_being_a_cost():
    own = H.cost_of_owning(PURCHASE, 7, investment_return=0.07,
                           appreciation=0.03)
    assert own["principal"] > 0
    # Net cost is outflows less what the sale returns, so principal is not
    # double-counted as a cost.
    assert own["total"] == pytest.approx(own["outflows_fv"] - own["terminal_equity"])


def test_outflows_are_carried_forward_to_the_horizon():
    """A dollar spent in year 3 could have been invested for the rest of the
    term. Summing undiscounted flatters whichever side spends later."""
    undiscounted = H.cost_of_owning(PURCHASE, 10, investment_return=0.0,
                                    appreciation=0.0)["outflows_fv"]
    compounded = H.cost_of_owning(PURCHASE, 10, investment_return=0.07,
                                  appreciation=0.0)["outflows_fv"]
    assert compounded > undiscounted


def test_a_zero_investment_return_reduces_to_a_plain_sum():
    own = H.cost_of_owning(PURCHASE, 5, investment_return=0.0, appreciation=0.0)
    plain = (own["down"] + 520_000 * H.BUY_COSTS + own["tax"] + own["insurance"]
             + own["maintenance"] + own["hoa"]
             + H.monthly_payment(own["loan"], 0.0645, 30) * 12 * 5)
    assert own["outflows_fv"] == pytest.approx(plain, abs=1)


def test_terminal_equity_is_sale_less_costs_less_balance():
    own = H.cost_of_owning(PURCHASE, 10, investment_return=0.07, appreciation=0.04)
    assert own["terminal_equity"] == pytest.approx(
        own["future_price"] * (1 - H.SELL_COSTS) - own["balance"])


def test_transaction_costs_are_charged_on_the_way_in_and_out():
    own = H.cost_of_owning(PURCHASE, 1, investment_return=0.0, appreciation=0.0)
    assert own["transaction"] == pytest.approx(
        520_000 * H.BUY_COSTS + 520_000 * H.SELL_COSTS, abs=1)


def test_rent_total_compounds_with_growth():
    flat = H.cost_of_renting(2_400, 3, rent_growth=0.0, investment_return=0.0)
    grown = H.cost_of_renting(2_400, 3, rent_growth=0.03, investment_return=0.0)
    assert flat == 2_400 * 12 * 3
    assert grown > flat


def test_rent_is_carried_forward_at_the_same_rate_as_owning():
    """Both sides must use the same clock or the comparison is rigged."""
    plain = H.cost_of_renting(2_400, 10, rent_growth=0.0, investment_return=0.0)
    fv = H.cost_of_renting(2_400, 10, rent_growth=0.0, investment_return=0.07)
    assert fv > plain


def test_short_holds_favour_renting():
    short = H.compare(PURCHASE, monthly_rent=2_400, years=3)
    assert not short.owning_cheaper


def test_a_high_enough_rent_makes_buying_win():
    dear = H.compare(PURCHASE, monthly_rent=6_000, years=10)
    assert dear.owning_cheaper
    assert dear.breakeven_years is not None
    assert any("Break-even at about" in f for f in dear.findings)


def test_higher_rent_shortens_the_breakeven():
    cheap = H.compare(PURCHASE, monthly_rent=4_000, years=10)
    dear = H.compare(PURCHASE, monthly_rent=6_000, years=10)
    assert cheap.breakeven_years is not None and dear.breakeven_years is not None
    assert dear.breakeven_years < cheap.breakeven_years


def test_appreciation_drives_the_crossover():
    """Validated against a hand analysis of a real household: the flip from
    rent to buy sits in the high fives / low sixes at a 6.5% mortgage and a
    7% alternative return."""
    low = H.compare(PURCHASE, monthly_rent=2_400, years=15, investment_return=0.07,
                    appreciation=0.03, rent_growth=0.035)
    high = H.compare(PURCHASE, monthly_rent=2_400, years=15, investment_return=0.07,
                     appreciation=0.09, rent_growth=0.035)
    assert not low.owning_cheaper
    assert high.owning_cheaper


def test_the_payment_versus_rent_comparison_is_explicitly_rejected():
    c = H.compare(PURCHASE, monthly_rent=2_400, years=7)
    assert any("Do not compare the mortgage payment to the rent" in f
               for f in c.findings)


def test_selling_costs_are_always_named():
    c = H.compare(PURCHASE, monthly_rent=2_400, years=7)
    assert any("Selling costs alone" in f for f in c.findings)


# ── mortgage review ─────────────────────────────────────────────────────────


def test_pmi_below_the_threshold_is_flagged_as_free_money():
    r = H.review_mortgage(balance=300_000, rate=0.05, term_years=25,
                          value=500_000, pmi_monthly=180)
    assert r.ltv == 0.6
    assert any("free money" in f for f in r.findings)


def test_pmi_above_the_threshold_is_not_flagged():
    r = H.review_mortgage(balance=450_000, rate=0.05, term_years=25,
                          value=500_000, pmi_monthly=180)
    assert not any("free money" in f for f in r.findings)


def test_unknown_value_leaves_ltv_none():
    r = H.review_mortgage(balance=300_000, rate=0.05, term_years=25, value=None)
    assert r.ltv is None


def test_extra_payment_shortens_the_term_and_saves_interest():
    r = H.review_mortgage(balance=300_000, rate=0.06, term_years=30,
                          value=500_000, extra_monthly=500)
    joined = " ".join(r.findings)
    assert "instead of 30y" in joined
    assert "saving about" in joined


def test_prepayment_is_framed_against_investing_with_the_certainty_point():
    r = H.review_mortgage(balance=300_000, rate=0.06, term_years=30,
                          value=500_000, extra_monthly=500)
    joined = " ".join(r.findings)
    assert "guaranteed" in joined
    assert "debt-payoff-priority" in joined


def test_refinance_is_always_framed_as_a_breakeven_not_a_rate_comparison():
    r = H.review_mortgage(balance=300_000, rate=0.06, term_years=30, value=500_000)
    joined = " ".join(r.findings)
    assert "break-even calculation, not a rate comparison" in joined
    assert "increasing total interest" in joined
