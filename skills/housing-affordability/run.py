#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Housing affordability — reconciled cash flow, liquidity, and phases."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

from pf import cli, conflicts as C, facts as F  # noqa: E402
from pf import housing_affordability as A  # noqa: E402
from pf import skill_metrics as SM  # noqa: E402

REQUIRED = [
    "household.members", "household.balance_sheet", "retirement.annual_savings",
    "cash_flow.scenarios", "housing.monthly_rent", "housing.purchase",
    "housing.affordability", "housing.transition",
]
m = cli.money


def calculate(data: dict) -> tuple[A.Affordability, A.Transition]:
    purchase = F._dig(data, "housing.purchase") or {}
    result = A.assess(
        scenarios=F._dig(data, "cash_flow.scenarios") or [],
        purchase=purchase,
        monthly_rent=float(F._dig(data, "housing.monthly_rent")),
        balance_sheet=F._dig(data, "household.balance_sheet") or [],
        reserve_assets=F.reserve_assets(data),
        retirement_annual_savings=F._dig(data, "retirement.annual_savings"),
        household_income=F.household_income(data),
        household_income_components=F.household_income_components(data),
        affordability=F._dig(data, "housing.affordability") or {},
        transition=F._dig(data, "housing.transition") or {},
        rental_deals=F._dig(data, "real_estate.deals") or [],
        portfolio_wash_sale=F._dig(data, "portfolio.wash_sale"),
    )
    return result, A.transition_from_facts(data)


def build(data: dict, w: cli.Writer) -> None:
    w.add_metrics(SM.emit("housing-affordability", data))
    try:
        result, transition = calculate(data)
    except A.ReconciliationError as exc:
        w(f"## BLOCKED — {exc}")
        w()
        w("No affordability conclusion is produced until the conflicting or "
          "missing fact is reconciled. Unknown is not zero.")
        cli.disclaimer(w, "lib/pf/housing_affordability.py")
        return

    phase_checks = A.phase_cash_checks(result.scenarios, transition)
    failed_phase_checks = [check for check in phase_checks if not check.passes]
    if failed_phase_checks:
        transition.blockers.append(
            f"The target transition misses its prorated savings floor in "
            f"{len(failed_phase_checks)} phase/scenario row(s).")

    if transition.blockers:
        w("## BLOCKED — financing or occupancy assumption")
        w()
        for blocker in transition.blockers:
            w(f"- {blocker}")
        w()

    target_ok = result.target_price <= result.stress_tested_ceiling
    if target_ok and not transition.blockers:
        w(f"✅ **Target {m(result.target_price)} is within the stress-tested "
          f"ceiling of {m(result.stress_tested_ceiling)}.**")
    else:
        w(f"**Target {m(result.target_price)} exceeds the stress-tested "
          f"ceiling of {m(result.stress_tested_ceiling)}.**")
    w()
    w("All figures in this report are **nominal cash flow**. Affordability "
      "includes mortgage principal. The separate `rent-vs-buy` report treats "
      "principal as equity and compares the economic cost only after a price "
      "has been shown feasible here.")
    w()

    w("## Capacity and constraints")
    w()
    w.table(["Constraint", "Limit"], [
        ["Current-income capacity", m(result.current_income_ceiling)],
        ["**Stress-tested ceiling**", f"**{m(result.stress_tested_ceiling)}**"],
        ["Controlling conservative case", result.stress_scenario],
        ["Lender maximum", (m(result.lender_maximum)
                            if result.lender_maximum is not None
                            else "not modeled")],
        ["Investment lender maximum",
         (m(result.investment_lender_maximum)
          if result.investment_lender_maximum is not None else "not modeled")],
        ["Liquidity/down-payment limit", m(result.liquidity_maximum)],
        ["Binding constraint", result.binding_constraint],
    ])
    w()
    w.table(
        ["Named income scenario", "Kind", "Cash-flow price limit"],
        [[label, kind, m(limit)]
         for label, kind, limit in result.scenario_cash_flow_limits],
    )
    w()
    w("The stress-tested ceiling is a constraint, not the household's only "
      "affordable price. The **target** remains a separate decision below it.")
    w()

    w("## Reconciled cash-flow scenarios")
    w()
    w.table(
        ["Scenario", "Income components", "Gross", "Taxes", "After-tax cash"],
        [[s.label,
          ", ".join(f"{name} {m(value)}" for name, value in s.income_components),
          m(s.gross_income), m(s.taxes), m(s.after_tax_cash_income)]
         for s in result.scenarios],
    )
    w()
    w.table(
        ["Scenario", "Employee retirement + IRA", "Employer retirement",
         "Other payroll", "Non-housing", "Timed obligations", "Other committed",
         "Pre-housing surplus", "Savings floor", "Renter savings"],
        [[s.label, m(s.retirement_contributions + s.ira_contributions),
          m(s.employer_retirement_contributions), m(s.payroll_deductions),
          m(s.non_housing_spending), m(s.timed_obligations_annual),
          m(s.other_committed), m(s.pre_housing_surplus), m(s.minimum_savings),
          m(s.pre_housing_surplus
            - float(F._dig(data, "housing.monthly_rent")) * 12.0)]
         for s in result.scenarios],
    )
    w()
    w("`pre-housing surplus` excludes both rent and ownership. The savings "
      "floor is the greater of the recorded dollar and gross-income-rate "
      "requirements when both are present.")
    w()

    w("## Candidate prices")
    w()
    w.table(
        ["Price", "Scenario", "Full owner cash/yr", "Principal/yr",
         "Remaining savings", "Savings rate", "Post-close cash",
         "Reserve months", "Result"],
        [[m(c.price), c.scenario, m(c.owner.gross_annual),
          m(c.owner.principal), m(c.savings.owner_taxable_savings),
          f"{c.savings_rate:.1%}", m(c.post_close_cash),
          f"{c.reserve_months:.1f}",
          ("passes" if (c.feasible_cash_flow and c.feasible_liquidity
                         and c.feasible_lender)
           else "**fails**")]
         for c in result.candidates],
    )
    w()
    w("Invariant checked on every row: `pre-housing surplus − full owner cash "
      "cost` equals `renter savings − (owner cash cost − rent)`. Incremental "
      "ownership cost is never subtracted from a pre-rent surplus.")
    w()
    w(result.tax_benefit.explanation)
    if result.tax_benefit.incremental_annual is not None:
        w("Affordability ceilings remain gross; this benefit is credited only "
          "to its recorded modeled price and is not extrapolated.")
    w()

    target_current = next(
        c for c in result.candidates
        if c.price == result.target_price
        and c.scenario == next(
            s.label for s in result.scenarios if s.kind == "current"))
    owner = target_current.owner
    w("### Target owner cash ledger")
    w()
    w.table(["Annual cash line", "Amount"], [
        ["Principal and interest", m(owner.principal_and_interest)],
        ["  of which principal", m(owner.principal)],
        ["Property tax", m(owner.property_tax)],
        ["Insurance", m(owner.insurance)],
        ["Maintenance", m(owner.maintenance)],
        ["HOA", m(owner.hoa)],
        ["PMI", m(owner.pmi)],
        ["Other owner costs", m(owner.other)],
        ["**Gross owner cash cost**", f"**{m(owner.gross_annual)}**"],
        ["Incremental tax benefit",
         m(owner.tax_benefit) if owner.tax_benefit is not None else "excluded"],
    ])
    w()

    w("## Closing sources and uses")
    w()
    w.table(["Source", "Amount"], [
        ["Cash and cash equivalents at face value", m(result.cash_available)],
        ["Marketable securities (not cash at par)", m(result.marketable_not_cash)],
        ["Restricted assets (not closing funds)", m(result.restricted_not_cash)],
        ["Illiquid assets (not closing funds)", m(result.illiquid_not_cash)],
        ["Unclassified assets (excluded)", m(result.unclassified_not_cash)],
        ["Spendable taxable-sale proceeds",
         m(result.liquidation.spendable_proceeds) if result.liquidation else "none"],
    ])
    if result.liquidation:
        sale = result.liquidation
        w()
        w.table(["Taxable liquidation", "Amount"], [
            ["Gross sale proceeds", m(sale.gross_sale_proceeds)],
            ["Less account debt payoff", f"−{m(sale.debt_payoff)}"],
            ["Less federal tax reserve", f"−{m(sale.federal_tax_reserve)}"],
            ["Less state tax reserve", f"−{m(sale.state_tax_reserve)}"],
            ["**Spendable proceeds**", f"**{m(sale.spendable_proceeds)}**"],
            ["Net-worth change from sale",
             (f"−{m(abs(sale.net_worth_change))}"
              if sale.net_worth_change < 0 else m(sale.net_worth_change))],
        ])
        w()
        w("The gross proceeds replace securities; they are not new wealth. "
          "Only taxes reduce net worth in this conversion ledger, while debt "
          "payoff removes an equal liability.")
        target = target_current
        opening_assets = sum(
            float(row.get("value") or 0.0)
            for row in (F._dig(data, "household.balance_sheet") or [])
            if not row.get("pending"))
        taxes = sale.federal_tax_reserve + sale.state_tax_reserve
        post_close_assets = (
            opening_assets - sale.gross_sale_proceeds
            + sale.gross_sale_proceeds - sale.debt_payoff - taxes
            - target.initial_down_payment - target.initial_closing_costs)
        w()
        w.table(["Target sources and uses", "Amount"], [
            ["Opening gross financial assets", m(opening_assets)],
            ["Less securities sold", f"−{m(sale.gross_sale_proceeds)}"],
            ["Plus cash proceeds received", m(sale.gross_sale_proceeds)],
            ["Less account debt payoff", f"−{m(sale.debt_payoff)}"],
            ["Less taxes reserved", f"−{m(taxes)}"],
            ["Less down payment and closing",
             f"−{m(target.initial_down_payment + target.initial_closing_costs)}"],
            ["**Post-close financial assets and cash**",
             f"**{m(post_close_assets)}**"],
        ])
    w()

    w("## Housing transition")
    w()
    if transition.occupancy_conversion_date:
        w(f"Occupancy converts on **{transition.occupancy_conversion_date}**; "
          f"financing is classified **{transition.financing_occupancy}**.")
        w()
    if transition.kind == "rental_then_owner":
        w.table(["Initial investment financing", "Amount"], [
            ["Investment-property down payment",
             m(transition.initial_down_payment)],
            ["Investment-property closing costs",
             m(transition.initial_closing_costs)],
            ["Initial investment loan", m(transition.initial_loan)],
            ["Investment lender test",
             (f"DSCR {transition.investment_dscr:.2f}"
              if transition.investment_lender_test == "dscr"
              and transition.investment_dscr is not None
              else str(transition.investment_lender_test or "missing"))],
            ["Loan balance entering owner phase", m(transition.owner_phase_loan)],
            ["Refinance cost",
             m(F._dig(data, "housing.transition.refinance_cost"))
             if F._dig(data, "housing.transition.refinance_at_occupancy")
             else "not applicable"],
            ["Cash reserve assumption",
             f"{transition.reserve_months_assumed:.1f} months"
             if transition.reserve_months_assumed is not None else "missing"],
        ])
        w()
    w.table(
        ["Phase", "Months", "Current rent", "Tenant gross", "Vacancy/credit",
         "Management", "Turnover", "Maintenance", "Cap reserve", "Tax",
         "Insurance", "HOA", "Debt service", "Other", "Net cash flow"],
        [[p.label, str(p.months), m(p.current_home_rent),
          m(p.tenant_gross_rent), m(p.vacancy_and_credit_loss),
          m(p.management), m(p.leasing_turnover), m(p.maintenance),
          m(p.capital_reserve), m(p.property_tax), m(p.insurance), m(p.hoa),
          m(p.debt_service), m(p.other), m(p.net_cash_flow)]
         for p in transition.phases],
    )
    w()
    household_rows = []
    combined_by_scenario = {scenario.label: 0.0 for scenario in result.scenarios}
    for check in phase_checks:
        combined_by_scenario[check.scenario] += check.remaining_cash
        household_rows.append([
            check.phase, check.scenario, m(check.pre_housing_cash),
            m(check.housing_cash_flow), m(check.remaining_cash),
            m(check.savings_floor),
            "passes" if check.passes else "**fails**",
        ])
    for scenario in result.scenarios:
        household_rows.append([
            "**Combined**", scenario.label, "—",
            m(transition.combined_cash_flow),
            f"**{m(combined_by_scenario[scenario.label])}**",
            m(scenario.minimum_savings * sum(
                phase.months for phase in transition.phases) / 12.0),
            "—",
        ])
    w.table(
        ["Phase", "Scenario", "Pre-housing cash", "Housing cash flow",
         "Remaining cash", "Prorated savings floor", "Result"],
        household_rows,
    )
    w()
    w(f"Combined transition cash flow: **{m(transition.combined_cash_flow)}**. "
      "The tenant phase is nominal and pre-investor-tax. Current rent and "
      "tenant income both end when owner occupancy begins.")
    w("The transition table evaluates the recorded **target property only**; "
      "its rent and operating expenses are not extrapolated to unrelated "
      "candidate prices.")
    w()
    for finding in transition.findings + result.findings:
        w(f"- {finding}")
    conflicts = C.for_skill(data, "housing-affordability")
    if conflicts:
        w()
        w("## Cross-skill checks")
        w()
        for conflict in conflicts:
            w(f"- **{conflict.key}:** {conflict.tension} {conflict.resolution}")

    cli.disclaimer(
        w,
        "lib/pf/housing_affordability.py",
        "No market prices, tax rules, or loan-occupancy deadlines are fetched; "
        "the report uses only recorded facts.",
    )


if __name__ == "__main__":
    raise SystemExit(cli.run(
        title="Housing affordability",
        required=REQUIRED,
        build=build,
        skill_id="housing-affordability",
    ))
