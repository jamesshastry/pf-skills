"""Housing affordability and transitions. All figures are synthetic."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from pf import facts as F, housing as H  # noqa: E402
from pf import housing_affordability as A, realestate as R  # noqa: E402


PURCHASE = {
    "price": 200_000,
    "down_payment_rate": 0.20,
    "closing_cost_rate": 0.02,
    "mortgage_rate": 0.06,
    "term_years": 30,
    "property_tax_rate": 0.01,
    "insurance_annual": 1_200,
    "maintenance_rate": 0.01,
    "hoa_monthly": 100,
    "pmi_rate": 0.0,
}


def scenario(label="Current", kind="current", **overrides):
    raw = {
        "label": label,
        "kind": kind,
        "income_components": {"salary": 80_000, "bonus": 12_000,
                              "equity": 8_000},
        "gross_income_annual": 100_000,
        "taxes_annual": 20_000,
        "after_tax_cash_income_annual": 80_000,
        "retirement_contributions_annual": 10_000,
        "employer_retirement_contributions_annual": 0,
        "ira_contributions_annual": 2_000,
        "other_payroll_deductions_annual": 2_000,
        "non_housing_spending_annual": 30_000,
        "other_committed_annual": 3_000,
        "minimum_savings": {"annual_amount": 5_000,
                            "gross_income_rate": 0.10},
        "obligations": [{"label": "education", "annual_amount": 6_000,
                         "start_month": 1, "end_month": 24}],
    }
    raw.update(overrides)
    return raw


def conservative(**overrides):
    raw = scenario("Conservative employed", "conservative")
    raw.update({
        "income_components": {"salary": 80_000},
        "gross_income_annual": 80_000,
        "taxes_annual": 16_000,
        "after_tax_cash_income_annual": 64_000,
        "retirement_contributions_annual": 8_000,
        "employer_retirement_contributions_annual": 0,
        "ira_contributions_annual": 1_000,
    })
    raw.update(overrides)
    return raw


def classified(cash=200_000, marketable=0):
    return F.ClassifiedAssets(
        included=cash,
        excluded=marketable,
        rows=[] if not marketable else [("brokerage", marketable)],
        by_class={"cash_equivalent": cash, "marketable": marketable},
    )


def assess(*, rent=1_000, current=None, stress=None, cash=200_000,
           purchase=None, affordability=None):
    return A.assess(
        scenarios=[current or scenario(), stress or conservative()],
        purchase=purchase or PURCHASE,
        monthly_rent=rent,
        balance_sheet=[{"name": "cash", "value": cash,
                        "liquidity_class": "cash_equivalent"}],
        reserve_assets=classified(cash),
        retirement_annual_savings=12_000,
        household_income=100_000,
        household_income_components={"salary": 80_000, "bonus": 12_000,
                                     "equity": 8_000},
        affordability=affordability or {
            "target_price": 200_000,
            "candidate_prices": [150_000, 200_000],
            "post_close_reserve_months": 3,
            "lender": {"maximum_housing_dti": 0.30,
                       "other_debt_annual": 0},
        },
    )


def test_hand_calculated_scenario_and_savings_invariant():
    """80,000 after tax - 10,000 retirement - 2,000 IRA - 2,000
    payroll - 30,000 non-housing - 6,000 education - 3,000 other =
    27,000 pre-housing. With 12,000 rent, renter savings is 15,000.
    Both valid owner formulations must land on the same number.
    """
    s = A.reconcile_scenario(scenario(), retirement_annual_savings=12_000)
    assert s.pre_housing_surplus == 27_000
    assert s.minimum_savings == 10_000  # greater of dollars and 10% of gross
    ledger = A.savings_ledger(
        s, owner_cash_cost_annual=18_000, annual_rent=12_000)
    assert ledger.renter_taxable_savings == 15_000
    assert ledger.owner_taxable_savings == 9_000
    assert ledger.owner_via_incremental_bridge == 9_000
    assert ledger.invariant_holds


def test_time_varying_obligation_stops_in_the_correct_phase():
    s = A.reconcile_scenario(scenario(obligations=[
        {"label": "education", "annual_amount": 6_000,
         "start_month": 1, "end_month": 12},
    ]))
    assert A.pre_housing_cash_for_period(s, start_month=1, months=12) == 27_000
    assert A.pre_housing_cash_for_period(s, start_month=13, months=12) == 33_000


def test_pre_housing_api_rejects_a_second_housing_line():
    with pytest.raises(A.ReconciliationError, match="housing belongs"):
        A.reconcile_scenario(scenario(rent_annual=12_000))


def test_principal_is_cash_for_affordability_but_equity_in_economic_cost():
    cash = A.owner_cash_cost(PURCHASE)
    economic = H.cost_of_owning(
        {"price": 200_000, "down_payment": 40_000,
         "mortgage_rate": 0.06, "term_years": 30,
         "property_tax_rate": 0.01, "insurance_annual": 1_200,
         "maintenance_rate": 0.01, "hoa_monthly": 100},
        1, investment_return=0.0, appreciation=0.0)
    assert cash.principal > 0
    assert cash.principal_and_interest == pytest.approx(
        cash.interest + cash.principal)
    assert economic["total"] == pytest.approx(
        economic["outflows_fv"] - economic["terminal_equity"])


def test_fixed_and_rate_down_payments_must_reconcile_at_the_target():
    with pytest.raises(A.ReconciliationError, match="down_payment disagrees"):
        A.owner_cash_cost({**PURCHASE, "down_payment": 10_000})


def test_current_and_conservative_have_separate_limits():
    result = assess()
    assert result.current_income_ceiling > result.stress_tested_ceiling
    assert [(label, kind) for label, kind, _ in result.scenario_cash_flow_limits] == [
        ("Current", "current"), ("Conservative employed", "conservative")]
    assert result.lender_maximum is not None
    assert result.binding_constraint


def test_most_constraining_conservative_case_controls_not_lowest_surplus():
    high_floor = scenario(
        "High savings commitment", "conservative",
        minimum_savings={"annual_amount": 30_000})
    result = A.assess(
        scenarios=[scenario(), conservative(), high_floor],
        purchase=PURCHASE, monthly_rent=1_000,
        balance_sheet=[{"name": "cash", "value": 500_000,
                        "liquidity_class": "cash_equivalent"}],
        reserve_assets=classified(500_000),
        retirement_annual_savings=12_000,
        household_income=100_000,
        household_income_components={"salary": 80_000, "bonus": 12_000,
                                     "equity": 8_000},
        affordability={"target_price": 100_000,
                       "post_close_reserve_months": 1},
    )
    assert high_floor["income_components"] == scenario()["income_components"]
    assert result.stress_scenario == "High savings commitment"


def test_candidate_fails_when_only_the_lender_limit_is_breached():
    result = assess(
        cash=500_000,
        affordability={
            "target_price": 100_000,
            "post_close_reserve_months": 1,
            "lender": {"maximum_housing_dti": 0.05,
                       "other_debt_annual": 0},
        })
    row = next(c for c in result.candidates if c.scenario == "Current")
    assert row.feasible_cash_flow
    assert row.feasible_liquidity
    assert not row.feasible_lender


def test_higher_rent_changes_renter_savings_not_affordability_capacity():
    low = assess(rent=1_000)
    high = assess(rent=3_000)
    assert high.current_income_ceiling == pytest.approx(
        low.current_income_ceiling, abs=1)
    low_row = next(c for c in low.candidates if c.scenario == "Current"
                   and c.price == 200_000)
    high_row = next(c for c in high.candidates if c.scenario == "Current"
                    and c.price == 200_000)
    assert high_row.savings.renter_taxable_savings == (
        low_row.savings.renter_taxable_savings - 24_000)
    assert high_row.savings.pre_housing_surplus == low_row.savings.pre_housing_surplus


@pytest.mark.parametrize("change, message", [
    ({"gross_income_annual": 120_000}, "gross income"),
    ({"after_tax_cash_income_annual": 70_000}, "after-tax cash income"),
    ({"retirement_contributions_annual": 8_000}, "retirement cash-flow"),
])
def test_conflicting_cash_flow_facts_are_blockers(change, message):
    with pytest.raises(A.ReconciliationError, match=message):
        A.reconcile_scenario(
            scenario(**change),
            household_income=100_000,
            retirement_annual_savings=12_000,
        )


def test_component_drift_is_a_blocker_even_when_the_total_matches():
    with pytest.raises(A.ReconciliationError, match="components disagree"):
        A.reconcile_scenario(
            scenario(),
            household_income=100_000,
            household_income_components={"salary": 90_000, "bonus": 2_000,
                                         "equity": 8_000},
        )


def test_taxes_are_not_silently_approximated():
    raw = scenario()
    del raw["taxes_annual"]
    del raw["after_tax_cash_income_annual"]
    with pytest.raises(A.ReconciliationError, match="will not be approximated"):
        A.reconcile_scenario(raw)


def test_null_component_or_obligation_is_not_silently_zero():
    with pytest.raises(A.ReconciliationError, match="components are unknown"):
        A.reconcile_scenario(
            scenario(income_components={"salary": 100_000, "bonus": None}))
    with pytest.raises(A.ReconciliationError, match="unknown annual_amount"):
        A.reconcile_scenario(
            scenario(obligations=[{"label": "education",
                                   "annual_amount": None}]))


def test_partial_tax_benefit_is_refused():
    with pytest.raises(A.ReconciliationError, match="tax benefit is partial"):
        A.incremental_tax_benefit({"filing_status": "single"})


def test_complete_tax_benefit_compares_owner_to_renter_baseline():
    benefit = A.incremental_tax_benefit({
        "filing_status": "single", "itemizes_owner": True,
        "standard_deduction_annual": 15_000,
        "renter_itemized_deductions_annual": 12_000,
        "owner_deductible_housing_annual": 10_000,
        "deduction_cap_annual": 8_000,
        "marginal_tax_rate": 0.25,
        "modeled_price": 200_000,
    })
    # Renter takes 15,000 standard; owner itemizes 12,000 + capped 8,000.
    assert benefit.incremental_annual == 1_250


def test_taxable_liquidation_is_asset_conversion_not_income():
    sale = A.liquidate_taxable(
        {"account_name": "brokerage", "securities_sold": ["GAIN", "LOSS"],
         "loss_carryforward": 500, "margin_debt_payoff": 2_000,
         "federal_tax_rate": 0.20, "state_tax_rate": 0.05,
         "wash_sale_reviewed": True},
        opening_assets=150_000,
        opening_securities=50_000,
        tax_lots=[
            {"ticker": "GAIN", "value": 20_000, "cost_basis": 12_000,
             "holding_period": "long_term"},
            {"ticker": "LOSS", "value": 10_000, "cost_basis": 13_000,
             "holding_period": "long_term"},
        ],
    )
    assert sale.gross_sale_proceeds == 30_000
    assert sale.cost_basis == 25_000
    assert sale.taxable_gain == 4_500
    assert sale.spendable_proceeds == 30_000 - 2_000 - 1_125
    assert sale.net_worth_change == -1_125


def test_liquidation_refuses_missing_basis_or_mixed_holding_periods():
    raw = {"account_name": "brokerage", "securities_sold": ["A"],
           "loss_carryforward": 0, "margin_debt_payoff": 0,
           "federal_tax_rate": 0.2, "state_tax_rate": 0,
           "wash_sale_reviewed": True}
    with pytest.raises(A.ReconciliationError, match="cost_basis"):
        A.liquidate_taxable(
            raw, opening_assets=10_000, opening_securities=10_000,
            tax_lots=[{"ticker": "A", "value": 10_000,
                       "holding_period": "long_term"}])


def test_reserves_count_cash_but_not_marketable_securities_at_par():
    facts = {"household": {"balance_sheet": [
        {"name": "cash", "value": 20_000,
         "liquidity_class": "cash_equivalent"},
        {"name": "stock", "value": 80_000,
         "liquidity_class": "marketable"},
    ]}}
    reserve = F.reserve_assets(facts)
    assert reserve.included == 20_000
    assert reserve.excluded == 80_000
    assert reserve.rows == [("stock", 80_000)]
    assert reserve.by_class == {"cash_equivalent": 20_000,
                                "marketable": 80_000}


def test_rent_first_liquidity_uses_investment_not_owner_down_payment():
    result = A.assess(
        scenarios=[scenario(), conservative()],
        purchase=PURCHASE,
        monthly_rent=1_000,
        balance_sheet=[{"name": "cash", "value": 200_000,
                        "liquidity_class": "cash_equivalent"}],
        reserve_assets=classified(200_000),
        retirement_annual_savings=12_000,
        household_income=100_000,
        household_income_components={"salary": 80_000, "bonus": 12_000,
                                     "equity": 8_000},
        affordability={"target_price": 200_000,
                       "post_close_reserve_months": 3},
        transition={"kind": "rental_then_owner",
                    "rental_deal_label": "home",
                    "investment_lender_test": "dscr"},
        rental_deals=[{**DEAL, "label": "home"}],
    )
    row = next(c for c in result.candidates if c.scenario == "Current")
    assert row.owner.down_payment == 40_000
    assert row.initial_down_payment == 50_000
    assert row.initial_closing_costs == 5_000
    assert result.investment_lender_maximum is not None


DEAL = {
    "price": 200_000, "down_payment": 50_000, "closing_costs": 5_000,
    "loan_rate": 0.065,
    "loan_term_years": 30, "gross_rent_monthly": 2_100,
    "vacancy_rate": 0.05, "credit_loss_rate": 0.01,
    "capex_reserve_rate": 0.05,
    "operating_expenses": {
        "property_tax": 2_400, "landlord_insurance": 1_200,
        "management": 1_800, "leasing_turnover": 600,
        "maintenance": 1_500, "hoa": 1_200,
    },
}


def rental_plan(**overrides):
    plan = {
        "kind": "rental_then_owner", "analysis_months": 30,
        "tenant_months": 15, "occupancy_conversion_date": "2028-01-01",
        "financing_occupancy": "investment",
        "investment_lender_test": "dscr",
        "loan_occupancy_requirement_months": None,
        "refinance_at_occupancy": True,
        "refinance_cost": 2_500,
        "owner_operating_cost_growth_rate": 0.03,
    }
    plan.update(overrides)
    return plan


def shut_gate():
    return R.ActivityGate(
        label="home", avg_stay_days=365, is_rental_activity=True,
        materially_participates=False, door=None, expected_loss=10_000,
        suspended_carryforward=0, deductible_against_wages=0,
        suspended_this_year=10_000)


def test_tenant_phase_has_current_rent_and_property_carry():
    t = A.build_transition(
        rental_plan(), purchase=PURCHASE, monthly_current_rent=1_500,
        rental_deal=DEAL, rental_gate=shut_gate())
    tenant, owner = t.phases
    assert tenant.current_home_rent == 1_500 * 15
    assert tenant.tenant_gross_rent == 2_100 * 15
    assert tenant.debt_service > 0
    assert tenant.management > 0 and tenant.capital_reserve > 0
    assert owner.current_home_rent == 0
    assert owner.tenant_gross_rent == 0
    assert owner.debt_service > 0
    assert sum(p.months for p in t.phases) == 30
    assert 0 < t.owner_phase_loan < t.initial_loan
    assert t.owner_phase_loan != PURCHASE["price"] * (
        1 - PURCHASE["down_payment_rate"])
    checks = A.phase_cash_checks(
        [A.reconcile_scenario(scenario()),
         A.reconcile_scenario(conservative())], t)
    assert len(checks) == 4
    assert {check.phase for check in checks} == {
        "Tenant phase", "Owner-occupancy phase"}


def test_shut_or_unresolved_469_gate_gives_zero_current_tax_benefit():
    shut = A.build_transition(
        rental_plan(), purchase=PURCHASE, monthly_current_rent=1_500,
        rental_deal=DEAL, rental_gate=shut_gate(), marginal_tax_rate=0.35)
    unknown = A.build_transition(
        rental_plan(), purchase=PURCHASE, monthly_current_rent=1_500,
        rental_deal=DEAL, rental_gate=None, marginal_tax_rate=0.35)
    assert shut.current_rental_tax_benefit == 0
    assert unknown.current_rental_tax_benefit == 0


def test_owner_occupied_financing_is_blocked_when_occupancy_is_too_late():
    t = A.build_transition(
        rental_plan(financing_occupancy="owner_occupied",
                    loan_occupancy_requirement_months=12),
        purchase=PURCHASE, monthly_current_rent=1_500,
        rental_deal=DEAL, rental_gate=shut_gate())
    assert any("exceeds" in blocker for blocker in t.blockers)


@pytest.mark.parametrize("plan", [
    {"kind": "continue_renting", "analysis_months": 12},
    {"kind": "buy_immediately_occupy", "analysis_months": 12},
    {"kind": "buy_land_continue_renting", "analysis_months": 12,
     "land_costs": {"debt_service_annual": 6_000,
                    "property_tax_annual": 1_000,
                    "insurance_annual": 500,
                    "maintenance_annual": 800,
                    "hoa_annual": 0}},
])
def test_other_transition_kinds_have_one_explicit_phase(plan):
    t = A.build_transition(
        plan, purchase=PURCHASE, monthly_current_rent=1_500)
    assert len(t.phases) == 1
    assert t.phases[0].months == 12


def test_rental_snapshot_exposes_every_property_cash_line():
    s = R.rental_snapshot(DEAL)
    assert s.vacancy_loss > 0 and s.credit_loss > 0
    assert s.management > 0 and s.leasing_turnover > 0
    assert s.maintenance > 0 and s.capital_reserve > 0
    assert s.property_tax > 0 and s.landlord_insurance > 0
    assert s.hoa > 0 and s.debt_service > 0


def test_tenant_period_applies_second_year_growth_after_month_twelve():
    period = R.rental_period({**DEAL, "rent_growth": 0.12,
                              "expense_growth": 0.06}, months=15)
    expected = 2_100 * 12 + (2_100 * 1.12) * 3
    assert period.gross_rent == pytest.approx(expected)
