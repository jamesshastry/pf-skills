"""PFIC divest-or-comply — the decision, the arithmetic, and the refusal."""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import pfic as P  # noqa: E402

D = dt.date


def rates(years=(2019, 2020, 2021), top=0.37, quarters=None, under=0.06):
    """A complete series over 2019–2022, unless asked for something narrower."""
    q = quarters
    if q is None:
        q = [f"{y}Q{i}" for y in range(2019, 2024) for i in range(1, 5)]
    return P.RateSeries(top_marginal={y: top for y in years},
                        underpayment={k: under for k in q})


def fund(**kw):
    base = {"name": "icici_equity", "value": 60_000, "basis": 20_000,
            "acquired": "2019-01-01", "qef_statement_available": False,
            "marketable_on_qualified_exchange": False}
    base.update(kw)
    return base


# ── the allocation ──────────────────────────────────────────────────────────


def test_the_gain_is_allocated_pro_rata_across_every_year_held():
    s = P.allocate(1000.0, acquired=D(2019, 1, 1), disposed=D(2021, 12, 31))
    assert [x.year for x in s] == [2019, 2020, 2021]
    assert round(sum(x.amount for x in s), 6) == 1000.0
    # 2020 is a leap year, so its slice is very slightly the largest.
    assert s[1].amount > s[0].amount


def test_the_allocation_is_by_days_not_by_whole_years():
    """A December purchase gets a sliver of that year, not a full year."""
    s = P.allocate(1000.0, acquired=D(2019, 12, 1), disposed=D(2020, 12, 31))
    assert s[0].days == 31
    assert s[0].amount < s[1].amount / 10


def test_the_disposition_year_is_flagged_as_current():
    s = P.allocate(1000.0, acquired=D(2019, 1, 1), disposed=D(2021, 6, 30))
    assert [x.current_year for x in s] == [False, False, True]


def test_a_single_year_hold_is_all_current_year():
    s = P.allocate(500.0, acquired=D(2021, 1, 1), disposed=D(2021, 12, 31))
    assert len(s) == 1 and s[0].current_year


# ── the charge ──────────────────────────────────────────────────────────────


def test_each_prior_year_is_taxed_at_that_years_rate_not_the_holders():
    r = P.RateSeries(
        top_marginal={2019: 0.10, 2020: 0.90, 2021: 0.37},
        underpayment={f"{y}Q{i}": 0.0 for y in range(2019, 2024) for i in range(1, 5)})
    c = P.compute_charge(3000.0, acquired=D(2019, 1, 1), disposed=D(2021, 12, 31),
                         rates=r)
    by_year = {s.year: s for s in c.slices}
    assert by_year[2019].tax < by_year[2020].tax
    assert by_year[2020].top_rate == 0.90


def test_the_current_year_slice_carries_no_interest():
    c = P.compute_charge(3000.0, acquired=D(2019, 1, 1), disposed=D(2021, 12, 31),
                         rates=rates())
    current = [s for s in c.slices if s.current_year][0]
    assert current.interest == 0.0
    assert all(s.interest > 0 for s in c.slices if not s.current_year)


def test_interest_compounds_so_the_oldest_slice_carries_the_most():
    c = P.compute_charge(3000.0, acquired=D(2019, 1, 1), disposed=D(2021, 12, 31),
                         rates=rates())
    prior = sorted((s for s in c.slices if not s.current_year), key=lambda s: s.year)
    assert prior[0].interest > prior[1].interest


def test_a_zero_underpayment_rate_produces_tax_with_no_interest():
    r = P.RateSeries(
        top_marginal={y: 0.37 for y in (2019, 2020, 2021)},
        underpayment={f"{y}Q{i}": 0.0 for y in range(2019, 2024) for i in range(1, 5)})
    c = P.compute_charge(1000.0, acquired=D(2019, 1, 1), disposed=D(2021, 12, 31),
                         rates=r)
    assert c.interest == 0.0
    assert round(c.tax, 6) == 370.0


def test_a_long_hold_makes_the_interest_exceed_the_tax():
    """The finding nobody intuits, and the reason this is computed."""
    yrs = range(1998, 2027)
    r = P.RateSeries(
        top_marginal={y: 0.37 for y in yrs},
        underpayment={f"{y}Q{i}": 0.08 for y in yrs for i in range(1, 5)})
    c = P.compute_charge(100_000.0, acquired=D(1999, 1, 1), disposed=D(2025, 6, 30),
                         rates=r)
    assert c.interest_exceeds_tax
    assert any("interest exceeds the tax" in f for f in c.findings)


def test_the_effective_rate_can_exceed_one_hundred_percent():
    yrs = range(1990, 2027)
    r = P.RateSeries(
        top_marginal={y: 0.39 for y in yrs},
        underpayment={f"{y}Q{i}": 0.10 for y in yrs for i in range(1, 5)})
    c = P.compute_charge(50_000.0, acquired=D(1995, 1, 1), disposed=D(2025, 6, 30),
                         rates=r)
    assert c.effective_rate > 1.0


def test_the_estimate_declares_its_compounding_basis():
    c = P.compute_charge(1000.0, acquired=D(2019, 1, 1), disposed=D(2021, 12, 31),
                         rates=rates())
    assert any("compounds daily" in f for f in c.findings)


# ── the refusal ─────────────────────────────────────────────────────────────


def test_a_missing_marginal_rate_refuses_the_whole_figure():
    """Not a smaller charge — an incomplete one, which would read as smaller."""
    r = rates(years=(2019, 2021))
    c = P.compute_charge(3000.0, acquired=D(2019, 1, 1), disposed=D(2021, 12, 31),
                         rates=r)
    assert not c.computable
    assert c.total is None and c.tax is None and c.interest is None
    assert "top_marginal_rate.2020" in c.missing_rates


def test_a_missing_quarterly_rate_also_refuses():
    r = rates(quarters=[f"{y}Q{i}" for y in (2019, 2020) for i in range(1, 5)])
    c = P.compute_charge(3000.0, acquired=D(2019, 1, 1), disposed=D(2021, 12, 31),
                         rates=r)
    assert not c.computable
    assert any(k.startswith("underpayment_rate.2021") for k in c.missing_rates)


def test_the_refusal_still_reports_the_shape_of_the_exposure():
    c = P.compute_charge(3000.0, acquired=D(2019, 1, 1), disposed=D(2021, 12, 31),
                         rates=P.RateSeries())
    assert len(c.slices) == 3
    assert round(c.holding_years) == 3
    assert any("shape" in f for f in c.findings)


def test_the_refusal_names_every_missing_rate_exactly():
    c = P.compute_charge(3000.0, acquired=D(2019, 1, 1), disposed=D(2021, 12, 31),
                         rates=P.RateSeries())
    assert "top_marginal_rate.2019" in c.missing_rates
    assert "underpayment_rate.2020Q2" in c.missing_rates


def test_rates_are_read_from_facts_not_encoded():
    """Nothing in the module supplies a rate. An empty facts block is empty."""
    assert P.RateSeries.from_facts(None).top_marginal == {}
    assert P.RateSeries.from_facts({}).underpayment == {}


# ── regime availability ─────────────────────────────────────────────────────


def test_no_information_statement_means_qef_is_unavailable():
    a = P.regimes_for(fund())
    assert a.regime == P.DEFAULT_1291
    assert any("QEF is unavailable" in r for r in a.reasons)
    assert any("nothing to elect" in r for r in a.reasons)


def test_null_is_not_false_on_regime_availability():
    a = P.regimes_for(fund(qef_statement_available=None,
                           marketable_on_qualified_exchange=None))
    assert not a.determinable
    assert a.regime == P.DEFAULT_1291
    assert any("unknown" in r.lower() for r in a.reasons)


def test_an_available_statement_gives_qef():
    a = P.regimes_for(fund(qef_statement_available=True))
    assert a.regime == P.QEF


def test_marketable_stock_gives_mark_to_market():
    a = P.regimes_for(fund(marketable_on_qualified_exchange=True))
    assert a.regime == P.MTM


def test_qef_outranks_mark_to_market_when_both_are_available():
    a = P.regimes_for(fund(qef_statement_available=True,
                           marketable_on_qualified_exchange=True))
    assert a.regime == P.QEF


# ── divest or comply ────────────────────────────────────────────────────────


def test_no_election_available_is_the_case_for_selling():
    d = P.divest_or_comply([fund()], rates=rates(), as_of=D(2021, 6, 30))
    assert not d.any_election_available
    assert any("case for selling" in f for f in d.findings)


def test_the_india_guide_is_pointed_at_not_restated():
    d = P.divest_or_comply([fund()], rates=rates(), as_of=D(2021, 6, 30))
    assert any("INDIA_PORTFOLIO_GUIDE.md" in f for f in d.findings)


def test_form_8621_is_counted_per_fund():
    d = P.divest_or_comply([fund(name="a"), fund(name="b"), fund(name="c")],
                           rates=rates(), as_of=D(2021, 6, 30),
                           annual_cost_per_form=300)
    assert d.forms_per_year == 3
    assert d.annual_compliance == 900


def test_breakeven_is_the_charge_over_the_annual_cost():
    d = P.divest_or_comply([fund()], rates=rates(), as_of=D(2021, 6, 30),
                           annual_cost_per_form=500)
    assert d.charge.computable
    assert d.breakeven_years == d.charge.total / d.annual_compliance
    assert any("no year in which selling gets cheaper" in f for f in d.findings)


def test_without_a_cost_quote_the_comparison_is_inverted_not_defaulted():
    d = P.divest_or_comply([fund()], rates=rates(), as_of=D(2021, 6, 30))
    assert d.annual_compliance is None
    assert any("only if preparation comes in under" in f for f in d.findings)


def test_the_charge_uses_the_earliest_acquisition_not_an_average():
    """The longest holding period drives the interest; averaging flatters it."""
    d = P.divest_or_comply(
        [fund(name="old", acquired="2019-01-01"),
         fund(name="new", acquired="2021-01-01")],
        rates=rates(), as_of=D(2021, 6, 30))
    assert d.charge.acquired == D(2019, 1, 1)


def test_a_position_at_a_loss_is_the_cheapest_one_to_leave():
    d = P.divest_or_comply([fund(value=10_000, basis=20_000)],
                           rates=rates(), as_of=D(2021, 6, 30))
    assert d.charge is None
    assert any("cheapest one to leave" in f for f in d.findings)


def test_a_fund_missing_a_basis_is_excluded_from_the_charge_not_the_cost():
    d = P.divest_or_comply([fund(name="priced"), fund(name="unpriced", basis=None)],
                           rates=rates(), as_of=D(2021, 6, 30),
                           annual_cost_per_form=300)
    assert d.forms_per_year == 2
    assert any("not excluded from the compliance cost" in f for f in d.findings)


def test_the_rate_differential_is_shown_against_plain_ltcg():
    d = P.divest_or_comply([fund()], rates=rates(), as_of=D(2021, 6, 30),
                           ltcg_rate=0.15)
    assert any("wrong wrapper" in f for f in d.findings)


def test_an_available_election_changes_the_arithmetic_rather_than_settling_it():
    d = P.divest_or_comply([fund(qef_statement_available=True)],
                           rates=rates(), as_of=D(2021, 6, 30))
    assert d.any_election_available
    assert any("does not clear what has already accrued" in f for f in d.findings)


def test_no_holdings_asks_for_an_explicit_empty_list():
    d = P.divest_or_comply([], rates=rates(), as_of=D(2021, 6, 30))
    assert any("pfic_holdings: []" in f for f in d.findings)


def test_every_report_ends_at_a_cross_border_preparer():
    d = P.divest_or_comply([fund()], rates=rates(), as_of=D(2021, 6, 30))
    assert any("not a filing position" in f for f in d.findings)
