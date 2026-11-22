"""Reconciled household income, tax estimates, and annual cash flow.

This module owns reusable arithmetic only.  Callers supply every tax rule,
income component, and cash use explicitly; the library contains no household
figures and no jurisdiction table.  The state-income calculation is an
anchored estimate, not a tax-return engine: it moves a caller-supplied known
estimate at a caller-supplied marginal rate.

Housing is deliberately outside ``pre_housing_surplus``.  Rent is subtracted
once to derive renter taxable saving, which prevents an owner comparison from
quietly subtracting both rent and the full ownership cost.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite


class CashFlowError(ValueError):
    """Inputs are missing, contradictory, or arithmetically invalid."""


Bracket = tuple[float, float | None]


def _finite_number(value: float | int | None, label: str) -> float:
    if value is None:
        raise CashFlowError(f"{label} is required; unknown is not zero")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CashFlowError(f"{label} must be numeric") from exc
    if not isfinite(number):
        raise CashFlowError(f"{label} must be finite")
    return number


def _nonnegative(value: float | int | None, label: str) -> float:
    number = _finite_number(value, label)
    if number < 0:
        raise CashFlowError(f"{label} cannot be negative")
    return number


def _rate(value: float | int | None, label: str) -> float:
    number = _finite_number(value, label)
    if not 0 <= number <= 1:
        raise CashFlowError(f"{label} must be between zero and one")
    return number


def validate_brackets(brackets: Sequence[Bracket]) -> tuple[Bracket, ...]:
    """Return normalized progressive brackets after structural validation."""
    if not brackets:
        raise CashFlowError("federal tax brackets are missing")

    normalized: list[Bracket] = []
    previous_rate = -1.0
    previous_bound = 0.0
    for index, (rate, upper) in enumerate(brackets):
        r = _rate(rate, f"federal bracket {index} rate")
        if r <= previous_rate:
            raise CashFlowError("federal tax bracket rates must be increasing")
        if upper is None:
            if index != len(brackets) - 1:
                raise CashFlowError(
                    "only the final federal tax bracket may be open-ended")
            bound = None
        else:
            bound = _finite_number(
                upper, f"federal bracket {index} upper bound")
            if bound <= previous_bound:
                raise CashFlowError(
                    "federal tax bracket bounds must be strictly increasing")
            previous_bound = bound
        normalized.append((r, bound))
        previous_rate = r

    if normalized[-1][1] is not None:
        raise CashFlowError(
            "federal tax brackets need an open-ended final band")
    return tuple(normalized)


@dataclass(frozen=True)
class StateTaxAnchor:
    """Known state estimate moved by an explicit marginal rate."""

    reference_gross: float
    reference_pre_tax_contributions: float
    reference_tax: float
    marginal_rate: float

    def __post_init__(self) -> None:
        _nonnegative(self.reference_gross, "state reference gross")
        _nonnegative(
            self.reference_pre_tax_contributions,
            "state reference pre-tax contributions",
        )
        if self.reference_pre_tax_contributions > self.reference_gross:
            raise CashFlowError(
                "state reference pre-tax contributions exceed reference gross")
        _nonnegative(self.reference_tax, "state reference tax")
        _rate(self.marginal_rate, "state marginal rate")


@dataclass(frozen=True)
class PayrollTaxRules:
    """Employee-side payroll-tax inputs supplied for one tax year."""

    state_payroll_rate: float
    social_security_wage_base: float
    social_security_rate: float
    medicare_rate: float
    additional_medicare_threshold: float
    additional_medicare_rate: float

    def __post_init__(self) -> None:
        _rate(self.state_payroll_rate, "state payroll rate")
        _nonnegative(
            self.social_security_wage_base, "Social Security wage base")
        _rate(self.social_security_rate, "Social Security rate")
        _rate(self.medicare_rate, "Medicare rate")
        _nonnegative(
            self.additional_medicare_threshold,
            "additional Medicare threshold",
        )
        _rate(self.additional_medicare_rate, "additional Medicare rate")


@dataclass(frozen=True)
class ItemizedDeductionRules:
    """Federal itemized-deduction limits supplied for one tax year.

    ``salt_cap`` limits state and local taxes (income, payroll, property).
    When ``salt_phaseout_threshold`` is set, the cap falls by
    ``salt_phaseout_rate`` of AGI above the threshold, but not below
    ``salt_cap_floor``. Medical expenses count only above
    ``medical_agi_floor`` x AGI. Mortgage interest is prorated when the
    balance exceeds ``mortgage_interest_debt_limit``.

    Rules from tax year 2026 (P.L. 119-21), all optional so earlier years
    are unchanged: charitable gifts count only above ``charitable_agi_floor``
    x AGI; a household taking the standard deduction may still deduct
    charitable gifts up to ``nonitemizer_charitable_limit``; and itemized
    deductions are reduced by ``limitation_rate`` (2/37) x the lesser of the
    itemized total or AGI above ``limitation_threshold`` (where the 37%
    bracket starts, expressed as taxable income).

    Approximations, stated rather than hidden: the SALT phase-out uses AGI,
    not modified AGI (they differ only for excluded foreign income), and
    state income tax enters SALT as the year's liability, not the amount
    paid in the calendar year.
    """

    salt_cap: float
    medical_agi_floor: float
    mortgage_interest_debt_limit: float
    salt_phaseout_threshold: float | None = None
    salt_phaseout_rate: float = 0.0
    salt_cap_floor: float = 0.0
    charitable_agi_floor: float = 0.0
    nonitemizer_charitable_limit: float = 0.0
    limitation_rate: float = 0.0
    limitation_threshold: float | None = None

    def __post_init__(self) -> None:
        _nonnegative(self.salt_cap, "SALT cap")
        _rate(self.medical_agi_floor, "medical AGI floor")
        _nonnegative(
            self.mortgage_interest_debt_limit, "mortgage interest debt limit")
        if self.salt_phaseout_threshold is not None:
            _nonnegative(self.salt_phaseout_threshold, "SALT phase-out threshold")
        _rate(self.salt_phaseout_rate, "SALT phase-out rate")
        _nonnegative(self.salt_cap_floor, "SALT cap floor")
        if self.salt_cap_floor > self.salt_cap:
            raise CashFlowError("SALT cap floor exceeds the SALT cap")
        _rate(self.charitable_agi_floor, "charitable AGI floor")
        _nonnegative(self.nonitemizer_charitable_limit,
                     "non-itemizer charitable limit")
        _rate(self.limitation_rate, "itemized limitation rate")
        if self.limitation_rate and self.limitation_threshold is None:
            raise CashFlowError(
                "itemized limitation rate needs a limitation threshold")
        if self.limitation_threshold is not None:
            _nonnegative(self.limitation_threshold, "itemized limitation threshold")

    def limitation(self, itemized: float, adjusted_gross_income: float) -> float:
        """Reduction of the itemized total for top-bracket households."""
        if not self.limitation_rate or self.limitation_threshold is None:
            return 0.0
        over = max(0.0, adjusted_gross_income - self.limitation_threshold)
        return self.limitation_rate * min(itemized, over)

    def effective_salt_cap(self, adjusted_gross_income: float) -> float:
        if self.salt_phaseout_threshold is None:
            return self.salt_cap
        excess = max(0.0, adjusted_gross_income - self.salt_phaseout_threshold)
        return max(self.salt_cap_floor,
                   self.salt_cap - excess * self.salt_phaseout_rate)


@dataclass(frozen=True)
class StateItemizedDeductionRules:
    """State itemized deductions layered on the state tax anchor.

    The anchor is assumed to reflect ``standard_deduction``; itemizing above
    it lowers state tax by the anchor's marginal rate. Defaults follow the
    common pattern of states (such as California) that do not allow their
    own income tax or payroll tax as a deduction and do not cap property
    tax. ``phaseout_*`` optionally reduces itemized deductions above an AGI
    threshold by ``phaseout_rate`` of the excess, limited to
    ``phaseout_max_share`` of the itemized total.
    """

    standard_deduction: float
    medical_agi_floor: float
    mortgage_interest_debt_limit: float
    salt_cap: float | None = None
    phaseout_threshold: float | None = None
    phaseout_rate: float = 0.0
    phaseout_max_share: float = 0.0

    def __post_init__(self) -> None:
        _nonnegative(self.standard_deduction, "state standard deduction")
        _rate(self.medical_agi_floor, "state medical AGI floor")
        _nonnegative(self.mortgage_interest_debt_limit,
                     "state mortgage interest debt limit")
        if self.salt_cap is not None:
            _nonnegative(self.salt_cap, "state SALT cap")
        if self.phaseout_threshold is not None:
            _nonnegative(self.phaseout_threshold, "state phase-out threshold")
        _rate(self.phaseout_rate, "state phase-out rate")
        _rate(self.phaseout_max_share, "state phase-out maximum share")


@dataclass(frozen=True)
class ItemizedDeductionInputs:
    """A household's itemizable amounts for one year, in nominal dollars.

    State income tax and state payroll tax come from the estimate itself and
    are added to the SALT total automatically; list only other state and
    local taxes here.
    """

    medical_expenses: float = 0.0
    property_tax: float = 0.0
    other_state_local_taxes: float = 0.0
    mortgage_interest: float = 0.0
    #: Average acquisition debt for the year. Required whenever
    #: ``mortgage_interest`` is positive — an unknown balance is not zero,
    #: and zero would silently skip the debt-limit proration.
    mortgage_balance: float | None = None
    charitable: float = 0.0
    other_itemized: float = 0.0

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if value is None:
                continue
            _nonnegative(value, name.replace("_", " "))
        if self.mortgage_interest > 0 and self.mortgage_balance is None:
            raise CashFlowError(
                "mortgage interest needs a mortgage balance for the debt limit")


@dataclass(frozen=True)
class TaxRules:
    """Explicit rules for a deterministic annual tax estimate.

    ``itemized`` is optional. Without it, or without itemized inputs, the
    estimate uses the standard deduction exactly as before.
    """

    federal_standard_deduction: float
    federal_brackets: tuple[Bracket, ...]
    state_anchor: StateTaxAnchor
    payroll: PayrollTaxRules
    itemized: ItemizedDeductionRules | None = None
    state_itemized: StateItemizedDeductionRules | None = None

    def __post_init__(self) -> None:
        _nonnegative(
            self.federal_standard_deduction, "federal standard deduction")
        object.__setattr__(
            self, "federal_brackets", validate_brackets(self.federal_brackets))


@dataclass(frozen=True)
class TaxEstimate:
    gross: float
    pre_tax_contributions: float
    adjusted_gross_income: float
    standard_deduction: float
    taxable_income: float
    federal_income_tax: float
    state_income_tax: float
    state_payroll_tax: float
    federal_payroll_tax: float
    total: float
    itemized_deduction: float = 0.0
    deduction: float = 0.0
    itemizes: bool = False
    state_itemized_deduction: float = 0.0
    state_deduction: float = 0.0
    state_itemizes: bool = False

    @property
    def effective_rate(self) -> float:
        return self.total / self.gross if self.gross else 0.0


@dataclass(frozen=True)
class CashFlowInputs:
    """Annual uses shared by each income case, in nominal dollars."""

    pre_tax_retirement_contributions: float
    employee_retirement_contributions: float
    employer_retirement_contributions: float
    ira_contributions: float
    other_payroll_deductions: float
    non_housing_spending: float
    temporary_obligations: float
    other_committed: float
    annual_rent: float
    redirected_savings_after_obligations: float

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            _nonnegative(value, name.replace("_", " "))
        if (
            self.pre_tax_retirement_contributions
            > self.employee_retirement_contributions
        ):
            raise CashFlowError(
                "pre-tax retirement contributions exceed total employee "
                "retirement contributions")
        if self.redirected_savings_after_obligations > self.temporary_obligations:
            raise CashFlowError(
                "redirected savings exceed the obligations that expire")


@dataclass(frozen=True)
class CashFlowScenario:
    key: str
    gross: float
    taxes: TaxEstimate
    employee_retirement_contributions: float
    employer_retirement_contributions: float
    ira_contributions: float
    other_payroll_deductions: float
    non_housing_spending: float
    temporary_obligations: float
    other_committed: float
    annual_rent: float
    after_tax_cash_income: float
    cash_after_payroll_and_employee_retirement: float
    pre_housing_surplus: float
    renter_taxable_savings: float
    total_savings_during_obligations: float
    total_savings_after_obligations: float

    @property
    def savings_rate_during_obligations(self) -> float:
        return (
            self.total_savings_during_obligations / self.gross
            if self.gross
            else 0.0
        )

    @property
    def savings_rate_after_obligations(self) -> float:
        return (
            self.total_savings_after_obligations / self.gross
            if self.gross
            else 0.0
        )


def income_scenarios(
    components_by_scenario: Mapping[str, Mapping[str, float | int | None]],
    *,
    current_key: str = "current",
    recorded_current: float | None = None,
) -> dict[str, float]:
    """Sum named income components and optionally reconcile the current total."""
    if not components_by_scenario:
        raise CashFlowError("income scenarios are missing")

    totals: dict[str, float] = {}
    for key, components in components_by_scenario.items():
        if not components:
            raise CashFlowError(f"{key} income components are missing")
        unknown = sorted(name for name, value in components.items() if value is None)
        if unknown:
            raise CashFlowError(
                f"{key} income components are unknown for {', '.join(unknown)}")
        values = [_nonnegative(value, f"{key} {name}")
                  for name, value in components.items()]
        totals[str(key)] = sum(values)

    if recorded_current is not None:
        if current_key not in totals:
            raise CashFlowError(f"current income scenario {current_key!r} is missing")
        recorded = _nonnegative(recorded_current, "recorded current income")
        if abs(recorded - totals[current_key]) > 1:
            raise CashFlowError(
                f"current income {recorded:,.0f} disagrees with components "
                f"{totals[current_key]:,.0f}")
    return totals


def progressive_tax(taxable_income: float, brackets: Sequence[Bracket]) -> float:
    """Tax an amount through validated marginal brackets."""
    taxable = max(0.0, _finite_number(taxable_income, "taxable income"))
    rows = validate_brackets(brackets)
    lower = 0.0
    total = 0.0
    for rate, upper in rows:
        top = taxable if upper is None else min(taxable, upper)
        total += max(0.0, top - lower) * rate
        if upper is None or taxable <= upper:
            break
        lower = upper
    return total


def itemized_deduction(
    *,
    adjusted_gross_income: float,
    state_income_tax: float,
    state_payroll_tax: float,
    rules: ItemizedDeductionRules,
    inputs: ItemizedDeductionInputs,
) -> float:
    """Federal itemized total under the supplied caps and floors."""
    agi = max(0.0, _finite_number(adjusted_gross_income, "adjusted gross income"))
    salt = min(
        rules.effective_salt_cap(agi),
        _nonnegative(state_income_tax, "state income tax")
        + _nonnegative(state_payroll_tax, "state payroll tax")
        + inputs.property_tax
        + inputs.other_state_local_taxes,
    )
    medical = max(0.0, inputs.medical_expenses - rules.medical_agi_floor * agi)
    interest = _prorate_interest(inputs.mortgage_interest,
                                 inputs.mortgage_balance,
                                 rules.mortgage_interest_debt_limit)
    charitable = max(0.0, inputs.charitable - rules.charitable_agi_floor * agi)
    return salt + medical + interest + charitable + inputs.other_itemized


def _prorate_interest(interest: float, balance: float | None, limit: float) -> float:
    if interest == 0 or limit == 0:
        return 0.0
    if balance is not None and balance > limit:
        return interest * limit / balance
    return interest


def state_itemized_deduction(
    *,
    adjusted_gross_income: float,
    rules: StateItemizedDeductionRules,
    inputs: ItemizedDeductionInputs,
) -> float:
    """State itemized total. State income and payroll tax are excluded."""
    agi = max(0.0, _finite_number(adjusted_gross_income, "adjusted gross income"))
    local = inputs.property_tax + inputs.other_state_local_taxes
    if rules.salt_cap is not None:
        local = min(local, rules.salt_cap)
    medical = max(0.0, inputs.medical_expenses - rules.medical_agi_floor * agi)
    interest = _prorate_interest(inputs.mortgage_interest,
                                 inputs.mortgage_balance,
                                 rules.mortgage_interest_debt_limit)
    total = local + medical + interest + inputs.charitable + inputs.other_itemized
    if rules.phaseout_threshold is not None and agi > rules.phaseout_threshold:
        # The share cap excludes medical expenses (as in former IRC §68(c)).
        reduction = min((agi - rules.phaseout_threshold) * rules.phaseout_rate,
                        (total - medical) * rules.phaseout_max_share)
        total -= reduction
    return total


def estimate_tax(
    gross: float,
    *,
    pre_tax_contributions: float,
    rules: TaxRules,
    itemized_inputs: ItemizedDeductionInputs | None = None,
    agi_adjustments: float = 0.0,
) -> TaxEstimate:
    """Estimate federal, state, and employee payroll taxes from explicit rules.

    ``agi_adjustments`` moves AGI and state taxable income without touching
    payroll tax — for example a business loss (negative) or non-wage income
    (positive). Itemizing is used only when ``rules.itemized`` and
    ``itemized_inputs`` are both supplied and the itemized total exceeds the
    standard deduction. State itemizing applies when ``rules.state_itemized``
    and ``itemized_inputs`` are supplied: the anchor is assumed to reflect
    the state standard deduction, and any excess lowers state tax at the
    anchor's marginal rate. State tax is computed first, so the federal SALT
    deduction sees the post-itemizing state figure.
    """
    gross = _nonnegative(gross, "gross income")
    pre_tax = _nonnegative(pre_tax_contributions, "pre-tax contributions")
    if pre_tax > gross:
        raise CashFlowError("pre-tax contributions exceed gross income")
    adjustment = _finite_number(agi_adjustments, "AGI adjustments")

    adjusted_gross = gross - pre_tax + adjustment

    anchor = rules.state_anchor
    reference_taxable = (
        anchor.reference_gross - anchor.reference_pre_tax_contributions)
    state_itemized = 0.0
    state_extra = 0.0
    state_deduction = 0.0
    if rules.state_itemized is not None and itemized_inputs is not None:
        state_itemized = state_itemized_deduction(
            adjusted_gross_income=adjusted_gross,
            rules=rules.state_itemized,
            inputs=itemized_inputs,
        )
        state_deduction = max(rules.state_itemized.standard_deduction,
                              state_itemized)
        state_extra = state_deduction - rules.state_itemized.standard_deduction
    elif rules.state_itemized is not None:
        state_deduction = rules.state_itemized.standard_deduction
    current_taxable = adjusted_gross - state_extra
    state_income = max(
        0.0,
        anchor.reference_tax
        + (current_taxable - reference_taxable) * anchor.marginal_rate,
    )

    payroll = rules.payroll
    state_payroll = gross * payroll.state_payroll_rate

    itemized = 0.0
    if rules.itemized is not None and itemized_inputs is not None:
        itemized = itemized_deduction(
            adjusted_gross_income=adjusted_gross,
            state_income_tax=state_income,
            state_payroll_tax=state_payroll,
            rules=rules.itemized,
            inputs=itemized_inputs,
        )
    if itemized and rules.itemized is not None:
        itemized -= rules.itemized.limitation(itemized, adjusted_gross)
    standard = rules.federal_standard_deduction
    if (rules.itemized is not None and itemized_inputs is not None
            and itemized <= standard):
        standard += min(itemized_inputs.charitable,
                        rules.itemized.nonitemizer_charitable_limit)
    deduction = max(standard, itemized)
    taxable = max(0.0, adjusted_gross - deduction)
    federal = progressive_tax(taxable, rules.federal_brackets)

    social_security = (
        min(gross, payroll.social_security_wage_base)
        * payroll.social_security_rate
    )
    medicare = gross * payroll.medicare_rate
    additional_medicare = max(
        0.0, gross - payroll.additional_medicare_threshold
    ) * payroll.additional_medicare_rate
    federal_payroll = social_security + medicare + additional_medicare
    total = federal + state_income + state_payroll + federal_payroll

    return TaxEstimate(
        gross=gross,
        pre_tax_contributions=pre_tax,
        adjusted_gross_income=adjusted_gross,
        standard_deduction=rules.federal_standard_deduction,
        taxable_income=taxable,
        federal_income_tax=federal,
        state_income_tax=state_income,
        state_payroll_tax=state_payroll,
        federal_payroll_tax=federal_payroll,
        total=total,
        itemized_deduction=itemized,
        deduction=deduction,
        itemizes=itemized > standard,
        state_itemized_deduction=state_itemized,
        state_deduction=state_deduction,
        state_itemizes=state_extra > 0,
    )


def build_cash_flow_scenarios(
    incomes: Mapping[str, float],
    *,
    tax_rules: TaxRules,
    cash: CashFlowInputs,
    itemized_inputs: ItemizedDeductionInputs | None = None,
    agi_adjustments: float = 0.0,
) -> dict[str, CashFlowScenario]:
    """Build reconciled scenarios from named gross incomes and shared uses.

    ``itemized_inputs`` and ``agi_adjustments`` pass through to
    ``estimate_tax``. A business loss belongs in ``agi_adjustments`` for its
    tax effect; its cash cost belongs in ``cash.other_committed``.
    """
    if not incomes:
        raise CashFlowError("income scenarios are missing")

    out: dict[str, CashFlowScenario] = {}
    for key, raw_gross in incomes.items():
        gross = _nonnegative(raw_gross, f"{key} gross income")
        taxes = estimate_tax(
            gross,
            pre_tax_contributions=cash.pre_tax_retirement_contributions,
            rules=tax_rules,
            itemized_inputs=itemized_inputs,
            agi_adjustments=agi_adjustments,
        )
        after_tax = gross - taxes.total
        after_payroll_and_retirement = (
            after_tax
            - cash.employee_retirement_contributions
            - cash.other_payroll_deductions
        )
        pre_housing = (
            after_payroll_and_retirement
            - cash.non_housing_spending
            - cash.temporary_obligations
            - cash.ira_contributions
            - cash.other_committed
        )
        renter_taxable = pre_housing - cash.annual_rent
        during = (
            cash.employee_retirement_contributions
            + cash.employer_retirement_contributions
            + cash.ira_contributions
            + renter_taxable
        )
        out[str(key)] = CashFlowScenario(
            key=str(key),
            gross=gross,
            taxes=taxes,
            employee_retirement_contributions=(
                cash.employee_retirement_contributions),
            employer_retirement_contributions=(
                cash.employer_retirement_contributions),
            ira_contributions=cash.ira_contributions,
            other_payroll_deductions=cash.other_payroll_deductions,
            non_housing_spending=cash.non_housing_spending,
            temporary_obligations=cash.temporary_obligations,
            other_committed=cash.other_committed,
            annual_rent=cash.annual_rent,
            after_tax_cash_income=after_tax,
            cash_after_payroll_and_employee_retirement=(
                after_payroll_and_retirement),
            pre_housing_surplus=pre_housing,
            renter_taxable_savings=renter_taxable,
            total_savings_during_obligations=during,
            total_savings_after_obligations=(
                during + cash.redirected_savings_after_obligations),
        )
    return out
