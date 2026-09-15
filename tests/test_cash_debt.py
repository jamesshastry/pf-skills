"""Cluster 5 — emergency fund, cash yield, debt payoff. Synthetic only."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import auto, cash as K, debt as D  # noqa: E402


# ── the shared threshold ────────────────────────────────────────────────────


def test_buffer_floor_is_one_constant_shared_with_the_pc_skills():
    """Extracted at the second consumer. Identity, not equality — a literal
    would pass while the two drifted apart."""
    assert auto.MIN_BUFFER_MONTHS is K.MIN_BUFFER_MONTHS


# ── target months ───────────────────────────────────────────────────────────


def test_base_case_is_the_floor():
    months, drivers = K.target_months(earners=2, has_dependents=False,
                                      variable_comp_share=None)
    assert months == K.BASE_MONTHS
    assert len(drivers) == 1


def test_single_earner_adds_most():
    two, _ = K.target_months(earners=2, has_dependents=False, variable_comp_share=None)
    one, _ = K.target_months(earners=1, has_dependents=False, variable_comp_share=None)
    assert one - two == K.SINGLE_EARNER_MONTHS


def test_dependents_and_variable_comp_stack():
    months, drivers = K.target_months(earners=1, has_dependents=True,
                                      variable_comp_share=0.4)
    assert months == (K.BASE_MONTHS + K.SINGLE_EARNER_MONTHS
                      + K.DEPENDENTS_MONTHS + K.VARIABLE_COMP_MONTHS)
    assert len(drivers) == 4


def test_variable_comp_below_threshold_does_not_count():
    months, _ = K.target_months(earners=2, has_dependents=False,
                                variable_comp_share=0.1)
    assert months == K.BASE_MONTHS


def test_target_is_capped():
    months, _ = K.target_months(earners=1, has_dependents=True,
                                variable_comp_share=0.9)
    assert months <= K.MAX_MONTHS


# ── sizing ──────────────────────────────────────────────────────────────────


def test_shortfall_blocks_everything_else():
    b = K.size_buffer(liquid=5_000, annual_spending=96_000, earners=1,
                      has_dependents=True)
    assert not b.adequate
    assert b.shortfall > 0
    assert any("blocked" in f for f in b.findings)


def test_adequate_buffer_says_no_action():
    b = K.size_buffer(liquid=64_000, annual_spending=96_000, earners=1,
                      has_dependents=True)
    assert b.adequate
    assert any("No action" in f for f in b.findings)


def test_large_excess_is_flagged_and_handed_on():
    b = K.size_buffer(liquid=617_000, annual_spending=135_000, earners=1,
                      has_dependents=True)
    assert b.excess > 0
    assert any("cash-yield-review" in f for f in b.findings)


def test_excess_only_counts_beyond_the_multiple():
    """Slightly over target is not excess — it is a sensible margin."""
    b = K.size_buffer(liquid=70_000, annual_spending=96_000, earners=1,
                      has_dependents=True)
    assert b.adequate and b.excess == 0


def test_essential_spending_runway_is_offered_as_context_not_as_the_target():
    b = K.size_buffer(liquid=64_000, annual_spending=96_000, earners=1,
                      has_dependents=True)
    assert b.target == b.target_months * (96_000 / 12)  # full spending
    assert any("essential spending only" in f for f in b.findings)


# ── yield ───────────────────────────────────────────────────────────────────

ROWS = [
    {"name": "checking", "value": 40_000, "tier": "liquid", "yield_gross": 0.0001},
    {"name": "mmf", "value": 45_000, "tier": "liquid", "yield_gross": 0.0415},
    {"name": "unknown_acct", "value": 10_000, "tier": "liquid"},
    {"name": "401k", "value": 310_000, "tier": "age_restricted", "yield_gross": 0.0},
]

#: A high-tax state, a fully taxable bank sweep, and a state-exempt Treasury
#: benchmark — the shape where the exemption is worth more than the yield edge.
HIGH_TAX = K.TaxProfile(federal=0.24, niit=0.038, state=0.093, state_code="CA")
SWEEP = [{"name": "sweep", "value": 170_000, "tier": "liquid",
          "asset_class": "cash", "yield_gross": 0.0350,
          "state_tax_exempt": False}]


# ── after-tax yield ─────────────────────────────────────────────────────────


def test_after_tax_yield_applies_state_tax_only_to_taxable_interest():
    assert K.after_tax_yield(0.0350, state_exempt=False, tax=HIGH_TAX) == pytest.approx(0.0220, abs=5e-5)
    assert K.after_tax_yield(0.0375, state_exempt=True, tax=HIGH_TAX) == pytest.approx(0.0271, abs=5e-5)


def test_a_partial_tax_profile_is_treated_as_no_profile():
    """Without the state rate the exemption cannot be valued, and the
    exemption is the whole point. Better to fall back than to silently omit
    the thing being measured."""
    assert not K.TaxProfile(federal=0.24).known
    assert not K.TaxProfile(state=0.093).known
    assert K.TaxProfile(federal=0.24, state=0.093).known


def test_the_exemption_can_outweigh_the_headline_yield_edge():
    """3.50% taxable vs 3.75% exempt: 0.25pp gross becomes 0.51pp after tax."""
    gross_gap = 0.0375 - 0.0350
    net_gap = (K.after_tax_yield(0.0375, state_exempt=True, tax=HIGH_TAX)
               - K.after_tax_yield(0.0350, state_exempt=False, tax=HIGH_TAX))
    assert net_gap > 2 * gross_gap


def test_after_tax_comparison_reproduces_the_worked_example():
    r = K.review_yield(SWEEP, benchmark_apr=0.0375, benchmark_state_exempt=True,
                       benchmark_label="VUSXX", tax=HIGH_TAX)
    assert r.after_tax
    assert round(r.total_foregone) == 860
    assert round(r.total_durable) == 553


def test_the_durable_floor_is_the_exemption_at_the_lower_yield():
    """A floor, not a forecast: valued at the lower of the two gross yields so
    it survives convergence in either direction."""
    r = K.review_yield(SWEEP, benchmark_apr=0.0375, benchmark_state_exempt=True,
                       tax=HIGH_TAX)
    assert r.total_durable == pytest.approx(0.0350 * 0.093 * 170_000)
    assert r.total_durable < r.total_foregone


def test_the_durable_part_is_reported_separately_from_the_floating_part():
    r = K.review_yield(SWEEP, benchmark_apr=0.0375, benchmark_state_exempt=True,
                       tax=HIGH_TAX)
    joined = " ".join(r.findings)
    assert "Only $553 of that is durable" in joined
    assert "Decide on the floor" in joined
    assert "gap widens after tax" in joined


def test_no_durable_part_when_the_benchmark_is_also_taxable():
    r = K.review_yield(SWEEP, benchmark_apr=0.0400, benchmark_state_exempt=False,
                       tax=HIGH_TAX)
    assert r.total_foregone > 0
    assert r.total_durable == 0


def test_a_no_income_tax_state_says_the_exemption_is_worthless():
    no_tax = K.TaxProfile(federal=0.24, niit=0.038, state=0.0, state_code="TX")
    r = K.review_yield(SWEEP, benchmark_apr=0.0375, benchmark_state_exempt=True,
                       tax=no_tax)
    assert r.total_durable == 0
    assert any("worth nothing here" in f for f in r.findings)


def test_without_tax_rates_it_falls_back_to_gross_and_says_so():
    r = K.review_yield(SWEEP, benchmark_apr=0.0375, benchmark_state_exempt=True)
    assert not r.after_tax
    assert any("Compared on gross yield only" in f for f in r.findings)
    assert r.total_foregone == pytest.approx((0.0375 - 0.0350) * 170_000)


def test_yield_apr_is_still_accepted_as_the_original_field_name():
    legacy = [{"name": "x", "value": 10_000, "tier": "liquid", "yield_apr": 0.01}]
    modern = [{"name": "x", "value": 10_000, "tier": "liquid", "yield_gross": 0.01}]
    a = K.review_yield(legacy, benchmark_apr=0.04)
    b = K.review_yield(modern, benchmark_apr=0.04)
    assert a.total_foregone == b.total_foregone


# ── asset class ─────────────────────────────────────────────────────────────


def test_equities_are_not_reviewed_as_cash():
    """`tier: liquid` is true of a stock position. That makes it spendable,
    not a cash-yield candidate."""
    rows = SWEEP + [{"name": "stock", "value": 130_000, "tier": "liquid",
                     "asset_class": "equity"}]
    r = K.review_yield(rows, benchmark_apr=0.0375, tax=HIGH_TAX)
    assert [l.name for l in r.lines] == ["sweep"]


def test_unclassified_holdings_are_reviewed_but_flagged():
    rows = SWEEP + [{"name": "mystery", "value": 10_000, "tier": "liquid"}]
    r = K.review_yield(rows, benchmark_apr=0.0375, tax=HIGH_TAX)
    assert len(r.lines) == 2
    assert any("no `asset_class`" in f for f in r.findings)


def test_no_benchmark_refuses_to_compare():
    r = K.review_yield(ROWS, benchmark_apr=None)
    assert r.lines == []
    assert any("No benchmark rate supplied" in f for f in r.findings)
    assert any("goes stale silently" in f for f in r.findings)


def test_only_liquid_holdings_are_reviewed():
    r = K.review_yield(ROWS, benchmark_apr=0.042)
    assert {l.name for l in r.lines} == {"checking", "mmf", "unknown_acct"}


def test_foregone_yield_is_computed_per_holding():
    r = K.review_yield(ROWS, benchmark_apr=0.042)
    checking = next(l for l in r.lines if l.name == "checking")
    assert checking.foregone == pytest.approx((0.042 - 0.0001) * 40_000)


def test_holding_above_benchmark_forgoes_nothing_rather_than_negative():
    r = K.review_yield([{"name": "hy", "value": 10_000, "tier": "liquid",
                         "yield_apr": 0.06}], benchmark_apr=0.042)
    assert r.lines[0].foregone == 0


def test_unknown_yield_is_counted_and_flagged():
    r = K.review_yield(ROWS, benchmark_apr=0.042)
    assert r.unknown_yields == 1
    assert any("no yield recorded" in f for f in r.findings)


def test_state_triggers_the_treasury_exemption_note():
    r = K.review_yield(ROWS, benchmark_apr=0.042, state="CA")
    assert any("exempt from CA income tax" in f for f in r.findings)


def test_always_warns_against_chasing_yield_with_the_buffer():
    r = K.review_yield(ROWS, benchmark_apr=0.042)
    assert any("liquid and boring" in f for f in r.findings)


# ── debt ────────────────────────────────────────────────────────────────────

DEBTS = [
    {"name": "personal", "balance": 1_800, "apr": 0.03, "minimum_payment": 60},
    {"name": "card", "balance": 6_200, "apr": 0.2249, "minimum_payment": 155},
    {"name": "auto", "balance": 14_800, "apr": 0.0629, "minimum_payment": 410},
    {"name": "student", "balance": 21_500, "apr": 0.0585, "minimum_payment": 240,
     "deductible_interest": True},
]


def test_after_tax_rate_only_applies_to_deductible_interest():
    d = D.parse(DEBTS)
    student = next(x for x in d if x.name == "student")
    card = next(x for x in d if x.name == "card")
    assert student.after_tax_apr(0.24) == pytest.approx(0.0585 * 0.76)
    assert card.after_tax_apr(0.24) == 0.2249


def test_zero_balance_debts_are_dropped():
    assert D.parse([{"name": "paid", "balance": 0, "apr": 0.1,
                     "minimum_payment": 0}]) == []


def test_avalanche_orders_by_after_tax_rate_not_headline():
    """Deductibility can invert the sequence, which is the point of tracking
    it. 7% deductible is 5.32% after tax at 24% — below a 6% non-deductible
    debt that looks cheaper on the headline number."""
    pair = D.parse([
        {"name": "mortgage", "balance": 200_000, "apr": 0.07,
         "minimum_payment": 1_400, "deductible_interest": True},
        {"name": "auto", "balance": 15_000, "apr": 0.06, "minimum_payment": 400},
    ])
    assert [x.name for x in D.order_for(pair, D.AVALANCHE, 0.0)] == ["mortgage", "auto"]
    assert [x.name for x in D.order_for(pair, D.AVALANCHE, 0.24)] == ["auto", "mortgage"]


def test_deductibility_widens_an_existing_gap_without_reordering():
    """The common case: it changes the margin, not the sequence."""
    d = D.parse(DEBTS)
    for rate in (0.0, 0.24):
        order = [x.name for x in D.order_for(d, D.AVALANCHE, rate)]
        assert order.index("auto") < order.index("student")


def test_snowball_orders_by_balance():
    d = D.parse(DEBTS)
    assert [x.name for x in D.order_for(d, D.SNOWBALL)] == [
        "personal", "card", "auto", "student"]


def test_unknown_method_raises():
    with pytest.raises(ValueError):
        D.order_for(D.parse(DEBTS), "vibes")


def test_avalanche_costs_less_interest_than_snowball():
    p = D.plan(DEBTS, monthly_extra=600, marginal_rate=0.24)
    assert p.avalanche.total_interest < p.snowball.total_interest
    assert p.cost_of_snowball > 0


def test_the_cost_of_snowball_is_stated_in_dollars():
    p = D.plan(DEBTS, monthly_extra=600, marginal_rate=0.24)
    assert any("Snowball costs $" in f for f in p.findings)
    assert any("not optimal" in f for f in p.findings)


def test_more_extra_payment_clears_faster_and_costs_less():
    slow = D.plan(DEBTS, monthly_extra=0)
    fast = D.plan(DEBTS, monthly_extra=1_000)
    assert fast.avalanche.months < slow.avalanche.months
    assert fast.avalanche.total_interest < slow.avalanche.total_interest


def test_identical_orderings_report_no_tradeoff():
    same = [{"name": "a", "balance": 1_000, "apr": 0.20, "minimum_payment": 50},
            {"name": "b", "balance": 5_000, "apr": 0.05, "minimum_payment": 100}]
    p = D.plan(same, monthly_extra=200)
    assert p.cost_of_snowball == 0
    assert any("no trade-off" in f for f in p.findings)


def test_non_terminating_schedule_is_detected_not_looped_forever():
    """Minimum payments below the interest accrual. The answer is
    restructuring, not ordering."""
    bad = [{"name": "trap", "balance": 20_000, "apr": 0.29,
            "minimum_payment": 10}]
    p = D.plan(bad, monthly_extra=0)
    assert not p.avalanche.terminated
    assert any("does not terminate" in f for f in p.findings)
    assert p.cost_of_snowball is None


def test_invest_instead_comparison_uses_after_tax_rates():
    p = D.plan(DEBTS, monthly_extra=600, marginal_rate=0.24,
               expected_return_apr=0.07)
    f = " ".join(p.findings)
    assert "competes with investing" in f
    assert "4.45%" in f  # student loan after tax, not 5.85%
    assert "certain" in f and "uncertain" in f


def test_no_expected_return_skips_rather_than_assumes():
    p = D.plan(DEBTS, monthly_extra=600, marginal_rate=0.24)
    assert any("skipped rather than assumed" in f for f in p.findings)


def test_high_rate_debt_short_circuits_the_debate():
    p = D.plan(DEBTS, monthly_extra=600)
    assert any("ordering debate is academic" in f for f in p.findings)


def test_empty_debt_list_is_handled():
    p = D.plan([])
    assert p.avalanche is None
    assert any("Nothing to order" in f for f in p.findings)


def test_cleared_debt_minimum_rolls_into_the_next_target():
    """Both methods snowball the freed minimum; without it the comparison
    would be unfair to whichever method clears a large minimum first."""
    s = D.simulate(D.parse(DEBTS), method=D.AVALANCHE, monthly_extra=0)
    total_min = sum(d["minimum_payment"] for d in DEBTS)
    # Naive: every debt paid only its own minimum for the whole term.
    naive_months = max(d["balance"] / d["minimum_payment"] for d in DEBTS)
    assert s.months < naive_months
    assert total_min > 0
