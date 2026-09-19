"""Reusable household cash-flow arithmetic. All figures are synthetic."""

from copy import deepcopy

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


def complete_uses() -> C.CashFlowInputs:
    return C.CashFlowInputs(
        pre_tax_retirement_contributions=10_000,
        employee_retirement_contributions=20_000,
        employer_retirement_contributions=5_000,
        ira_contributions=5_000,
        other_payroll_deductions=2_000,
        non_housing_spending=20_000,
        temporary_obligations=3_000,
        other_committed=4_000,
        annual_rent=12_000,
        redirected_savings_after_obligations=2_000,
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


def test_cash_flow_conservation_with_every_cash_use_present():
    cash = complete_uses()
    result = C.build_cash_flow_scenarios(
        {"current": 100_000}, tax_rules=rules(), cash=cash)["current"]

    expected_taxable_saving = (
        result.gross
        - result.taxes.total
        - cash.employee_retirement_contributions
        - cash.other_payroll_deductions
        - cash.non_housing_spending
        - cash.temporary_obligations
        - cash.ira_contributions
        - cash.other_committed
        - cash.annual_rent
    )
    assert result.renter_taxable_savings == expected_taxable_saving
    assert result.total_savings_during_obligations == (
        cash.employee_retirement_contributions
        + cash.employer_retirement_contributions
        + cash.ira_contributions
        + result.renter_taxable_savings
    )
    assert result.total_savings_after_obligations == (
        result.total_savings_during_obligations
        + cash.redirected_savings_after_obligations
    )


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


def test_state_anchor_moves_up_and_down_at_supplied_marginal_rate():
    higher = C.estimate_tax(
        110_000, pre_tax_contributions=10_000, rules=rules())
    lower = C.estimate_tax(
        90_000, pre_tax_contributions=10_000, rules=rules())

    assert higher.state_income_tax == 5_000
    assert lower.state_income_tax == 4_000


def test_low_income_floors_state_and_federal_tax_at_zero():
    low_income_rules = C.TaxRules(
        federal_standard_deduction=10_000,
        federal_brackets=((0.10, 20_000), (0.20, None)),
        state_anchor=C.StateTaxAnchor(
            reference_gross=100_000,
            reference_pre_tax_contributions=0,
            reference_tax=1_000,
            marginal_rate=0.05,
        ),
        payroll=rules().payroll,
    )
    estimate = C.estimate_tax(
        5_000, pre_tax_contributions=0, rules=low_income_rules)

    assert estimate.taxable_income == 0
    assert estimate.federal_income_tax == 0
    assert estimate.state_income_tax == 0


def test_progressive_tax_floors_negative_taxable_income_at_zero():
    assert C.progressive_tax(-1, ((0.10, None),)) == 0


def test_zero_income_has_zero_effective_and_savings_rates():
    zero_uses = C.CashFlowInputs(**{
        name: 0 for name in vars(uses())
    })
    result = C.build_cash_flow_scenarios(
        {"no_income": 0}, tax_rules=rules(), cash=zero_uses)["no_income"]

    assert result.taxes.effective_rate == 0.0
    assert result.savings_rate_during_obligations == 0.0
    assert result.savings_rate_after_obligations == 0.0


def test_non_finite_inputs_are_refused():
    with pytest.raises(C.CashFlowError, match="current salary must be finite"):
        C.income_scenarios({"current": {"salary": float("nan")}})
    with pytest.raises(C.CashFlowError, match="annual rent must be finite"):
        C.CashFlowInputs(**{
            **vars(uses()),
            "annual_rent": float("inf"),
        })
    with pytest.raises(C.CashFlowError, match="upper bound must be finite"):
        C.validate_brackets(((0.10, float("nan")), (0.20, None)))
    with pytest.raises(C.CashFlowError, match="taxable income must be finite"):
        C.progressive_tax(float("-inf"), ((0.10, None),))
    with pytest.raises(C.CashFlowError, match="rate must be finite"):
        C.PayrollTaxRules(
            state_payroll_rate=float("nan"),
            social_security_wage_base=80_000,
            social_security_rate=0.06,
            medicare_rate=0.015,
            additional_medicare_threshold=90_000,
            additional_medicare_rate=0.01,
        )


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


def test_missing_or_empty_income_scenarios_are_refused():
    with pytest.raises(C.CashFlowError, match="scenarios are missing"):
        C.income_scenarios({})
    with pytest.raises(C.CashFlowError, match="components are missing"):
        C.income_scenarios({"current": {}})
    with pytest.raises(C.CashFlowError, match="scenario 'current' is missing"):
        C.income_scenarios(
            {"alternate": {"salary": 1}}, recorded_current=1)
    with pytest.raises(C.CashFlowError, match="scenarios are missing"):
        C.build_cash_flow_scenarios({}, tax_rules=rules(), cash=uses())


def test_negative_income_and_cash_uses_are_refused():
    with pytest.raises(C.CashFlowError, match="cannot be negative"):
        C.income_scenarios({"current": {"salary": -1}})
    with pytest.raises(C.CashFlowError, match="cannot be negative"):
        C.CashFlowInputs(**{
            **vars(uses()),
            "other_committed": -1,
        })


def test_contribution_constraints_are_refused():
    with pytest.raises(C.CashFlowError, match="exceed gross income"):
        C.estimate_tax(
            5_000, pre_tax_contributions=6_000, rules=rules())
    with pytest.raises(C.CashFlowError, match="exceed total"):
        C.CashFlowInputs(**{
            **vars(uses()),
            "pre_tax_retirement_contributions": 21_000,
        })
    with pytest.raises(C.CashFlowError, match="exceed the obligations"):
        C.CashFlowInputs(**{
            **vars(uses()),
            "redirected_savings_after_obligations": 6_000,
        })


@pytest.mark.parametrize("invalid_rate", [-0.01, 1.01])
def test_rates_outside_zero_to_one_are_refused(invalid_rate):
    with pytest.raises(C.CashFlowError, match="between zero and one"):
        C.PayrollTaxRules(
            state_payroll_rate=invalid_rate,
            social_security_wage_base=80_000,
            social_security_rate=0.06,
            medicare_rate=0.015,
            additional_medicare_threshold=90_000,
            additional_medicare_rate=0.01,
        )


@pytest.mark.parametrize(
    ("brackets", "message"),
    [
        (((0.10, 10_000), (0.10, None)), "rates must be increasing"),
        (
            ((0.10, 10_000), (0.20, 10_000), (0.30, None)),
            "bounds must be strictly increasing",
        ),
        (((0.10, None), (0.20, None)), "only the final"),
        (((0.10, 10_000), (0.20, 20_000)), "open-ended final"),
    ],
)
def test_invalid_bracket_structures_are_refused(brackets, message):
    with pytest.raises(C.CashFlowError, match=message):
        C.validate_brackets(brackets)


def test_public_functions_do_not_mutate_input_mappings():
    component_inputs = {
        "current": {"salary": 80_000, "bonus": 20_000},
        "conservative": {"salary": 80_000, "bonus": 0},
    }
    gross_inputs = {"current": 100_000, "conservative": 80_000}
    components_before = deepcopy(component_inputs)
    gross_before = deepcopy(gross_inputs)

    C.income_scenarios(component_inputs, recorded_current=100_000)
    C.build_cash_flow_scenarios(
        gross_inputs, tax_rules=rules(), cash=uses())

    assert component_inputs == components_before
    assert gross_inputs == gross_before
