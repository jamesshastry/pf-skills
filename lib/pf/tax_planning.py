"""History-anchored tax planning without pretending to prepare a return.

Filed-return history establishes the household's actual tax baseline. Current
facts then expose a small set of tax-reduction candidates whose arithmetic can
be explained: pre-tax contribution room, HSA room, loss harvesting, charitable
giving, and a low-income Roth-conversion window. Statutory limits and personal
rates are supplied elsewhere; this module does not carry a tax table.

Positive ``current_tax_savings`` means lower estimated current-year tax.
Negative means the strategy deliberately raises current tax in exchange for a
possible later benefit. Opportunity figures are alternatives, not a total.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from . import charity as G
from . import limits as L


class TaxPlanningError(ValueError):
    """Tax history or planning inputs are incomplete or contradictory."""


def _number(value: Any, label: str) -> float:
    if value is None:
        raise TaxPlanningError(f"{label} is required; unknown is not zero")
    if isinstance(value, bool):
        raise TaxPlanningError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TaxPlanningError(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise TaxPlanningError(f"{label} must be finite")
    return number


def _nonnegative(value: Any, label: str) -> float:
    number = _number(value, label)
    if number < 0:
        raise TaxPlanningError(f"{label} cannot be negative")
    return number


def _rate(value: Any, label: str) -> float:
    number = _number(value, label)
    if not 0 <= number <= 1:
        raise TaxPlanningError(f"{label} must be between zero and one")
    return number


def _optional_nonnegative(value: Any, label: str) -> float | None:
    return None if value is None else _nonnegative(value, label)


def _optional_rate(value: Any, label: str) -> float | None:
    return None if value is None else _rate(value, label)


def _year(value: Any, label: str) -> int:
    number = _nonnegative(value, label)
    year = int(number)
    if number != year or not 1900 <= year <= 9999:
        raise TaxPlanningError(f"{label} must be a four-digit tax year")
    return year


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaxPlanningError(f"{label} is required")
    return value.strip()


def _combined_rate(*rates: float, label: str) -> float:
    combined = sum(rates)
    if combined > 1:
        raise TaxPlanningError(f"{label} cannot exceed one")
    return combined


@dataclass(frozen=True)
class TaxYear:
    """Comparable figures from one filed return or current projection."""

    tax_year: int
    adjusted_gross_income: float
    taxable_income: float
    federal_total_tax: float
    state_income_tax: float
    filing_status: str
    state: str
    payments: float | None = None
    projected: bool = False

    @property
    def combined_tax(self) -> float:
        return self.federal_total_tax + self.state_income_tax

    @property
    def effective_rate(self) -> float:
        if not self.adjusted_gross_income:
            return 0.0
        return self.combined_tax / self.adjusted_gross_income

    @property
    def payment_gap(self) -> float | None:
        if self.payments is None:
            return None
        return self.combined_tax - self.payments


@dataclass(frozen=True)
class TaxHistory:
    """Filed returns ordered by tax year."""

    years: tuple[TaxYear, ...]

    @property
    def weighted_effective_rate(self) -> float:
        income = sum(row.adjusted_gross_income for row in self.years)
        return sum(row.combined_tax for row in self.years) / income if income else 0.0

    @property
    def median_agi(self) -> float:
        return float(statistics.median(
            row.adjusted_gross_income for row in self.years))

    @property
    def effective_rate_change(self) -> float | None:
        if len(self.years) < 2:
            return None
        return self.years[-1].effective_rate - self.years[0].effective_rate

    @property
    def agi_change(self) -> float | None:
        if len(self.years) < 2:
            return None
        return (
            self.years[-1].adjusted_gross_income
            - self.years[0].adjusted_gross_income
        )

    @property
    def regimes(self) -> tuple[tuple[str, str], ...]:
        return tuple(sorted({
            (row.filing_status, row.state) for row in self.years
        }))


@dataclass(frozen=True)
class TaxOpportunity:
    """One tax move and the costs that prevent it being a free lunch."""

    key: str
    action: str
    amount: float | None
    current_tax_savings: float | None
    future_tax_savings: float | None
    confidence: str
    reason: str
    tradeoffs: tuple[str, ...]
    related_skill: str


@dataclass
class TaxPlan:
    history: TaxHistory
    current: TaxYear
    opportunities: list[TaxOpportunity] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)


def _parse_row(row: Mapping[str, Any], *, projected: bool) -> TaxYear:
    prefix = "current projection" if projected else "historical return"
    if projected:
        names = {
            "adjusted_gross_income": "projected_adjusted_gross_income",
            "taxable_income": "projected_taxable_income",
            "federal_total_tax": "projected_federal_total_tax",
            "state_income_tax": "projected_state_income_tax",
            "payments": "projected_payments",
        }
    else:
        names = {
            "adjusted_gross_income": "adjusted_gross_income",
            "taxable_income": "taxable_income",
            "federal_total_tax": "federal_total_tax",
            "state_income_tax": "state_income_tax",
            "payments": "payments",
        }

    agi = _nonnegative(row.get(names["adjusted_gross_income"]), f"{prefix} AGI")
    taxable = _nonnegative(
        row.get(names["taxable_income"]), f"{prefix} taxable income")
    if taxable > agi:
        raise TaxPlanningError(f"{prefix} taxable income exceeds AGI")
    payments = _optional_nonnegative(
        row.get(names["payments"]), f"{prefix} payments")
    return TaxYear(
        tax_year=_year(row.get("tax_year"), f"{prefix} tax year"),
        adjusted_gross_income=agi,
        taxable_income=taxable,
        federal_total_tax=_nonnegative(
            row.get(names["federal_total_tax"]),
            f"{prefix} federal total tax",
        ),
        state_income_tax=_nonnegative(
            row.get(names["state_income_tax"]),
            f"{prefix} state income tax",
        ),
        filing_status=_text(row.get("filing_status"), f"{prefix} filing status"),
        state=_text(row.get("state"), f"{prefix} state"),
        payments=payments,
        projected=projected,
    )


def parse_history(rows: Sequence[Mapping[str, Any]]) -> TaxHistory:
    """Normalize filed returns without changing their input mappings."""
    if not rows:
        raise TaxPlanningError("at least one historical tax return is required")
    years = tuple(sorted(
        (_parse_row(row, projected=False) for row in rows),
        key=lambda row: row.tax_year,
    ))
    duplicates = sorted({
        row.tax_year for row in years
        if sum(other.tax_year == row.tax_year for other in years) > 1
    })
    if duplicates:
        raise TaxPlanningError(
            "duplicate historical tax years: "
            + ", ".join(str(year) for year in duplicates)
        )
    return TaxHistory(years)


def _opportunity(
    key: str,
    action: str,
    *,
    amount: float | None,
    current_tax_savings: float | None,
    future_tax_savings: float | None = None,
    confidence: str = "estimated",
    reason: str,
    tradeoffs: Sequence[str],
    related_skill: str,
) -> TaxOpportunity:
    return TaxOpportunity(
        key=key,
        action=action,
        amount=amount,
        current_tax_savings=current_tax_savings,
        future_tax_savings=future_tax_savings,
        confidence=confidence,
        reason=reason,
        tradeoffs=tuple(tradeoffs),
        related_skill=related_skill,
    )


def _primary_age(data: Mapping[str, Any]) -> int | None:
    members = data.get("household", {}).get("members", [])
    primary = next(
        (row for row in members if row.get("role") == "primary"), None)
    if not primary or primary.get("age") is None:
        return None
    age = _nonnegative(primary["age"], "primary age")
    if age != int(age):
        raise TaxPlanningError("primary age must be a whole number")
    return int(age)


def _contribution_opportunities(
    data: Mapping[str, Any],
    current_cfg: Mapping[str, Any],
    federal_rate: float,
    state_rate: float,
    findings: list[str],
) -> list[TaxOpportunity]:
    contributions = data.get("contributions") or {}
    tax_year = _year(current_cfg.get("tax_year"), "current projection tax year")
    contribution_year = contributions.get("year")
    if (
        contribution_year is not None
        and _year(contribution_year, "contribution year") != tax_year
    ):
        raise TaxPlanningError(
            "contribution year does not match the current projection tax year")

    limits = L.for_year(tax_year)
    if not limits.known:
        findings.append(
            f"Contribution limits for {tax_year} are unavailable; retirement "
            "and HSA opportunities are not sized."
        )
        return []

    age = _primary_age(data)
    if age is None:
        findings.append(
            "Primary age is not recorded; catch-up contribution room is not "
            "sized."
        )
        return []

    opportunities: list[TaxOpportunity] = []
    state_flag = current_cfg.get("retirement_contribution_state_deductible")
    deduction_rate = _combined_rate(
        federal_rate,
        state_rate if state_flag is True else 0.0,
        label="combined retirement deduction rate",
    )
    state_note = (
        "State deduction included from the recorded treatment."
        if state_flag is True
        else "State treatment is excluded unless explicitly recorded as deductible."
    )

    plan = contributions.get("employer_plan") or {}
    if plan:
        raw_pre_tax = plan.get("employee_pre_tax")
        raw_roth = plan.get("employee_roth")
        if raw_pre_tax is None or raw_roth is None:
            findings.append(
                "Employer-plan pre-tax or Roth contributions are unknown; "
                "current-year deferral choices are not sized."
            )
        else:
            pre_tax = _nonnegative(raw_pre_tax, "employee pre-tax contribution")
            roth = _nonnegative(raw_roth, "employee Roth contribution")
            ceiling = (limits.elective_deferral or 0) + L.catch_up_for_age(
                age, limits)
            used = pre_tax + roth
            if used > ceiling:
                findings.append(
                    "Recorded elective deferrals exceed the supplied annual "
                    "limit; reconcile them before changing the election."
                )
            else:
                headroom = ceiling - used
                if headroom > 0:
                    opportunities.append(_opportunity(
                        "pre-tax-deferral",
                        "Increase pre-tax employer-plan deferrals",
                        amount=headroom,
                        current_tax_savings=headroom * deduction_rate,
                        reason=(
                            f"{headroom:,.0f} of elective-deferral room remains "
                            f"for {tax_year}."
                        ),
                        tradeoffs=(
                            "Reduces spendable cash dollar for dollar.",
                            "Defers rather than eliminates ordinary income tax; "
                            "withdrawals and future rates still matter.",
                            state_note,
                            "Spread changes across pay periods so employer match "
                            "is not accidentally forfeited.",
                        ),
                        related_skill="contribution-space-audit",
                    ))
                if roth > 0:
                    remaining = _optional_nonnegative(
                        current_cfg.get("remaining_roth_deferrals"),
                        "remaining Roth deferrals",
                    )
                    if remaining is None:
                        opportunities.append(_opportunity(
                            "roth-to-pretax",
                            "Compare future Roth deferrals with pre-tax deferrals",
                            amount=None,
                            current_tax_savings=None,
                            confidence="conditional",
                            reason=(
                                f"{roth:,.0f} of Roth deferrals is recorded, but "
                                "the amount remaining in future payrolls is not."
                            ),
                            tradeoffs=(
                                "Past Roth deferrals cannot be changed retroactively.",
                                "A future switch lowers current tax but gives up "
                                "tax-free qualified withdrawals.",
                                "The decision turns on current versus future "
                                "marginal rates, not the current deduction alone.",
                                state_note,
                            ),
                            related_skill="contribution-space-audit",
                        ))
                    elif remaining > 0:
                        opportunities.append(_opportunity(
                            "roth-to-pretax",
                            "Compare future Roth deferrals with pre-tax deferrals",
                            amount=remaining,
                            current_tax_savings=remaining * deduction_rate,
                            reason=(
                                f"{remaining:,.0f} of future Roth deferrals is "
                                "recorded and can change tax timing without "
                                "changing total saving."
                            ),
                            tradeoffs=(
                                "Past Roth deferrals cannot be changed retroactively.",
                                "Lowers current tax but gives up tax-free qualified "
                                "withdrawals on the shifted amount.",
                                "The decision turns on current versus future "
                                "marginal rates, not the current deduction alone.",
                                state_note,
                            ),
                            related_skill="contribution-space-audit",
                        ))

    hsa = contributions.get("hsa") or {}
    if hsa and hsa.get("eligible") is True:
        if hsa.get("coverage") is None or hsa.get("contribution") is None:
            findings.append(
                "HSA eligibility is recorded but coverage or contributions "
                "are unknown; HSA room is not sized."
            )
        else:
            hsa_limit = L.hsa_space(hsa.get("coverage"), age, limits)
            used = _nonnegative(hsa.get("contribution"), "HSA contribution")
            if hsa_limit is not None and used > hsa_limit:
                findings.append(
                    "Recorded HSA contributions exceed the supplied annual "
                    "limit; reconcile them before changing the election."
                )
            elif hsa_limit is not None and used < hsa_limit:
                headroom = hsa_limit - used
                hsa_state = current_cfg.get("hsa_state_deductible")
                hsa_rate = _combined_rate(
                    federal_rate,
                    state_rate if hsa_state is True else 0.0,
                    label="combined HSA deduction rate",
                )
                hsa_state_note = (
                    "State deduction included from the recorded treatment."
                    if hsa_state is True
                    else "State and payroll-tax effects are not included."
                )
                opportunities.append(_opportunity(
                    "hsa-contribution",
                    "Fill available HSA contribution room",
                    amount=headroom,
                    current_tax_savings=headroom * hsa_rate,
                    reason=(
                        f"{headroom:,.0f} of recorded HSA room remains for "
                        f"{tax_year}."
                    ),
                    tradeoffs=(
                        "Requires current cash and continued HSA eligibility.",
                        "Non-medical withdrawals do not receive the full tax "
                        "advantage.",
                        hsa_state_note,
                    ),
                    related_skill="hsa-review",
                ))
    return opportunities


def _loss_harvest_opportunity(
    data: Mapping[str, Any],
    current_cfg: Mapping[str, Any],
    findings: list[str],
) -> TaxOpportunity | None:
    losses: list[tuple[str, float, bool | None]] = []
    for account in data.get("household", {}).get("balance_sheet", []):
        if account.get("account_type") != "taxable":
            continue
        for lot in account.get("tax_lots") or []:
            label = str(lot.get("ticker") or lot.get("name") or "tax lot")
            if lot.get("value") is None or lot.get("cost_basis") is None:
                findings.append(
                    f"{label} lacks value or basis and is excluded from the "
                    "loss-harvest screen."
                )
                continue
            value = _nonnegative(lot.get("value"), f"{label} value")
            basis = _nonnegative(lot.get("cost_basis"), f"{label} cost basis")
            if basis > value:
                losses.append((
                    label,
                    basis - value,
                    account.get("wash_sale_policy_applied"),
                ))
    if not losses:
        return None

    available = sum(loss for _name, loss, _policy in losses)
    usable = _optional_nonnegative(
        current_cfg.get("loss_harvest_usable_amount"),
        "loss-harvest usable amount",
    )
    rate = _optional_rate(
        current_cfg.get("loss_harvest_marginal_rate"),
        "loss-harvest marginal rate",
    )
    tax_savings = (
        min(available, usable) * rate
        if usable is not None and rate is not None
        else None
    )
    labels = ", ".join(name for name, _loss, _policy in losses)
    policy_unknown = any(policy is not True for _name, _loss, policy in losses)
    return _opportunity(
        "tax-loss-harvest",
        "Review taxable loss lots before year end",
        amount=available,
        current_tax_savings=tax_savings,
        confidence="conditional" if policy_unknown else "estimated",
        reason=(
            f"Recorded taxable lots contain {available:,.0f} of unrealized "
            f"losses across {labels}."
        ),
        tradeoffs=(
            "A harvested loss is tax timing, not an economic profit; future "
            "gains and carryforwards determine when it is used.",
            "Avoid replacement purchases across every household account for "
            "the wash-sale window, including retirement and spouse accounts.",
            "Use the recorded usable amount and marginal rate from tax "
            "software; this planner does not perform capital-gain netting.",
        ),
        related_skill="wash-sale-policy",
    )


def _charitable_opportunities(
    data: Mapping[str, Any],
    federal_rate: float,
) -> list[TaxOpportunity]:
    charity = data.get("charity") or {}
    candidates = charity.get("candidate_holdings") or []
    assumptions = data.get("assumptions") or {}
    ltcg_rate = _optional_rate(
        assumptions.get("ltcg_rate"), "long-term capital-gains rate")
    niit_rate = _optional_rate(
        assumptions.get("niit_rate"), "net investment income tax rate")
    if ltcg_rate is not None and niit_rate is not None:
        _combined_rate(
            ltcg_rate,
            niit_rate,
            label="combined capital-gains rate",
        )
    review = G.review_gifts(
        candidates,
        ltcg_rate=ltcg_rate,
        niit_rate=niit_rate,
    )
    opportunities: list[TaxOpportunity] = []
    eligible = [
        line for line in review.lines
        if line.long_term is True
        and line.gain is not None
        and line.gain > 0
        and line.gain_tax_avoided is not None
    ]
    annual_gift = charity.get("annual_gift")
    if eligible and annual_gift is not None:
        intended = _nonnegative(annual_gift, "annual charitable gift")
        remaining = intended
        amount = 0.0
        avoided = 0.0
        ranked = sorted(
            eligible,
            key=lambda line: (
                -((line.gain_tax_avoided or 0.0) / line.value),
                line.name,
            ),
        )
        for line in ranked:
            allocated = min(line.value, remaining)
            amount += allocated
            avoided += allocated * (
                (line.gain_tax_avoided or 0.0) / line.value)
            remaining -= allocated
            if remaining <= 0:
                break
    else:
        amount = 0.0
        avoided = 0.0
    if amount > 0:
        opportunities.append(_opportunity(
            "appreciated-charity",
            "Donate intended gifts with appreciated long-term lots",
            amount=amount,
            current_tax_savings=avoided,
            reason=(
                "Giving the recorded long-term lots in kind avoids their "
                "embedded gain without changing the charitable deduction."
            ),
            tradeoffs=(
                "The gift is irrevocable; charitable intent sets its size.",
                "Confirm holding period, basis, recipient eligibility, and "
                "AGI deduction limits before transferring.",
                "Transfer shares directly; selling first realizes the gain.",
            ),
            related_skill="charitable-giving-strategy",
        ))

    standard = assumptions.get("standard_deduction")
    other = assumptions.get("other_itemized_deductions")
    if all(value is not None for value in (standard, other, annual_gift)):
        bunch = G.best_bunch(
            standard_deduction=_nonnegative(
                standard, "standard deduction"),
            other_itemized=_nonnegative(other, "other itemized deductions"),
            annual_gift=_nonnegative(annual_gift, "annual charitable gift"),
            marginal_rate=federal_rate,
        )
        if bunch.benefit > 0:
            opportunities.append(_opportunity(
                "charitable-bunching",
                f"Bunch {bunch.years} years of planned giving",
                amount=bunch.annual_gift * bunch.years,
                current_tax_savings=None,
                future_tax_savings=bunch.benefit,
                reason=(
                    f"Bunching creates {bunch.extra_deduction:,.0f} more "
                    f"deductions and an estimated {bunch.benefit:,.0f} "
                    f"federal benefit over the {bunch.years}-year window."
                ),
                tradeoffs=(
                    "Requires prefunding several years of irrevocable gifts.",
                    "A donor-advised fund adds fees and administration.",
                    "AGI limits can defer or expire part of a large deduction.",
                ),
                related_skill="charitable-giving-strategy",
            ))
    return opportunities


def _roth_conversion_opportunity(
    data: Mapping[str, Any],
    history: TaxHistory,
    current: TaxYear,
    current_cfg: Mapping[str, Any],
    federal_rate: float,
    state_rate: float,
) -> TaxOpportunity | None:
    age = _primary_age(data)
    retirement_age = data.get("retirement", {}).get("planned_retirement_age")
    if retirement_age is not None:
        retirement_age = _nonnegative(
            retirement_age, "planned retirement age")
    if age is None or retirement_age is None or age < retirement_age:
        return None
    if current.adjusted_gross_income >= history.median_agi:
        return None

    bracket_top = _optional_nonnegative(
        current_cfg.get("target_ordinary_bracket_top"),
        "target ordinary bracket top",
    )
    future_rate = _optional_rate(
        current_cfg.get("expected_future_combined_marginal_rate"),
        "expected future combined marginal rate",
    )
    if bracket_top is None or bracket_top <= current.taxable_income:
        return None

    state_taxable = current_cfg.get("roth_conversion_state_taxable") is True
    current_rate = _combined_rate(
        federal_rate,
        state_rate if state_taxable else 0.0,
        label="combined Roth-conversion rate",
    )
    amount = bracket_top - current.taxable_income
    later_savings = (
        amount * max(0.0, future_rate - current_rate)
        if future_rate is not None
        else None
    )
    return _opportunity(
        "roth-conversion-window",
        "Model a Roth conversion into the recorded bracket headroom",
        amount=amount,
        current_tax_savings=-(amount * current_rate),
        future_tax_savings=later_savings,
        confidence="scenario",
        reason=(
            f"Projected AGI is below the historical median and {amount:,.0f} "
            "of supplied target-bracket headroom remains."
        ),
        tradeoffs=(
            "Raises current tax; it is not a current-year tax reduction.",
            "Raises MAGI and can reduce ACA subsidies or trigger IRMAA later.",
            "The future-rate comparison is undiscounted and uncertain; pay "
            "conversion tax from outside funds.",
            "State tax is included only when explicitly recorded as taxable.",
        ),
        related_skill="roth-conversion-window",
    )


def _opportunity_order(item: TaxOpportunity) -> tuple[Any, ...]:
    current = item.current_tax_savings or 0.0
    future = item.future_tax_savings or 0.0
    if current > 0:
        group = 0
    elif future > 0:
        group = 1
    else:
        group = 2
    return (group, -max(0.0, current), -max(0.0, future), item.key)


def plan_from_facts(data: Mapping[str, Any]) -> TaxPlan:
    """Build a tax plan from filed-return history and current recorded facts."""
    section = data.get("tax_planning") or {}
    history = parse_history(section.get("returns") or [])
    current_cfg = section.get("current_year") or {}
    current = _parse_row(current_cfg, projected=True)
    if current.tax_year <= history.years[-1].tax_year:
        raise TaxPlanningError(
            "current projection tax year must follow the historical returns")

    assumptions = data.get("assumptions") or {}
    federal_rate = _rate(
        assumptions.get("marginal_tax_rate"), "federal marginal tax rate")
    state_rate = _rate(
        assumptions.get("state_tax_rate"), "state marginal tax rate")

    result = TaxPlan(history=history, current=current)
    if len(history.regimes) > 1:
        result.findings.append(
            "Filing status or state changed within the return history; rates "
            "remain visible but are not treated as a like-for-like trend."
        )
    latest = history.years[-1]
    if (
        current.filing_status != latest.filing_status
        or current.state != latest.state
    ):
        result.findings.append(
            "The current filing status or state differs from the latest filed "
            "return; the projected rate is not directly comparable."
        )
    if len(history.years) == 1:
        result.findings.append(
            "Only one filed return is recorded, so no historical trend is "
            "claimed."
        )
    else:
        gaps = [
            (left.tax_year, right.tax_year)
            for left, right in zip(history.years, history.years[1:])
            if right.tax_year != left.tax_year + 1
        ]
        if gaps:
            result.findings.append(
                "Tax history has year gaps; no missing return is carried "
                "forward or interpolated."
            )

    balances_due = [
        row for row in history.years
        if row.payment_gap is not None and row.payment_gap > 0
    ]
    if balances_due:
        result.findings.append(
            f"{len(balances_due)} historical year(s) ended with tax due. "
            "Withholding and estimates change payment timing and penalties, "
            "not the underlying tax."
        )
    if current.payment_gap is not None and current.payment_gap > 0:
        result.findings.append(
            f"The current projection is short ${current.payment_gap:,.0f} "
            "against recorded payments; reserve or adjust payments separately "
            "from tax-reduction decisions."
        )

    country = _text(
        data.get("meta", {}).get("jurisdiction", {}).get("country"),
        "current country",
    ).upper()
    if country != "US":
        result.findings.append(
            "The strategy screen is U.S.-specific, so no contribution, HSA, "
            "loss-harvest, charitable, or Roth action is generated for the "
            f"recorded country {country}."
        )
        return result

    result.opportunities.extend(_contribution_opportunities(
        data, current_cfg, federal_rate, state_rate, result.findings))
    loss = _loss_harvest_opportunity(data, current_cfg, result.findings)
    if loss is not None:
        result.opportunities.append(loss)
    result.opportunities.extend(_charitable_opportunities(data, federal_rate))
    conversion = _roth_conversion_opportunity(
        data,
        history,
        current,
        current_cfg,
        federal_rate,
        state_rate,
    )
    if conversion is not None:
        result.opportunities.append(conversion)
    result.opportunities.sort(key=_opportunity_order)
    return result
