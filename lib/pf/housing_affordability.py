"""Household housing capacity and phased transitions, in nominal dollars.

This module answers a cash-flow question: what purchase price survives the
household's income, savings floor, lender constraint, and closing liquidity?
It intentionally does not answer whether buying is economically preferable;
``pf.housing`` owns that comparison and excludes mortgage principal from cost.

The load-bearing invariant is that a pre-housing surplus must lose the *full*
owner cash cost.  The equivalent renter bridge subtracts rent first and then
only the incremental owner cost.  Both paths are computed and asserted equal
so the historical double-rent defect cannot return as a reporting choice.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

from . import facts as F
from . import realestate as R
from .housing import amortise, monthly_payment

#: Reconciliations within $100 and 0.1% are treated as rounding; larger gaps
#: mean two independently maintained versions of the same annual figure exist.
MATERIAL_MISMATCH_DOLLARS = 100.0
MATERIAL_MISMATCH_RATE = 0.001

#: Binary searches stop once adjacent candidate prices differ by one dollar;
#: reporting a tighter result would imply false precision in insurance and tax.
CEILING_RESOLUTION = 1.0


class ReconciliationError(ValueError):
    """Facts disagree in a way that makes an affordability result unsafe."""


def _materially_different(recorded: float, derived: float) -> bool:
    tolerance = max(
        MATERIAL_MISMATCH_DOLLARS,
        MATERIAL_MISMATCH_RATE * max(abs(recorded), abs(derived)),
    )
    return abs(recorded - derived) > tolerance


def _number(mapping: dict, key: str) -> float:
    value = mapping.get(key)
    if value is None:
        raise ReconciliationError(f"`{key}` is required; unknown is not zero")
    return float(value)


@dataclass(frozen=True)
class CashObligation:
    label: str
    annual_amount: float
    start_month: int
    end_month: int | None


@dataclass(frozen=True)
class IncomeScenario:
    label: str
    kind: str
    income_components: tuple[tuple[str, float], ...]
    gross_income: float
    after_tax_cash_income: float
    taxes: float
    retirement_contributions: float
    employer_retirement_contributions: float
    payroll_deductions: float
    non_housing_spending: float
    timed_obligations_annual: float
    ira_contributions: float
    other_committed: float
    pre_housing_surplus: float
    minimum_savings: float
    obligations: tuple[CashObligation, ...] = ()
    findings: tuple[str, ...] = ()


def _parse_obligations(raw: dict) -> tuple[CashObligation, ...]:
    out = []
    for item in raw.get("obligations") or []:
        if item.get("annual_amount") is None:
            raise ReconciliationError(
                f"{raw.get('label') or 'scenario'}: obligation "
                f"{item.get('label') or 'unnamed'} has unknown annual_amount")
        first = int(item.get("start_month") or 1)
        last_raw = item.get("end_month")
        last = None if last_raw is None else int(last_raw)
        if first < 1 or (last is not None and last < first):
            raise ReconciliationError(
                f"{raw.get('label') or 'scenario'}: obligation months are invalid")
        amount = float(item["annual_amount"])
        if amount < 0:
            raise ReconciliationError(
                f"{raw.get('label') or 'scenario'}: obligation amount cannot "
                "be negative")
        out.append(CashObligation(
            label=str(item.get("label") or "unnamed obligation"),
            annual_amount=amount,
            start_month=first,
            end_month=last,
        ))
    return tuple(out)


def obligation_cash(
    obligations: tuple[CashObligation, ...],
    *,
    start_month: int,
    months: int,
) -> float:
    """Cash due during an inclusive month window."""
    end_month = start_month + months - 1
    total = 0.0
    for item in obligations:
        first = item.start_month
        last = math.inf if item.end_month is None else item.end_month
        overlap = max(0, min(end_month, last) - max(start_month, first) + 1)
        total += item.annual_amount * overlap / 12.0
    return total


def pre_housing_cash_for_period(
    scenario: IncomeScenario,
    *,
    start_month: int,
    months: int,
) -> float:
    """Scenario cash before housing for a period with timed obligations."""
    fixed_annual = (
        scenario.after_tax_cash_income - scenario.retirement_contributions
        - scenario.ira_contributions - scenario.payroll_deductions
        - scenario.non_housing_spending - scenario.other_committed
    )
    return (
        fixed_annual * months / 12.0
        - obligation_cash(
            scenario.obligations, start_month=start_month, months=months)
    )


def reconcile_scenario(
    raw: dict,
    *,
    household_income: float | None = None,
    household_income_components: dict[str, float] | None = None,
    retirement_annual_savings: float | None = None,
) -> IncomeScenario:
    """Derive one scenario and reject independently maintained contradictions.

    ``after_tax_cash_income_annual`` is compensation after income/payroll tax
    but before the separately listed payroll deductions, retirement saving,
    and committed uses.  If it is absent, ``taxes_annual`` must be present so
    the same value can be derived.  No tax rate is guessed.
    """
    label = str(raw.get("label") or "unnamed scenario")
    kind = str(raw.get("kind") or "")
    if kind not in ("current", "conservative"):
        raise ReconciliationError(
            f"{label}: `kind` must be current or conservative")
    duplicated_housing = [
        key for key in ("housing_spending_annual", "rent_annual", "monthly_rent")
        if key in raw
    ]
    if duplicated_housing:
        raise ReconciliationError(
            f"{label}: housing belongs in the housing ledger, not the "
            "pre-housing scenario; remove " + ", ".join(duplicated_housing))
    components = raw.get("income_components")
    if not isinstance(components, dict) or not components:
        raise ReconciliationError(
            f"{label}: `income_components` must name the compensation parts")
    missing_components = [name for name, value in components.items()
                          if value is None]
    if missing_components:
        raise ReconciliationError(
            f"{label}: income components are unknown for "
            + ", ".join(sorted(missing_components)))
    gross_derived = sum(float(v or 0.0) for v in components.values())
    if any(float(value) < 0 for value in components.values()):
        raise ReconciliationError(f"{label}: income components cannot be negative")
    gross_recorded = raw.get("gross_income_annual")
    if gross_recorded is not None and _materially_different(
            float(gross_recorded), gross_derived):
        raise ReconciliationError(
            f"{label}: gross income {float(gross_recorded):,.0f} disagrees "
            f"with components {gross_derived:,.0f}")
    gross = gross_derived if gross_recorded is None else float(gross_recorded)
    if kind == "current" and household_income is not None and _materially_different(
            household_income, gross):
        raise ReconciliationError(
            f"{label}: current scenario gross income {gross:,.0f} disagrees "
            f"with household members {household_income:,.0f}")
    if kind == "current" and household_income_components:
        keys = set(components) | set(household_income_components)
        mismatched = [
            key for key in sorted(keys)
            if _materially_different(
                float(components.get(key) or 0.0),
                float(household_income_components.get(key) or 0.0),
            )
        ]
        if mismatched:
            raise ReconciliationError(
                f"{label}: income components disagree with household members "
                f"for {', '.join(mismatched)}")

    after_tax_raw = raw.get("after_tax_cash_income_annual")
    taxes_raw = raw.get("taxes_annual")
    if after_tax_raw is None and taxes_raw is None:
        raise ReconciliationError(
            f"{label}: supply after-tax cash income or annual taxes; taxes "
            "will not be approximated")
    if after_tax_raw is None:
        taxes = float(taxes_raw)
        after_tax = gross - taxes
    elif taxes_raw is None:
        after_tax = float(after_tax_raw)
        taxes = gross - after_tax
    else:
        after_tax = float(after_tax_raw)
        taxes = float(taxes_raw)
        derived_after_tax = gross - taxes
        if _materially_different(after_tax, derived_after_tax):
            raise ReconciliationError(
                f"{label}: after-tax cash income {after_tax:,.0f} disagrees "
                f"with gross less taxes {derived_after_tax:,.0f}")
    if gross < 0 or taxes < 0 or after_tax < 0 or after_tax > gross:
        raise ReconciliationError(
            f"{label}: gross income, taxes, and after-tax cash are inconsistent")

    retirement = _number(raw, "retirement_contributions_annual")
    ira = _number(raw, "ira_contributions_annual")
    employer_raw = raw.get("employer_retirement_contributions_annual")
    if (kind == "current" and retirement_annual_savings is not None
            and employer_raw is None):
        raise ReconciliationError(
            f"{label}: employer_retirement_contributions_annual is required "
            "to reconcile retirement.annual_savings")
    employer_retirement = float(employer_raw or 0.0)
    if (kind == "current" and retirement_annual_savings is not None
            and _materially_different(
                retirement_annual_savings,
                retirement + ira + employer_retirement)):
        raise ReconciliationError(
            f"{label}: retirement cash-flow inputs "
            f"{retirement + ira + employer_retirement:,.0f} "
            f"disagree with retirement.annual_savings "
            f"{retirement_annual_savings:,.0f}")

    payroll = _number(raw, "other_payroll_deductions_annual")
    non_housing = _number(raw, "non_housing_spending_annual")
    obligations = _parse_obligations(raw)
    education = obligation_cash(
        obligations, start_month=1, months=12)
    other = _number(raw, "other_committed_annual")
    pre_housing = (
        after_tax - retirement - ira - payroll - non_housing - education - other
    )

    floor = raw.get("minimum_savings") or {}
    if not floor or ("annual_amount" not in floor
                     and "gross_income_rate" not in floor):
        raise ReconciliationError(
            f"{label}: minimum_savings needs annual_amount, "
            "gross_income_rate, or both")
    null_floor = [key for key in ("annual_amount", "gross_income_rate")
                  if key in floor and floor[key] is None]
    if null_floor:
        raise ReconciliationError(
            f"{label}: minimum_savings is unknown for "
            + ", ".join(null_floor))
    dollars = float(floor.get("annual_amount", 0.0))
    rate = float(floor.get("gross_income_rate", 0.0))
    if dollars < 0 or not 0 <= rate <= 1:
        raise ReconciliationError(
            f"{label}: minimum savings dollars must be nonnegative and the "
            "rate must be between 0 and 1")
    minimum = max(dollars, gross * rate)
    findings = (
        "Both savings floors were supplied; the greater requirement controls.",
    ) if "annual_amount" in floor and "gross_income_rate" in floor else ()
    return IncomeScenario(
        label=label,
        kind=kind,
        income_components=tuple(
            (str(name), float(value)) for name, value in sorted(components.items())),
        gross_income=gross,
        after_tax_cash_income=after_tax,
        taxes=taxes,
        retirement_contributions=retirement,
        employer_retirement_contributions=employer_retirement,
        payroll_deductions=payroll,
        non_housing_spending=non_housing,
        timed_obligations_annual=education,
        ira_contributions=ira,
        other_committed=other,
        pre_housing_surplus=pre_housing,
        minimum_savings=minimum,
        obligations=obligations,
        findings=findings,
    )


@dataclass(frozen=True)
class TaxBenefit:
    incremental_annual: float | None
    explanation: str
    modeled_price: float | None = None


def incremental_tax_benefit(raw: dict | None) -> TaxBenefit:
    """Incremental owner benefit against the renter baseline, or excluded."""
    if not raw:
        return TaxBenefit(
            None,
            "Tax benefit excluded: itemization, filing status, deduction cap, "
            "and the renter baseline were not modeled.",
        )
    required = (
        "filing_status", "itemizes_owner", "standard_deduction_annual",
        "renter_itemized_deductions_annual",
        "owner_deductible_housing_annual", "deduction_cap_annual",
        "marginal_tax_rate", "modeled_price",
    )
    missing = [k for k in required if raw.get(k) is None]
    if missing:
        raise ReconciliationError(
            "tax benefit is partial; missing " + ", ".join(missing))
    if not raw.get("itemizes_owner"):
        return TaxBenefit(
            0.0,
            "Owner itemization is recorded as false; zero incremental benefit.",
            float(raw["modeled_price"]),
        )
    standard = float(raw["standard_deduction_annual"])
    renter_itemized = float(raw["renter_itemized_deductions_annual"])
    eligible_housing = min(
        float(raw["owner_deductible_housing_annual"]),
        float(raw["deduction_cap_annual"]),
    )
    renter_deduction = max(standard, renter_itemized)
    owner_deduction = max(standard, renter_itemized + eligible_housing)
    incremental = max(0.0, owner_deduction - renter_deduction)
    benefit = incremental * float(raw["marginal_tax_rate"])
    return TaxBenefit(
        benefit,
        f"{raw['filing_status']} filer: owner deduction exceeds the renter "
        f"baseline by {incremental:,.0f}; tax effect uses the recorded "
        f"{float(raw['marginal_tax_rate']):.1%} marginal rate at the modeled "
        f"price of {float(raw['modeled_price']):,.0f}.",
        float(raw["modeled_price"]),
    )


@dataclass(frozen=True)
class OwnerCashCost:
    price: float
    down_payment: float
    closing_costs: float
    loan: float
    principal_and_interest: float
    interest: float
    principal: float
    property_tax: float
    insurance: float
    maintenance: float
    hoa: float
    pmi: float
    other: float
    gross_annual: float
    tax_benefit: float | None
    net_annual: float


def owner_cash_cost(
    purchase: dict,
    *,
    price: float | None = None,
    tax_benefit: TaxBenefit | None = None,
) -> OwnerCashCost:
    """First-year owner cash ledger; principal is an outflow here."""
    p = (_number(purchase, "price") if price is None else float(price))
    down_rate = _number(purchase, "down_payment_rate")
    closing_rate = _number(purchase, "closing_cost_rate")
    rate = _number(purchase, "mortgage_rate")
    term = int(_number(purchase, "term_years"))
    tax_rate = _number(purchase, "property_tax_rate")
    insurance = _number(purchase, "insurance_annual")
    maintenance_rate = _number(purchase, "maintenance_rate")
    hoa = _number(purchase, "hoa_monthly") * 12.0
    pmi_rate = _number(purchase, "pmi_rate")
    other = float(purchase.get("other_owner_costs_annual") or 0.0)
    if p < 0 or not 0 <= down_rate <= 1 or closing_rate < 0:
        raise ReconciliationError(
            "purchase price and closing rate must be nonnegative and "
            "down_payment_rate must be between 0 and 1")
    if rate < 0 or term <= 0 or min(
            tax_rate, insurance, maintenance_rate, hoa, pmi_rate, other) < 0:
        raise ReconciliationError(
            "mortgage term must be positive and owner cash inputs cannot be negative")
    down = p * down_rate
    recorded_price = purchase.get("price")
    recorded_down = purchase.get("down_payment")
    if (recorded_price is not None and recorded_down is not None
            and math.isclose(p, float(recorded_price), abs_tol=0.01)
            and _materially_different(float(recorded_down), down)):
        raise ReconciliationError(
            "housing.purchase.down_payment disagrees with price times "
            "down_payment_rate")
    loan = max(0.0, p - down)
    payment = monthly_payment(loan, rate, term) * 12.0
    interest, principal, _ = amortise(loan, rate, term, 12)
    property_tax = p * tax_rate
    maintenance = p * maintenance_rate
    pmi = loan * pmi_rate
    gross = payment + property_tax + insurance + maintenance + hoa + pmi + other
    benefit = None if tax_benefit is None else tax_benefit.incremental_annual
    net = gross - (benefit or 0.0)
    return OwnerCashCost(
        price=p,
        down_payment=down,
        closing_costs=p * closing_rate,
        loan=loan,
        principal_and_interest=payment,
        interest=interest,
        principal=principal,
        property_tax=property_tax,
        insurance=insurance,
        maintenance=maintenance,
        hoa=hoa,
        pmi=pmi,
        other=other,
        gross_annual=gross,
        tax_benefit=benefit,
        net_annual=net,
    )


@dataclass(frozen=True)
class SavingsLedger:
    pre_housing_surplus: float
    annual_rent: float
    full_owner_cash_cost: float
    renter_taxable_savings: float
    owner_taxable_savings: float
    owner_via_incremental_bridge: float

    @property
    def invariant_holds(self) -> bool:
        return math.isclose(
            self.owner_taxable_savings,
            self.owner_via_incremental_bridge,
            abs_tol=0.01,
        )


def savings_ledger(
    scenario: IncomeScenario,
    *,
    owner_cash_cost_annual: float,
    annual_rent: float,
) -> SavingsLedger:
    """Compute both valid formulations and enforce their equality."""
    renter = scenario.pre_housing_surplus - annual_rent
    direct = scenario.pre_housing_surplus - owner_cash_cost_annual
    bridge = renter - (owner_cash_cost_annual - annual_rent)
    out = SavingsLedger(
        pre_housing_surplus=scenario.pre_housing_surplus,
        annual_rent=annual_rent,
        full_owner_cash_cost=owner_cash_cost_annual,
        renter_taxable_savings=renter,
        owner_taxable_savings=direct,
        owner_via_incremental_bridge=bridge,
    )
    if not out.invariant_holds:  # pragma: no cover - arithmetic invariant
        raise AssertionError("owner savings formulations diverged")
    return out


@dataclass(frozen=True)
class Liquidation:
    account_name: str
    opening_securities: float
    gross_sale_proceeds: float
    cost_basis: float
    taxable_gain: float
    debt_payoff: float
    federal_tax_reserve: float
    state_tax_reserve: float
    spendable_proceeds: float
    post_sale_net_assets: float
    net_worth_change: float
    securities_sold: tuple[str, ...]
    wash_sale_reviewed: bool


def liquidate_taxable(
    raw: dict,
    *,
    opening_assets: float,
    opening_securities: float,
    tax_lots: list[dict] | None = None,
    account_debt: float | None = None,
) -> Liquidation:
    """Convert taxable securities to cash without creating net worth."""
    required = (
        "account_name", "loss_carryforward", "federal_tax_rate",
        "state_tax_rate", "wash_sale_reviewed",
    )
    missing = [k for k in required if raw.get(k) is None]
    if missing:
        raise ReconciliationError(
            "taxable liquidation cannot be modeled; missing "
            + ", ".join(missing))
    selected = tuple(str(x) for x in raw.get("securities_sold") or [])
    if len(selected) != len(set(selected)):
        raise ReconciliationError(
            "taxable liquidation securities_sold contains a duplicate ticker")
    if tax_lots and selected:
        tickers = [str(lot.get("ticker")) for lot in tax_lots]
        if len(tickers) != len(set(tickers)):
            raise ReconciliationError(
                "taxable account tax_lots contains a duplicate ticker")
        by_ticker = {str(lot.get("ticker")): lot for lot in tax_lots}
        absent = [ticker for ticker in selected if ticker not in by_ticker]
        if absent:
            raise ReconciliationError(
                "taxable liquidation lots not found in account: "
                + ", ".join(absent))
        lots = [by_ticker[ticker] for ticker in selected]
        lot_missing = [
            f"{lot.get('ticker')}.{key}"
            for lot in lots
            for key in ("value", "cost_basis", "holding_period")
            if lot.get(key) is None
        ]
        if lot_missing:
            raise ReconciliationError(
                "taxable liquidation cannot be modeled; missing "
                + ", ".join(lot_missing))
        gross = sum(float(lot["value"]) for lot in lots)
        basis = sum(float(lot["cost_basis"]) for lot in lots)
        periods = {lot["holding_period"] for lot in lots}
        if len(periods) != 1:
            raise ReconciliationError(
                "taxable liquidation mixes holding periods; model separate sales")
        holding = periods.pop()
        for key, derived in (("gross_sale_proceeds", gross),
                             ("cost_basis", basis)):
            if raw.get(key) is not None and _materially_different(
                    float(raw[key]), derived):
                raise ReconciliationError(
                    f"taxable liquidation {key} disagrees with selected lots")
    else:
        manual = ("gross_sale_proceeds", "cost_basis", "holding_period")
        missing_manual = [key for key in manual if raw.get(key) is None]
        if missing_manual:
            raise ReconciliationError(
                "taxable liquidation cannot be modeled; missing "
                + ", ".join(missing_manual))
        gross = float(raw["gross_sale_proceeds"])
        basis = float(raw["cost_basis"])
        holding = raw["holding_period"]
    if holding not in ("short_term", "long_term"):
        raise ReconciliationError(
            "taxable liquidation holding_period must be short_term or long_term")
    if gross < 0 or basis < 0:
        raise ReconciliationError(
            "taxable liquidation proceeds and cost basis cannot be negative")
    debt_raw = raw.get("margin_debt_payoff")
    if account_debt is None and debt_raw is None:
        raise ReconciliationError(
            "taxable liquidation cannot be modeled; missing margin debt")
    debt = float(account_debt if account_debt is not None else debt_raw)
    if (account_debt is not None and debt_raw is not None
            and _materially_different(float(debt_raw), account_debt)):
        raise ReconciliationError(
            "taxable liquidation margin debt disagrees with the account")
    loss_cf = float(raw["loss_carryforward"])
    if debt < 0 or loss_cf < 0:
        raise ReconciliationError(
            "margin debt and loss carryforward cannot be negative")
    rates = (float(raw["federal_tax_rate"]), float(raw["state_tax_rate"]))
    if any(rate < 0 or rate > 1 for rate in rates):
        raise ReconciliationError("tax reserve rates must be between 0 and 1")
    if gross > opening_securities + 0.01:
        raise ReconciliationError(
            f"taxable sale {gross:,.0f} exceeds account value "
            f"{opening_securities:,.0f}")
    taxable_gain = max(0.0, gross - basis - loss_cf)
    federal = taxable_gain * rates[0]
    state = taxable_gain * rates[1]
    spendable = gross - debt - federal - state
    if spendable < 0:
        raise ReconciliationError(
            "taxable liquidation produces negative spendable proceeds")
    opening_net_assets = opening_assets - debt
    post_sale_net_assets = opening_assets - debt - federal - state
    return Liquidation(
        account_name=str(raw["account_name"]),
        opening_securities=opening_securities,
        gross_sale_proceeds=gross,
        cost_basis=basis,
        taxable_gain=taxable_gain,
        debt_payoff=debt,
        federal_tax_reserve=federal,
        state_tax_reserve=state,
        spendable_proceeds=spendable,
        post_sale_net_assets=post_sale_net_assets,
        net_worth_change=post_sale_net_assets - opening_net_assets,
        securities_sold=selected,
        wash_sale_reviewed=bool(raw["wash_sale_reviewed"]),
    )


@dataclass(frozen=True)
class Candidate:
    scenario: str
    price: float
    owner: OwnerCashCost
    savings: SavingsLedger
    minimum_savings: float
    savings_rate: float
    initial_down_payment: float
    initial_closing_costs: float
    post_close_cash: float
    reserve_required: float
    reserve_months: float
    feasible_cash_flow: bool
    feasible_liquidity: bool
    feasible_lender: bool


@dataclass
class Affordability:
    scenarios: list[IncomeScenario]
    candidates: list[Candidate]
    scenario_cash_flow_limits: tuple[tuple[str, str, float], ...]
    target_price: float
    current_income_ceiling: float
    stress_tested_ceiling: float
    stress_scenario: str
    lender_maximum: float | None
    investment_lender_maximum: float | None
    liquidity_maximum: float
    binding_constraint: str
    cash_available: float
    marketable_not_cash: float
    restricted_not_cash: float
    illiquid_not_cash: float
    unclassified_not_cash: float
    liquidation: Liquidation | None
    tax_benefit: TaxBenefit
    findings: list[str] = field(default_factory=list)


def _solve_ceiling(predicate: Callable[[float], bool]) -> float:
    lo, hi = 0.0, 100_000.0
    for _ in range(30):
        if not predicate(hi):
            break
        lo, hi = hi, hi * 2.0
    else:  # pragma: no cover - implausibly unbounded malformed inputs
        raise ReconciliationError("affordability ceiling did not converge")
    while hi - lo > CEILING_RESOLUTION:
        mid = (lo + hi) / 2.0
        if predicate(mid):
            lo = mid
        else:
            hi = mid
    return lo


def _lender_limit(purchase: dict, lender: dict | None, gross: float) -> float | None:
    if not lender:
        return None
    dti = lender.get("maximum_housing_dti")
    if dti is None:
        raise ReconciliationError(
            "lender model is present but maximum_housing_dti is missing")
    other_debt = float(lender.get("other_debt_annual") or 0.0)
    maximum = gross * float(dti) - other_debt

    def clears(price: float) -> bool:
        c = owner_cash_cost(purchase, price=price)
        lender_housing = (
            c.principal_and_interest + c.property_tax + c.insurance
            + c.hoa + c.pmi
        )
        return lender_housing <= maximum

    return _solve_ceiling(clears)


def assess(
    *,
    scenarios: list[dict],
    purchase: dict,
    monthly_rent: float,
    balance_sheet: list[dict],
    reserve_assets: F.ClassifiedAssets,
    retirement_annual_savings: float | None,
    household_income: float | None,
    household_income_components: dict[str, float] | None = None,
    affordability: dict,
    transition: dict | None = None,
    rental_deals: list[dict] | None = None,
    portfolio_wash_sale: dict | None = None,
) -> Affordability:
    """Reconcile inputs, calculate constraints, and evaluate candidate prices."""
    reconciled = [
        reconcile_scenario(
            s,
            household_income=household_income,
            household_income_components=household_income_components,
            retirement_annual_savings=retirement_annual_savings,
        )
        for s in scenarios
    ]
    current = [s for s in reconciled if s.kind == "current"]
    conservative = [s for s in reconciled if s.kind == "conservative"]
    if len(current) != 1 or not conservative:
        raise ReconciliationError(
            "cash_flow.scenarios needs exactly one current case and at least "
            "one conservative case")
    tax = incremental_tax_benefit(affordability.get("tax_benefit"))
    # Validate the fixed target amount against its rate even when a phased
    # financing plan later substitutes the investment loan balance.
    owner_cash_cost(purchase)

    opening_assets = sum(
        float(r.get("value") or 0.0) for r in balance_sheet
        if not r.get("pending"))
    liquidation = None
    funding = affordability.get("funding") or {}
    sale = funding.get("taxable_liquidation")
    if sale:
        account = next(
            (r for r in balance_sheet if r.get("name") == sale.get("account_name")),
            None,
        )
        if account is None:
            raise ReconciliationError(
                "taxable liquidation account_name does not match the balance sheet")
        if account.get("liquidity_class") != F.MARKETABLE:
            raise ReconciliationError(
                "taxable liquidation source must be classified marketable")
        liquidation = liquidate_taxable(
            sale,
            opening_assets=opening_assets,
            opening_securities=float(account.get("value") or 0.0),
            tax_lots=account.get("tax_lots") or [],
            account_debt=account.get("margin_debt"),
        )
    available_cash = reserve_assets.included + (
        liquidation.spendable_proceeds if liquidation else 0.0)
    reserve_months_required = _number(affordability, "post_close_reserve_months")
    initial_down_rate = _number(purchase, "down_payment_rate")
    initial_closing_rate = _number(purchase, "closing_cost_rate")
    owner_purchase = purchase
    rental_deal = None
    if (transition or {}).get("kind") == "rental_then_owner":
        label = (transition or {}).get("rental_deal_label")
        deal = next(
            (d for d in (rental_deals or []) if d.get("label") == label),
            None,
        )
        if deal is None:
            raise ReconciliationError(
                "rental_then_owner needs a matching real_estate.deals entry")
        rental_deal = deal
        deal_price = float(deal.get("price") or 0.0)
        if (deal_price <= 0 or deal.get("down_payment") is None
                or deal.get("closing_costs") is None):
            raise ReconciliationError(
                "investment-property price, down payment, and closing costs "
                "are required")
        initial_down_rate = float(deal["down_payment"]) / deal_price
        initial_closing_rate = float(deal["closing_costs"]) / deal_price
        tenant_months = int((transition or {}).get("tenant_months") or 0)
        _, _, remaining_per_dollar = amortise(
            1.0 - initial_down_rate,
            float(deal.get("loan_rate") or 0.0),
            int(deal.get("loan_term_years") or 30),
            tenant_months,
        )
        if (transition or {}).get("refinance_at_occupancy") is True:
            owner_purchase = {
                key: value for key, value in purchase.items()
                if key != "down_payment"
            }
            owner_purchase["down_payment_rate"] = 1.0 - remaining_per_dollar
        elif (transition or {}).get("refinance_at_occupancy") is False:
            owner_purchase = {
                **{key: value for key, value in purchase.items()
                   if key != "down_payment"},
                "down_payment_rate": initial_down_rate,
                "mortgage_rate": deal.get("loan_rate"),
                "term_years": deal.get("loan_term_years"),
            }

    lender_limits = {
        scenario.label: _lender_limit(
            owner_purchase, affordability.get("lender"), scenario.gross_income)
        for scenario in reconciled
    }
    investment_lender_max = None
    if (rental_deal is not None
            and (transition or {}).get("investment_lender_test") == "dscr"):
        def clears_investment_lender(price: float) -> bool:
            candidate_deal = {
                **rental_deal,
                "price": price,
                "down_payment": price * initial_down_rate,
                "closing_costs": price * initial_closing_rate,
            }
            return R.underwrite(candidate_deal).financeable is True

        investment_lender_max = _solve_ceiling(clears_investment_lender)

    def result_for(
        scenario: IncomeScenario,
        price: float,
        *,
        include_tax_benefit: bool = True,
    ) -> Candidate:
        candidate_tax = (
            tax if include_tax_benefit and tax.modeled_price is not None
            and math.isclose(price, tax.modeled_price, abs_tol=0.01)
            else None
        )
        owner = owner_cash_cost(
            owner_purchase, price=price, tax_benefit=candidate_tax)
        savings = savings_ledger(
            scenario,
            owner_cash_cost_annual=owner.net_annual,
            annual_rent=float(monthly_rent) * 12.0,
        )
        initial_down = price * initial_down_rate
        initial_closing = price * initial_closing_rate
        post_close = available_cash - initial_down - initial_closing
        monthly_need = (
            scenario.non_housing_spending + scenario.timed_obligations_annual
            + scenario.other_committed + owner.gross_annual
        ) / 12.0
        reserve_required = reserve_months_required * monthly_need
        months = post_close / monthly_need if monthly_need > 0 else math.inf
        return Candidate(
            scenario=scenario.label,
            price=price,
            owner=owner,
            savings=savings,
            minimum_savings=scenario.minimum_savings,
            savings_rate=(savings.owner_taxable_savings / scenario.gross_income
                          if scenario.gross_income else 0.0),
            initial_down_payment=initial_down,
            initial_closing_costs=initial_closing,
            post_close_cash=post_close,
            reserve_required=reserve_required,
            reserve_months=months,
            feasible_cash_flow=(
                savings.owner_taxable_savings >= scenario.minimum_savings),
            feasible_liquidity=post_close >= reserve_required,
            feasible_lender=(
                lender_limits[scenario.label] is None
                or price <= float(lender_limits[scenario.label]))
                and (investment_lender_max is None
                     or price <= investment_lender_max),
        )

    cash_flow_limits = {
        scenario.label: _solve_ceiling(
            lambda p, s=scenario: result_for(
                s, p, include_tax_benefit=False).feasible_cash_flow)
        for scenario in reconciled
    }
    current_ceiling = cash_flow_limits[current[0].label]
    stress_cash_limits = {
        scenario.label: cash_flow_limits[scenario.label]
        for scenario in conservative
    }
    stress_label, stress_cash_ceiling = min(
        stress_cash_limits.items(), key=lambda item: item[1])
    liquidity_limits = {
        scenario.label: _solve_ceiling(
            lambda p, s=scenario: result_for(
                s, p, include_tax_benefit=False).feasible_liquidity)
        for scenario in conservative
    }
    _, liquidity_ceiling = min(
        liquidity_limits.items(), key=lambda item: item[1])
    lender_values = [
        value for scenario in conservative
        if (value := lender_limits[scenario.label]) is not None
    ]
    lender_max = min(lender_values) if lender_values else None
    constraints = {
        "conservative cash-flow savings floor": stress_cash_ceiling,
        "cash-only post-close reserve": liquidity_ceiling,
    }
    if lender_max is not None:
        constraints["lender DTI"] = lender_max
    if investment_lender_max is not None:
        constraints["investment-property DSCR"] = investment_lender_max
    binding, stress_ceiling = min(constraints.items(), key=lambda item: item[1])

    target = float(affordability.get("target_price") or purchase.get("price"))
    prices = [float(p) for p in affordability.get("candidate_prices") or []]
    if target not in prices:
        prices.append(target)
    candidates = [
        result_for(s, price)
        for price in sorted(set(prices))
        for s in reconciled
    ]
    marketable = reserve_assets.by_class.get(F.MARKETABLE, 0.0)
    findings = []
    if reserve_assets.unknown:
        findings.append(
            "Reserve classification missing for: "
            + ", ".join(reserve_assets.unknown)
            + ". These assets are excluded from closing cash.")
    if liquidation and not liquidation.wash_sale_reviewed:
        exclusions = {
            str(x.get("ticker"))
            for x in (portfolio_wash_sale or {}).get("excluded_securities") or []
        }
        overlap = exclusions.intersection(liquidation.securities_sold)
        detail = (
            f"; excluded-list overlap: {', '.join(sorted(overlap))}"
            if overlap else "")
        findings.append(
            "Taxable sale has not been checked against the household wash-sale "
            f"policy{detail}.")
    return Affordability(
        scenarios=reconciled,
        candidates=candidates,
        scenario_cash_flow_limits=tuple(
            (scenario.label, scenario.kind, cash_flow_limits[scenario.label])
            for scenario in reconciled),
        target_price=target,
        current_income_ceiling=current_ceiling,
        stress_tested_ceiling=stress_ceiling,
        stress_scenario=stress_label,
        lender_maximum=lender_max,
        investment_lender_maximum=investment_lender_max,
        liquidity_maximum=liquidity_ceiling,
        binding_constraint=binding,
        cash_available=reserve_assets.included,
        marketable_not_cash=marketable,
        restricted_not_cash=reserve_assets.by_class.get(F.RESTRICTED, 0.0),
        illiquid_not_cash=reserve_assets.by_class.get(F.RESERVE_ILLIQUID, 0.0),
        unclassified_not_cash=sum(
            float(r.get("value") or 0.0) for r in balance_sheet
            if not r.get("pending")
            and r.get("liquidity_class") not in F.LIQUIDITY_CLASSES),
        liquidation=liquidation,
        tax_benefit=tax,
        findings=findings,
    )


@dataclass(frozen=True)
class HousingPhase:
    label: str
    kind: str
    months: int
    current_home_rent: float
    tenant_gross_rent: float
    vacancy_and_credit_loss: float
    management: float
    leasing_turnover: float
    maintenance: float
    capital_reserve: float
    property_tax: float
    insurance: float
    hoa: float
    debt_service: float
    other: float
    net_cash_flow: float


@dataclass
class Transition:
    kind: str
    phases: list[HousingPhase]
    combined_cash_flow: float
    occupancy_conversion_date: str | None
    financing_occupancy: str | None
    current_rental_tax_benefit: float
    initial_down_payment: float = 0.0
    initial_closing_costs: float = 0.0
    initial_loan: float = 0.0
    owner_phase_loan: float = 0.0
    investment_dscr: float | None = None
    investment_lender_test: str | None = None
    reserve_months_assumed: float | None = None
    blockers: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PhaseCashCheck:
    phase: str
    scenario: str
    months: int
    pre_housing_cash: float
    housing_cash_flow: float
    remaining_cash: float
    savings_floor: float

    @property
    def passes(self) -> bool:
        return self.remaining_cash >= self.savings_floor


def phase_cash_checks(
    scenarios: list[IncomeScenario],
    transition: Transition,
) -> list[PhaseCashCheck]:
    """Apply timed household cash uses to each explicit housing phase."""
    rows = []
    start_month = 1
    for phase in transition.phases:
        for scenario in scenarios:
            pre_housing = pre_housing_cash_for_period(
                scenario, start_month=start_month, months=phase.months)
            remaining = pre_housing + phase.net_cash_flow
            rows.append(PhaseCashCheck(
                phase=phase.label,
                scenario=scenario.label,
                months=phase.months,
                pre_housing_cash=pre_housing,
                housing_cash_flow=phase.net_cash_flow,
                remaining_cash=remaining,
                savings_floor=scenario.minimum_savings * phase.months / 12.0,
            ))
        start_month += phase.months
    return rows


def build_transition(
    plan: dict,
    *,
    purchase: dict,
    monthly_current_rent: float,
    rental_deal: dict | None = None,
    rental_gate: R.ActivityGate | None = None,
    marginal_tax_rate: float | None = None,
    reserve_months: float | None = None,
) -> Transition:
    """Build mutually exclusive housing phases over one explicit timeline."""
    kind = str(plan.get("kind") or "")
    total_months = int(plan.get("analysis_months") or 0)
    if total_months <= 0:
        raise ReconciliationError("transition.analysis_months must be positive")
    phases: list[HousingPhase] = []
    blockers: list[str] = []
    findings: list[str] = []
    conversion = plan.get("occupancy_conversion_date")
    financing = plan.get("financing_occupancy")
    tax_benefit = 0.0
    initial_down = initial_closing = initial_loan = 0.0
    owner_phase_loan = 0.0
    investment_dscr = None
    investment_lender_test = plan.get("investment_lender_test")
    owner_growth_raw = plan.get("owner_operating_cost_growth_rate")
    owner_growth = float(owner_growth_raw or 0.0)

    def phase(
        label: str,
        phase_kind: str,
        months: int,
        *,
        rent: float = 0.0,
        owner: OwnerCashCost | None = None,
        snapshot: R.RentalSnapshot | None = None,
        other: float = 0.0,
    ) -> HousingPhase:
        if snapshot:
            tenant = snapshot.gross_rent
            losses = snapshot.vacancy_loss + snapshot.credit_loss
            management = snapshot.management
            leasing = snapshot.leasing_turnover
            maintenance = snapshot.maintenance
            capital = snapshot.capital_reserve
            prop_tax = snapshot.property_tax
            insurance = snapshot.landlord_insurance
            hoa = snapshot.hoa
            debt = snapshot.debt_service
            other_cost = snapshot.other_operating + other
            net = snapshot.cash_flow - rent * months - other
        elif owner:
            tenant = losses = management = leasing = capital = 0.0
            maintenance = prop_tax = insurance = hoa = 0.0
            debt = other_cost = 0.0
            remaining = months
            year = 1
            while remaining:
                chunk = min(12, remaining)
                share = chunk / 12.0
                factor = (1.0 + owner_growth) ** (year - 1)
                maintenance += owner.maintenance * factor * share
                prop_tax += owner.property_tax * factor * share
                insurance += owner.insurance * factor * share
                hoa += owner.hoa * factor * share
                debt += owner.principal_and_interest * share
                other_cost += (owner.pmi + owner.other) * factor * share
                remaining -= chunk
                year += 1
            other_cost += other
            net = -(maintenance + prop_tax + insurance + hoa + debt
                    + other_cost + rent * months)
        else:
            tenant = losses = management = leasing = maintenance = capital = 0.0
            prop_tax = insurance = hoa = debt = 0.0
            other_cost = other
            net = -(rent * months + other)
        return HousingPhase(
            label=label,
            kind=phase_kind,
            months=months,
            current_home_rent=rent * months,
            tenant_gross_rent=tenant,
            vacancy_and_credit_loss=losses,
            management=management,
            leasing_turnover=leasing,
            maintenance=maintenance,
            capital_reserve=capital,
            property_tax=prop_tax,
            insurance=insurance,
            hoa=hoa,
            debt_service=debt,
            other=other_cost,
            net_cash_flow=net,
        )

    if kind == "continue_renting":
        phases.append(phase(
            "Continue current lease", kind, total_months,
            rent=float(monthly_current_rent)))
    elif kind == "buy_immediately_occupy":
        if owner_growth_raw is None:
            findings.append(
                "No owner operating-cost growth rate recorded; 0% nominal was "
                "used for the transition table.")
        phases.append(phase(
            "Owner occupancy", kind, total_months,
            owner=owner_cash_cost(purchase)))
    elif kind == "buy_land_continue_renting":
        land = plan.get("land_costs") or {}
        required = (
            "debt_service_annual", "property_tax_annual", "insurance_annual",
            "maintenance_annual", "hoa_annual",
        )
        missing = [k for k in required if land.get(k) is None]
        if missing:
            raise ReconciliationError(
                "land transition missing " + ", ".join(missing))
        annual = sum(float(land[k]) for k in required)
        phases.append(phase(
            "Rent residence and carry land", kind, total_months,
            rent=float(monthly_current_rent),
            other=annual * total_months / 12.0))
    elif kind == "rental_then_owner":
        tenant_months = int(plan.get("tenant_months") or 0)
        if tenant_months <= 0 or tenant_months >= total_months:
            raise ReconciliationError(
                "rental_then_owner needs tenant_months between 1 and "
                "analysis_months - 1")
        if not conversion:
            raise ReconciliationError(
                "rental_then_owner needs occupancy_conversion_date")
        if rental_deal is None:
            raise ReconciliationError(
                "rental_then_owner needs a matching real_estate.deals entry")
        required_deal = (
            "price", "closing_costs", "down_payment", "loan_rate",
            "loan_term_years", "gross_rent_monthly", "vacancy_rate",
            "credit_loss_rate", "capex_reserve_rate",
        )
        missing_deal = [key for key in required_deal
                        if rental_deal.get(key) is None]
        expenses = rental_deal.get("operating_expenses") or {}
        required_expenses = (
            "property_tax", "management", "leasing_turnover", "maintenance",
            "hoa",
        )
        missing_expenses = [key for key in required_expenses
                            if expenses.get(key) is None]
        if (expenses.get("landlord_insurance") is None
                and expenses.get("insurance") is None):
            missing_expenses.append("landlord_insurance")
        if missing_deal or missing_expenses:
            missing = missing_deal + [f"operating_expenses.{k}"
                                      for k in missing_expenses]
            raise ReconciliationError(
                "rental-first property cash flow is incomplete; missing "
                + ", ".join(missing))
        if _materially_different(
                float(rental_deal["price"]), float(purchase.get("price") or 0.0)):
            raise ReconciliationError(
                "rental deal price disagrees with housing.purchase.price")
        if financing not in ("investment", "owner_occupied"):
            blockers.append(
                "financing_occupancy must be investment or owner_occupied.")
        if reserve_months is None:
            blockers.append(
                "The investment-property cash reserve assumption is missing.")
        if owner_growth_raw is None:
            findings.append(
                "No owner operating-cost growth rate recorded; 0% nominal was "
                "used after conversion.")
        snapshot = R.rental_period(rental_deal, months=tenant_months)
        underwriting = R.underwrite(rental_deal)
        investment_dscr = underwriting.dscr
        if investment_lender_test == "dscr" and underwriting.financeable is False:
            blockers.append(
                f"Investment financing fails the recorded DSCR test: "
                f"{underwriting.dscr:.2f} is below "
                f"{R.DSCR_LENDER_FLOOR:.2f}.")
        elif investment_lender_test not in ("dscr", "personal_dti"):
            blockers.append(
                "investment_lender_test must be dscr or personal_dti.")
        initial_down = float(rental_deal.get("down_payment") or 0.0)
        initial_closing = float(rental_deal.get("closing_costs") or 0.0)
        initial_loan = max(
            0.0, float(rental_deal.get("price") or 0.0) - initial_down)
        refinance = plan.get("refinance_at_occupancy")
        refinance_cost = 0.0
        owner_purchase = purchase
        if refinance is True:
            if plan.get("refinance_cost") is None:
                blockers.append(
                    "Refinancing is planned but refinance_cost is missing.")
            else:
                refinance_cost = float(plan["refinance_cost"])
            _, _, remaining = amortise(
                initial_loan,
                float(rental_deal["loan_rate"]),
                int(rental_deal["loan_term_years"]),
                tenant_months,
            )
            owner_purchase = {
                key: value for key, value in purchase.items()
                if key != "down_payment"
            }
            owner_purchase["down_payment_rate"] = (
                1.0 - remaining / float(rental_deal["price"]))
            owner_phase_loan = remaining
        elif refinance is False:
            owner_purchase = {
                **{key: value for key, value in purchase.items()
                   if key != "down_payment"},
                "down_payment_rate": initial_down / float(rental_deal["price"]),
                "mortgage_rate": rental_deal["loan_rate"],
                "term_years": rental_deal["loan_term_years"],
            }
            _, _, owner_phase_loan = amortise(
                initial_loan,
                float(rental_deal["loan_rate"]),
                int(rental_deal["loan_term_years"]),
                tenant_months,
            )
        phases.append(phase(
            "Tenant phase", "tenant", tenant_months,
            rent=float(monthly_current_rent), snapshot=snapshot))
        phases.append(phase(
            "Owner-occupancy phase", "owner", total_months - tenant_months,
            owner=owner_cash_cost(owner_purchase), other=refinance_cost))
        requirement = plan.get("loan_occupancy_requirement_months")
        if financing == "owner_occupied":
            if requirement is None:
                blockers.append(
                    "Owner-occupied financing is assumed but its actual "
                    "occupancy deadline is not recorded.")
            elif tenant_months > int(requirement):
                blockers.append(
                    f"Planned occupancy after {tenant_months} months exceeds "
                    f"the recorded loan requirement of {int(requirement)} months.")
        if refinance is None:
            blockers.append(
                "The financing/refinancing assumption at conversion is missing.")
        if rental_gate is None or rental_gate.deductible_against_wages is None:
            findings.append(
                "§469 eligibility is unresolved; current rental tax benefit is "
                "zero in this cash plan.")
        elif rental_gate.deductible_against_wages <= 0:
            findings.append(
                "The §469 gate is shut or the loss is suspended; current "
                "rental tax benefit is zero.")
        elif marginal_tax_rate is None:
            findings.append(
                "A §469 door may be open, but no marginal rate is recorded; "
                "the transition remains pre-investor-tax.")
        else:
            tax_benefit = (
                rental_gate.deductible_against_wages * float(marginal_tax_rate))
            findings.append(
                "A potential rental tax benefit is shown separately and is "
                "not added to pre-investor-tax property cash flow.")
        if snapshot.defaults_used:
            findings.append(
                "Rental underwriting defaults used: "
                + ", ".join(snapshot.defaults_used) + ".")
    else:
        raise ReconciliationError(
            "transition.kind must be continue_renting, buy_immediately_occupy, "
            "rental_then_owner, or buy_land_continue_renting")

    return Transition(
        kind=kind,
        phases=phases,
        combined_cash_flow=sum(p.net_cash_flow for p in phases),
        occupancy_conversion_date=None if conversion is None else str(conversion),
        financing_occupancy=None if financing is None else str(financing),
        current_rental_tax_benefit=tax_benefit,
        initial_down_payment=initial_down,
        initial_closing_costs=initial_closing,
        initial_loan=initial_loan,
        owner_phase_loan=owner_phase_loan,
        investment_dscr=investment_dscr,
        investment_lender_test=(
            None if investment_lender_test is None
            else str(investment_lender_test)),
        reserve_months_assumed=reserve_months,
        blockers=blockers,
        findings=findings,
    )


def transition_from_facts(data: dict) -> Transition:
    """Resolve the rental deal and §469 activity joins from one facts tree."""
    plan = F._dig(data, "housing.transition") or {}
    label = str(plan.get("rental_deal_label") or "")
    deals = F._dig(data, "real_estate.deals") or []
    deal = next((d for d in deals if d.get("label") == label), None)
    gate = None
    participation = F._dig(data, "real_estate.participation") or {}
    if participation.get("magi") is not None:
        gate_result = R.assess_gate(
            F._dig(data, "real_estate.activities") or [],
            magi=float(participation["magi"]),
            active_participation=participation.get("active_participation"),
            hours_real_property=participation.get("hours_real_property"),
            hours_all_work=participation.get("hours_all_work"),
            grouping_election=bool(participation.get("grouping_election")),
            allowance=F._dig(data, "assumptions.passive_loss_allowance"),
            phaseout_start=F._dig(
                data, "assumptions.passive_loss_phaseout_start"),
            phaseout_end=F._dig(data, "assumptions.passive_loss_phaseout_end"),
        )
        gate = next((activity for activity in gate_result.activities
                     if activity.label == label), None)
    return build_transition(
        plan,
        purchase=F._dig(data, "housing.purchase") or {},
        monthly_current_rent=float(F._dig(data, "housing.monthly_rent")),
        rental_deal=deal,
        rental_gate=gate,
        marginal_tax_rate=F._dig(data, "assumptions.marginal_tax_rate"),
        reserve_months=F._dig(
            data, "housing.affordability.post_close_reserve_months"),
    )
