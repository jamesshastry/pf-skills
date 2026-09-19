"""Reusable household cash-flow arithmetic. All figures are synthetic."""

import pytest

from pf import cashflow as C


def rules() -> C.TaxRules:
    return C.TaxRules(
        federal_standard_deduction=10_000,
        federal_brackets=((0.10, 20_000), (0.20, None)),
        state_anchor=C.StateTaxAnchor(
            reference_gross=100_000,
            reference_pre_tax_contributions=10_000,
            reference_tax=4_500,
            marginal_rate=0.05,
        ),
        payroll=C.PayrollTaxRules(
            state_payroll_rate=0.01,
            social_security_wage_base=80_000,
            social_security_rate=0.06,
            medicare_rate=0.015,
            additional_medicare_threshold=90_000,
            additional_medicare_rate=0.01,
        ),
    )


def uses() -> C.CashFlowInputs:
    return C.CashFlowInputs(
        pre_tax_retirement_contributions=10_000,
        employee_retirement_contributions=20_000,
        employer_retirement_contributions=5_000,
        ira_contributions=5_000,
        other_payroll_deductions=0,
        non_housing_spending=30_000,
        temporary_obligations=5_000,
        other_committed=0,
        annual_rent=12_000,
        redirected_savings_after_obligations=5_000,
    )


def test_income_cases_sum_named_components_and_reconcile_current():
    incomes = C.income_scenarios(
        {
            "current": {"salary": 80_000, "bonus": 10_000, "equity": 10_000},
            "conservative": {"salary": 80_000, "bonus": 5_000, "equity": 0},
        },
        recorded_current=100_000,
    )
    assert incomes == {"current": 100_000, "conservative": 85_000}


def test_current_tax_and_cash_flow_reconcile_by_hand():
    result = C.build_cash_flow_scenarios(
        {"current": 100_000}, tax_rules=rules(), cash=uses())["current"]

    assert result.taxes.federal_income_tax == 14_000
    assert result.taxes.state_income_tax == 4_500
    assert result.taxes.state_payroll_tax == 1_000
    assert result.taxes.federal_payroll_tax == 6_400
    assert result.taxes.total == 25_900
    assert result.after_tax_cash_income == 74_100
    assert result.cash_after_payroll_and_employee_retirement == 54_100
    assert result.pre_housing_surplus == 14_100
    assert result.renter_taxable_savings == 2_100
    assert result.total_savings_during_obligations == 32_100
    assert result.total_savings_after_obligations == 37_100


def test_rent_is_subtracted_exactly_once():
    low = C.build_cash_flow_scenarios(
        {"current": 100_000}, tax_rules=rules(), cash=uses())["current"]
    high_rent = C.CashFlowInputs(**{
        **vars(uses()),
        "annual_rent": 18_000,
    })
    high = C.build_cash_flow_scenarios(
        {"current": 100_000}, tax_rules=rules(), cash=high_rent)["current"]

    assert high.pre_housing_surplus == low.pre_housing_surplus
    assert high.renter_taxable_savings == low.renter_taxable_savings - 6_000


def test_progressive_tax_uses_each_bracket_once():
    assert C.progressive_tax(
        40_000, ((0.10, 10_000), (0.20, 30_000), (0.30, None))) == 8_000


def test_zero_income_has_zero_effective_and_savings_rates():
    zero_uses = C.CashFlowInputs(**{
        name: 0 for name in vars(uses())
    })
    result = C.build_cash_flow_scenarios(
        {"no_income": 0}, tax_rules=rules(), cash=zero_uses)["no_income"]

    assert result.taxes.effective_rate == 0.0
    assert result.savings_rate_during_obligations == 0.0
    assert result.savings_rate_after_obligations == 0.0


def test_unknown_or_contradictory_inputs_are_refused():
    with pytest.raises(C.CashFlowError, match="unknown"):
        C.income_scenarios({"current": {"salary": 100_000, "bonus": None}})
    with pytest.raises(C.CashFlowError, match="disagrees"):
        C.income_scenarios(
            {"current": {"salary": 100_000}}, recorded_current=90_000)
    with pytest.raises(C.CashFlowError, match="open-ended"):
        C.TaxRules(
            federal_standard_deduction=10_000,
            federal_brackets=((0.10, 20_000),),
            state_anchor=rules().state_anchor,
            payroll=rules().payroll,
        )
    with pytest.raises(C.CashFlowError, match="exceed total"):
        C.CashFlowInputs(**{
            **vars(uses()),
            "pre_tax_retirement_contributions": 25_000,
        })
    with pytest.raises(C.CashFlowError, match="unknown is not zero"):
        C.CashFlowInputs(**{
            **vars(uses()),
            "annual_rent": None,
        })
