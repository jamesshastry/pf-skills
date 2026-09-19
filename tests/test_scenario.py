"""Scenario events reconcile monthly and never turn assumptions into facts."""
from __future__ import annotations

import copy
import datetime as dt
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from pf import cash as C, facts as F, housing_affordability as H  # noqa: E402
from pf import retirement as R, scenario as S, timeseries as T  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def baseline(**changes) -> S.Baseline:
    values = dict(
        as_of=dt.date(2026, 1, 1), currency="USD", basis="nominal",
        name="current", monthly_after_tax_income=10_000,
        monthly_current_spending=6_000, monthly_essential_spending=4_500,
        monthly_employee_retirement_contribution=1_000,
        monthly_employer_retirement_contribution=250,
        monthly_other_outflows=0, cash=50_000, marketable=100_000,
        retirement=200_000, illiquid=0, debt=20_000, employer_stock=20_000,
        employer_stock_in_marketable=False,
        unvested_equity=40_000, emergency_floor=30_000,
        annual_savings_floor=24_000, current_age=40,
        retirement_spending_annual=72_000, source_fingerprint="baseline",
    )
    values.update(changes)
    return S.Baseline(**values)


def spec(events, **changes) -> S.ScenarioSpec:
    values = dict(
        id="test-case", label="Test case", as_of=dt.date(2026, 1, 1),
        baseline="current", kind="stress", horizon_months=12,
        objective="compare_only", currency="USD", basis="nominal",
        events=tuple(events),
    )
    values.update(changes)
    return S.ScenarioSpec(**values)


def event(event_type, **changes) -> S.ScenarioEvent:
    values = dict(id=f"event-{event_type.replace('_', '-')}", type=event_type,
                  start_month=1)
    values.update(changes)
    return S.ScenarioEvent(**values)


def test_cash_and_stock_with_same_gross_value_have_different_liquidity():
    cash = event("cash_receipt", gross_amount=100_000, tax_reserve=20_000)
    stock = event("asset_receipt", market_value=100_000, cost_basis=None,
                  liquidate=False)
    cash_result = S.run_scenario(baseline(), spec([cash]))
    stock_result = S.run_scenario(baseline(),
                                  replace(spec([stock]), id="stock-case"))
    assert cash_result.terminal_liquidity_change == pytest.approx(80_000)
    assert stock_result.terminal_liquidity_change == pytest.approx(0)
    assert S.windfall_net_amount(stock)[0] is None


def test_missing_stock_basis_never_becomes_zero_basis():
    with pytest.raises(S.ScenarioError, match="known cost_basis"):
        event("asset_receipt", market_value=100_000, liquidate=True,
              tax_rate=0.2)


def test_correlated_job_loss_applies_stock_and_unvested_loss_once():
    loss = event(
        "employment_loss", person_id="p1", duration_months=3,
        after_tax_income_loss_monthly=10_000,
        employee_contribution_loss_monthly=1_000,
        employer_match_loss_monthly=250, unvested_forfeiture=40_000,
        employer_stock_change=-0.5,
    )
    result = S.run_scenario(baseline(), spec([loss], horizon_months=4))
    assert result.monthly_path[0].unvested_equity == 0
    assert result.monthly_path[-1].unvested_equity == 0
    assert result.monthly_path[0].employer_stock == pytest.approx(10_000)
    assert result.monthly_path[-1].employer_stock == pytest.approx(10_000)


def test_employer_stock_balance_sheet_flag_prevents_double_counting():
    separate = baseline(marketable=100_000, employer_stock=20_000,
                        employer_stock_in_marketable=False)
    embedded = baseline(marketable=120_000, employer_stock=20_000,
                        employer_stock_in_marketable=True)
    assert separate.net_worth == embedded.net_worth
    loss = event("employment_loss", person_id="p1", duration_months=1,
                 after_tax_income_loss_monthly=10_000,
                 employer_stock_change=-0.5)
    a = S.run_scenario(separate, spec([loss], horizon_months=1))
    b = S.run_scenario(embedded, spec([loss], horizon_months=1))
    assert a.terminal_net_worth_change == pytest.approx(
        b.terminal_net_worth_change)


def test_severance_and_benefits_arrive_only_in_specified_months():
    loss = event(
        "employment_loss", person_id="p1", duration_months=4,
        after_tax_income_loss_monthly=10_000,
        severance_after_tax=12_000, severance_month=2,
        unemployment_after_tax_monthly=1_500,
        benefit_start_month=3, benefit_duration_months=2,
    )
    result = S.run_scenario(baseline(), spec([loss], horizon_months=4))
    assert [row.explicit_inflows for row in result.monthly_path] == [0, 12_000, 0, 0]
    assert [row.after_tax_income for row in result.monthly_path] == [0, 0, 1_500, 1_500]


def test_terminal_recovery_does_not_hide_an_earlier_cash_failure():
    expense = event("one_time_expense", amount=70_000)
    receipt = event("cash_receipt", id="late-receipt", start_month=12,
                    after_tax_amount=100_000)
    result = S.run_scenario(baseline(), spec([expense, receipt]))
    assert result.monthly_path[-1].closing_cash > 0
    assert result.minimum_cash < 0
    assert not result.liquidity_passes


def test_current_and_essential_runway_remain_separate():
    result = S.run_scenario(baseline(), spec([]))
    current, essential = S.current_and_essential_runway(result)
    assert current == pytest.approx(50_000 / 6_000)
    assert essential == pytest.approx(50_000 / 4_500)


def test_cash_to_investment_transfer_changes_liquidity_not_net_worth():
    transfer = event("portfolio_contribution", amount=25_000)
    result = S.run_scenario(baseline(), spec([transfer], horizon_months=1))
    assert result.terminal_liquidity_change == pytest.approx(-25_000)
    assert result.terminal_net_worth_change == pytest.approx(0)


def test_home_down_payment_is_conversion_and_only_closing_cost_reduces_worth():
    home = event("home_purchase", purchase_price=300_000,
                 down_payment=60_000, closing_cost=6_000)
    result = S.run_scenario(baseline(), spec([home], horizon_months=1))
    assert result.terminal_liquidity_change == pytest.approx(-66_000)
    assert result.terminal_net_worth_change == pytest.approx(-6_000)


def test_unknown_income_loss_is_refused_and_optional_job_inputs_are_named():
    with pytest.raises(S.ScenarioError, match="after_tax_income_loss_monthly"):
        event("employment_loss", person_id="p1")
    raw = {"id": "job", "type": "employment_loss", "start_month": 1,
           "person_id": "p1", "after_tax_income_loss_monthly": 5000}
    parsed = S.ScenarioEvent.from_dict(raw, currency="USD")
    assert "severance_after_tax" in parsed.unknown_fields


def test_order_is_deterministic_and_ambiguous_flows_are_rejected():
    receipt = event("cash_receipt", after_tax_amount=20_000)
    spend = event("one_time_expense", amount=5_000)
    first = S.run_scenario(baseline(), spec([spend, receipt], horizon_months=1))
    second = S.run_scenario(baseline(), spec([receipt, spend], horizon_months=1))
    assert first.monthly_path == second.monthly_path
    contribution = event("portfolio_contribution", id="put", amount=1_000,
                         account_id="acct")
    withdrawal = event("portfolio_withdrawal", id="take", amount=1_000,
                       account_id="acct")
    with pytest.raises(S.ScenarioError, match="ambiguous"):
        spec([contribution, withdrawal])


def test_run_from_facts_does_not_mutate_baseline():
    data = F.load(ROOT / "inputs/facts.example.yml")
    original = copy.deepcopy(data)
    S.run_from_facts(data)
    assert data == original


def test_real_and_nominal_values_cannot_be_combined():
    with pytest.raises(S.ScenarioError, match="currency/basis"):
        S.run_scenario(baseline(), spec([], basis="real"))


def test_domain_adapters_match_emergency_retirement_and_housing_engines():
    data = F.load(ROOT / "inputs/facts.example.yml")
    base = S.baseline_from_facts(data)
    members = F._dig(data, "household.members") or []
    earners = [m for m in members if float(m.get("income_annual") or 0) > 0]
    expected_buffer = C.size_buffer(
        liquid=F.reserve_assets(data).included,
        annual_spending=float(F._dig(data, "household.annual_spending")),
        earners=len(earners), has_dependents=bool(F.dependents(data)),
        variable_comp_share=earners[0].get("income_variable_share"),
    )
    assert base.emergency_floor == expected_buffer.target
    home_spec = next(x for x in S.scenarios_from_facts(data)
                     if x.id == "inheritance-home")
    adapted = S.adapt_housing_events(data, home_spec)
    home = next(e for e in adapted.events if e.type == "home_purchase")
    owner = H.owner_cash_cost(F._dig(data, "housing.purchase"))
    assert home.down_payment == owner.down_payment
    result = S.run_scenario(base, replace(spec([], horizon_months=1),
                                          id="retirement-check",
                                          as_of=base.as_of))
    direct = R.assess_readiness(
        annual_spending=base.retirement_spending_annual,
        assets=result.monthly_path[-1].retirement
        + result.monthly_path[-1].marketable
        + result.monthly_path[-1].employer_stock,
        annual_savings=result.monthly_path[-1].retirement_contributions * 12,
        current_age=base.current_age + 1 / 12,
    )
    assert result.retirement_age_at_target == direct.age_at_target


def test_projection_metrics_use_the_shared_time_series_protocol():
    result = S.run_scenario(baseline(), spec([], horizon_months=2))
    assert result.metrics
    assert all(metric.clock == T.CLOCK_PROJECTION for metric in result.metrics)
    assert {metric.scenario for metric in result.metrics} == {"test-case"}
