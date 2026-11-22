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


# ── Itemized deductions (synthetic figures) ────────────────────────────

def itemized_rules(**overrides) -> C.TaxRules:
    base = rules()
    item = C.ItemizedDeductionRules(
        salt_cap=8_000,
        medical_agi_floor=0.10,
        mortgage_interest_debt_limit=200_000,
        **overrides,
    )
    return C.TaxRules(
        federal_standard_deduction=base.federal_standard_deduction,
        federal_brackets=base.federal_brackets,
        state_anchor=base.state_anchor,
        payroll=base.payroll,
        itemized=item,
    )


def test_without_itemized_inputs_the_estimate_is_unchanged():
    plain = C.estimate_tax(100_000, pre_tax_contributions=10_000, rules=rules())
    with_rules = C.estimate_tax(
        100_000, pre_tax_contributions=10_000, rules=itemized_rules())
    assert with_rules == plain
    assert plain.deduction == 10_000 and not plain.itemizes


def test_itemized_total_applies_cap_floor_and_debt_limit_by_hand():
    # AGI 90,000; state income 4,500; state payroll 1,000.
    est = C.estimate_tax(
        100_000,
        pre_tax_contributions=10_000,
        rules=itemized_rules(),
        itemized_inputs=C.ItemizedDeductionInputs(
            medical_expenses=12_000,      # 12,000 - 9,000 floor = 3,000
            property_tax=5_000,           # 4,500 + 1,000 + 5,000 -> capped 8,000
            mortgage_interest=12_000,     # 300,000 balance > 200,000 -> 8,000
            mortgage_balance=300_000,
            charitable=500,
        ),
    )
    assert est.itemized_deduction == pytest.approx(8_000 + 3_000 + 8_000 + 500)
    assert est.itemizes and est.deduction == pytest.approx(19_500)
    assert est.taxable_income == pytest.approx(90_000 - 19_500)
    assert est.federal_income_tax == pytest.approx(2_000 + 0.20 * 50_500)


def test_standard_deduction_wins_when_larger():
    est = C.estimate_tax(
        100_000, pre_tax_contributions=10_000, rules=itemized_rules(),
        itemized_inputs=C.ItemizedDeductionInputs(charitable=100))
    # SALT 5,500 + charity 100 < 10,000 standard.
    assert est.itemized_deduction == pytest.approx(5_600)
    assert est.deduction == 10_000 and not est.itemizes


def test_salt_cap_phases_down_with_agi_to_its_floor():
    r = C.ItemizedDeductionRules(
        salt_cap=8_000, medical_agi_floor=0.10,
        mortgage_interest_debt_limit=200_000,
        salt_phaseout_threshold=50_000, salt_phaseout_rate=0.30,
        salt_cap_floor=2_000)
    assert r.effective_salt_cap(50_000) == 8_000
    assert r.effective_salt_cap(60_000) == pytest.approx(5_000)
    assert r.effective_salt_cap(100_000) == 2_000


def test_agi_adjustment_moves_federal_and_state_but_not_payroll():
    base = C.estimate_tax(100_000, pre_tax_contributions=10_000, rules=rules())
    loss = C.estimate_tax(100_000, pre_tax_contributions=10_000, rules=rules(),
                          agi_adjustments=-20_000)
    assert loss.adjusted_gross_income == pytest.approx(70_000)
    assert base.state_income_tax - loss.state_income_tax == pytest.approx(1_000)
    assert base.federal_income_tax - loss.federal_income_tax == pytest.approx(4_000)
    assert loss.state_payroll_tax == base.state_payroll_tax
    assert loss.federal_payroll_tax == base.federal_payroll_tax


def test_agi_adjustment_lowers_the_medical_floor():
    inputs = C.ItemizedDeductionInputs(medical_expenses=12_000, property_tax=5_000)
    hi = C.estimate_tax(100_000, pre_tax_contributions=10_000,
                        rules=itemized_rules(), itemized_inputs=inputs)
    lo = C.estimate_tax(100_000, pre_tax_contributions=10_000,
                        rules=itemized_rules(), itemized_inputs=inputs,
                        agi_adjustments=-20_000)
    # Floor falls by 10% of 20,000 = 2,000; SALT stays at the 8,000 cap.
    assert lo.itemized_deduction - hi.itemized_deduction == pytest.approx(2_000)


def test_scenarios_pass_itemized_inputs_and_adjustments_through():
    inputs = C.ItemizedDeductionInputs(medical_expenses=12_000, property_tax=5_000)
    out = C.build_cash_flow_scenarios(
        {"a": 100_000}, tax_rules=itemized_rules(), cash=uses(),
        itemized_inputs=inputs, agi_adjustments=-5_000)
    direct = C.estimate_tax(100_000, pre_tax_contributions=10_000,
                            rules=itemized_rules(), itemized_inputs=inputs,
                            agi_adjustments=-5_000)
    assert out["a"].taxes == direct


@pytest.mark.parametrize("kwargs, message", [
    ({"salt_cap": -1}, "SALT cap"),
    ({"medical_agi_floor": 1.5}, "medical AGI floor"),
    ({"salt_cap_floor": 9_000}, "floor exceeds"),
])
def test_invalid_itemized_rules_are_refused(kwargs, message):
    params = dict(salt_cap=8_000, medical_agi_floor=0.10,
                  mortgage_interest_debt_limit=200_000)
    params.update(kwargs)
    with pytest.raises(C.CashFlowError, match=message):
        C.ItemizedDeductionRules(**params)


def test_negative_itemized_inputs_are_refused():
    with pytest.raises(C.CashFlowError):
        C.ItemizedDeductionInputs(medical_expenses=-1)


# ── State itemized deductions (synthetic figures) ──────────────────────

def state_rules(**overrides) -> C.TaxRules:
    base = itemized_rules()
    st = dict(standard_deduction=3_000, medical_agi_floor=0.10,
              mortgage_interest_debt_limit=250_000)
    st.update(overrides)
    return C.TaxRules(
        federal_standard_deduction=base.federal_standard_deduction,
        federal_brackets=base.federal_brackets,
        state_anchor=base.state_anchor,
        payroll=base.payroll,
        itemized=base.itemized,
        state_itemized=C.StateItemizedDeductionRules(**st),
    )


def test_state_itemizing_lowers_state_tax_at_the_marginal_rate_by_hand():
    inputs = C.ItemizedDeductionInputs(
        medical_expenses=12_000,     # 12,000 - 9,000 = 3,000
        property_tax=5_000,          # uncapped at state level
        mortgage_interest=12_000,    # 300,000 > 250,000 -> 10,000
        mortgage_balance=300_000)
    est = C.estimate_tax(100_000, pre_tax_contributions=10_000,
                         rules=state_rules(), itemized_inputs=inputs)
    assert est.state_itemized_deduction == pytest.approx(18_000)
    assert est.state_itemizes and est.state_deduction == pytest.approx(18_000)
    # Anchor 4,500 at AGI 90,000; 15,000 above the state standard x 5%.
    assert est.state_income_tax == pytest.approx(4_500 - 750)


def test_state_itemizing_feeds_the_federal_salt_total():
    inputs = C.ItemizedDeductionInputs(property_tax=1_000, medical_expenses=15_000)
    est = C.estimate_tax(100_000, pre_tax_contributions=10_000,
                         rules=state_rules(), itemized_inputs=inputs)
    # State itemized 1,000 + 6,000 = 7,000 -> 4,000 over standard -> -200.
    assert est.state_income_tax == pytest.approx(4_300)
    # Federal SALT = 4,300 + 1,000 payroll + 1,000 property = 6,300 (< 8,000 cap).
    assert est.itemized_deduction == pytest.approx(6_300 + 6_000)


def test_state_standard_deduction_wins_when_larger():
    inputs = C.ItemizedDeductionInputs(medical_expenses=10_000)
    est = C.estimate_tax(100_000, pre_tax_contributions=10_000,
                         rules=state_rules(), itemized_inputs=inputs)
    assert est.state_itemized_deduction == pytest.approx(1_000)
    assert not est.state_itemizes and est.state_deduction == 3_000
    assert est.state_income_tax == pytest.approx(4_500)


def test_state_phaseout_and_cap_options():
    inputs = C.ItemizedDeductionInputs(property_tax=20_000)
    capped = C.estimate_tax(100_000, pre_tax_contributions=10_000,
                            rules=state_rules(salt_cap=6_000),
                            itemized_inputs=inputs)
    assert capped.state_itemized_deduction == pytest.approx(6_000)
    phased = C.estimate_tax(100_000, pre_tax_contributions=10_000,
                            rules=state_rules(phaseout_threshold=80_000,
                                              phaseout_rate=0.06,
                                              phaseout_max_share=0.80),
                            itemized_inputs=inputs)
    # Excess AGI 10,000 x 6% = 600 reduction.
    assert phased.state_itemized_deduction == pytest.approx(19_400)


def test_without_state_rules_state_tax_is_unchanged():
    inputs = C.ItemizedDeductionInputs(property_tax=5_000, medical_expenses=12_000)
    a = C.estimate_tax(100_000, pre_tax_contributions=10_000,
                       rules=itemized_rules(), itemized_inputs=inputs)
    assert a.state_income_tax == pytest.approx(4_500)
    assert a.state_itemized_deduction == 0 and not a.state_itemizes


def test_invalid_state_itemized_rules_are_refused():
    with pytest.raises(C.CashFlowError, match="state medical AGI floor"):
        C.StateItemizedDeductionRules(standard_deduction=1, medical_agi_floor=2,
                                      mortgage_interest_debt_limit=1)


# ── 2026+ federal rules (P.L. 119-21) ─────────────────────────────────────

def test_charitable_floor_counts_only_gifts_above_half_a_percent_of_agi():
    # AGI 90,000 -> floor 450; charity 2,450 -> 2,000 counted.
    est = C.estimate_tax(
        100_000, pre_tax_contributions=10_000,
        rules=itemized_rules(charitable_agi_floor=0.005),
        itemized_inputs=C.ItemizedDeductionInputs(property_tax=5_000,
                                                  charitable=2_450))
    assert est.itemized_deduction == pytest.approx(8_000 + 2_000)


def test_non_itemizer_still_deducts_charity_up_to_the_limit():
    est = C.estimate_tax(
        100_000, pre_tax_contributions=10_000,
        rules=itemized_rules(nonitemizer_charitable_limit=1_000),
        itemized_inputs=C.ItemizedDeductionInputs(charitable=1_500))
    # Itemized 5,500 + 1,500 = 7,000 < 10,000 standard; +1,000 above the line.
    assert not est.itemizes
    assert est.deduction == pytest.approx(11_000)
    assert est.taxable_income == pytest.approx(90_000 - 11_000)


def test_top_bracket_limitation_trims_itemized_by_hand():
    # AGI 90,000, threshold 80,000 -> 10,000 over; itemized 19,500.
    # Reduction 2/37 x min(19,500, 10,000) = 540.54.
    est = C.estimate_tax(
        100_000, pre_tax_contributions=10_000,
        rules=itemized_rules(limitation_rate=2 / 37, limitation_threshold=80_000),
        itemized_inputs=C.ItemizedDeductionInputs(
            medical_expenses=12_000, property_tax=5_000,
            mortgage_interest=12_000, mortgage_balance=300_000, charitable=500))
    assert est.itemized_deduction == pytest.approx(19_500 - 2 / 37 * 10_000)


def test_limitation_rate_without_threshold_is_refused():
    with pytest.raises(C.CashFlowError, match="threshold"):
        C.ItemizedDeductionRules(salt_cap=1, medical_agi_floor=0.075,
                                 mortgage_interest_debt_limit=1,
                                 limitation_rate=2 / 37)


def test_mortgage_interest_without_a_balance_is_refused():
    with pytest.raises(C.CashFlowError, match="balance"):
        C.ItemizedDeductionInputs(mortgage_interest=10_000)
    assert C.ItemizedDeductionInputs().mortgage_balance is None


def test_state_phaseout_share_cap_excludes_medical():
    # AGI 90,000; state medical floor 9,000 -> 21,000 - 9,000 = 12,000 medical.
    # Property 1,000. Share cap 0.80 x (13,000 - 12,000) = 800 binds
    # below the 10,000 x 50% = 5,000 rate reduction.
    est = C.estimate_tax(
        100_000, pre_tax_contributions=10_000,
        rules=state_rules(phaseout_threshold=80_000, phaseout_rate=0.50,
                          phaseout_max_share=0.80),
        itemized_inputs=C.ItemizedDeductionInputs(property_tax=1_000,
                                                  medical_expenses=21_000))
    assert est.state_itemized_deduction == pytest.approx(13_000 - 800)
