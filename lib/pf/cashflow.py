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


class CashFlowError(ValueError):
    """Inputs are missing, contradictory, or arithmetically invalid."""


Bracket = tuple[float, float | None]


def _nonnegative(value: float | int | None, label: str) -> float:
    if value is None:
        raise CashFlowError(f"{label} is required; unknown is not zero")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CashFlowError(f"{label} must be numeric") from exc
    if number < 0:
        raise CashFlowError(f"{label} cannot be negative")
    return number


def _rate(value: float | int | None, label: str) -> float:
    if value is None:
        raise CashFlowError(f"{label} is required; unknown is not zero")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise CashFlowError(f"{label} must be numeric") from exc
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
            bound = float(upper)
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
class TaxRules:
    """Explicit rules for a deterministic annual tax estimate."""

    federal_standard_deduction: float
    federal_brackets: tuple[Bracket, ...]
    state_anchor: StateTaxAnchor
    payroll: PayrollTaxRules

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
        if self.pre_tax_retirement_contributions > self.employee_retirement_contributions:
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
        return self.total_savings_during_obligations / self.gross

    @property
    def savings_rate_after_obligations(self) -> float:
        return self.total_savings_after_obligations / self.gross


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
    taxable = max(0.0, float(taxable_income))
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


def estimate_tax(
    gross: float,
    *,
    pre_tax_contributions: float,
    rules: TaxRules,
) -> TaxEstimate:
    """Estimate federal, state, and employee payroll taxes from explicit rules."""
    gross = _nonnegative(gross, "gross income")
    pre_tax = _nonnegative(pre_tax_contributions, "pre-tax contributions")
    if pre_tax > gross:
        raise CashFlowError("pre-tax contributions exceed gross income")

    adjusted_gross = gross - pre_tax
    taxable = max(0.0, adjusted_gross - rules.federal_standard_deduction)
    federal = progressive_tax(taxable, rules.federal_brackets)

    anchor = rules.state_anchor
    reference_taxable = (
        anchor.reference_gross - anchor.reference_pre_tax_contributions)
    current_taxable = gross - pre_tax
    state_income = max(
        0.0,
        anchor.reference_tax
        + (current_taxable - reference_taxable) * anchor.marginal_rate,
    )

    payroll = rules.payroll
    state_payroll = gross * payroll.state_payroll_rate
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
    )


def build_cash_flow_scenarios(
    incomes: Mapping[str, float],
    *,
    tax_rules: TaxRules,
    cash: CashFlowInputs,
) -> dict[str, CashFlowScenario]:
    """Build reconciled scenarios from named gross incomes and shared uses."""
    if not incomes:
        raise CashFlowError("income scenarios are missing")

    out: dict[str, CashFlowScenario] = {}
    for key, raw_gross in incomes.items():
        gross = _nonnegative(raw_gross, f"{key} gross income")
        taxes = estimate_tax(
            gross,
            pre_tax_contributions=cash.pre_tax_retirement_contributions,
            rules=tax_rules,
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
