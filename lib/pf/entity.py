"""Owner-operator entity choice, and the reasonable-salary optimum.

Scope is **one or two owner-operators with no third-party employees.** A sole
proprietor deciding whether to elect S-Corp status is making a personal
financial decision about their own money. Optimising payroll across staff is
business administration and is out of scope — the arithmetic here assumes the
only W-2 wages the business pays are the owners' own.

## The one idea

**W-2 salary reduces payroll tax exposure and reduces qualified business
income at the same time.** Those pull in opposite directions, so reasonable
salary has an *optimum*, not a floor:

- Below the QBI taxable-income threshold, every dollar moved from distribution
  to salary costs FICA *and* costs 20 cents of QBI deduction. The best salary
  is the **lowest defensible** one, and the binding constraint is what can be
  justified to the IRS — not arithmetic.
- Above the threshold, the QBI deduction is capped at 50% of W-2 wages (or
  25% + 2.5% UBIA). Now salary *buys* deduction, and there is a genuine
  interior optimum — classically near 28% of pre-salary profit, where
  `0.5 × W` meets `0.2 × (P − W − employer FICA)`.
- Above the threshold in a specified service trade or business, QBI phases out
  to nothing. The W-2 limit stops mattering and salary is a pure cost again.

A comparison that models SE-tax savings without the QBI offset recommends the
wrong salary, confidently, and in the same tone in all three regimes. That is
why QBI is computed here rather than in a skill of its own.

## Basis

Nominal, single-year, federal plus a flat state rate. Take-home is **cash in
the owners' hands after all federal and state tax**, before any retirement
contribution.

The federal income tax uses the supplied *marginal* rate applied to taxable
income rather than a bracket schedule. That makes each absolute take-home
figure an approximation and each **difference between structures** close to
right, which is what the decision turns on. Read the gaps, not the levels.

## What comes from the facts file, and what does not

Rates fixed in statute and not inflation-indexed are constants here — the SE
tax rates, the QBI percentages, the corporate rate. Every figure that is
**indexed annually** — the Social Security wage base, the QBI threshold and
phase-in range — is read from the facts file and is never guessed. Absent, the
module reports the structure and refuses the figure.

That line is deliberate: `REVIEW.md` A3 records `limits.py` as an unverified
tax-code mirror that must not grow, and an annual figure baked into a module is
exactly the thing that goes stale silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import limits as _limits

SCHEDULE_C = "schedule_c"
S_CORP = "s_corp"
C_CORP = "c_corp"

#: OASDI, employer + employee combined. Fixed in statute since 1990; only the
#: wage base it applies to is indexed, and that comes from the facts file.
SS_RATE = 0.124
#: Medicare HI, employer + employee combined. No wage cap.
MEDICARE_RATE = 0.029
#: Additional Medicare on wages/SE income above a threshold. Employee only, no
#: employer match, and the threshold is fixed in statute — never indexed.
ADDL_MEDICARE_RATE = 0.009
ADDL_MEDICARE_THRESHOLD = {
    "single": 200_000, "head_of_household": 200_000,
    "married_joint": 250_000, "married_separate": 125_000,
}

#: Net earnings from self-employment are 92.35% of net profit — the statutory
#: stand-in for the employer half a sole proprietor does not get to deduct
#: before computing the tax.
SE_BASE_FACTOR = 0.9235

#: §199A deduction rate.
QBI_RATE = 0.20
#: §199A(b)(2) wage limit, the two alternatives. The second exists for
#: capital-heavy businesses; an owner-operator service business rarely has the
#: UBIA to make it bind.
QBI_WAGE_ONLY = 0.50
QBI_WAGE_PLUS_WAGE = 0.25
QBI_WAGE_PLUS_UBIA = 0.025

#: Flat corporate rate, TCJA. Not indexed.
C_CORP_RATE = 0.21

#: Trades or businesses where the principal asset is the reputation or skill of
#: its employees or owners — §199A(d)(2). Above the threshold their QBI phases
#: out entirely, which reverses the salary advice.
SSTB_FIELDS = (
    "health", "law", "accounting", "actuarial_science", "performing_arts",
    "consulting", "athletics", "financial_services", "brokerage_services",
    "investing_and_investment_management", "trading", "dealing_in_securities",
)

ENTITY_SOURCE = (
    "IRC §1401 and §3101 (SECA/FICA rates); §1402(a)(12) (the 92.35% factor); "
    "§3101(b)(2) (Additional Medicare tax and its fixed thresholds); "
    "§199A (the 20% deduction, the wage and wage-plus-UBIA limits, and the "
    "SSTB definition at §199A(d)(2)); §11(b) (the 21% corporate rate); "
    "§404(a)(3) and §415(c) (the 25%/20% employer contribution rates)"
)
ENTITY_VERIFIED = "unverified — check against irs.gov Publications 15, 334 and 535"

#: Steps in the salary sweep. Fine enough to locate the interior optimum to
#: within a rounding error, coarse enough that the reported curve is readable.
SWEEP_STEPS = 200

#: An S-Corp election is worth making only if the tax saving clears the cost of
#: running it. Below this multiple of the added annual cost the saving is not
#: worth the standing obligation — a payroll filing that must happen every
#: quarter, forever, is not free even when the accountant's invoice is small.
ROI_MULTIPLE = 2.0


# ── inputs ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TaxParams:
    """Year-specific rates and thresholds. All from the facts file.

    `known` is deliberately strict. A comparison missing the wage base or the
    QBI threshold is not a slightly worse comparison — it is one that cannot
    tell which of the three regimes the household is in, which is the only
    thing the salary answer depends on.
    """

    marginal_rate: float | None = None
    state_rate: float | None = None
    ss_wage_base: float | None = None
    qbi_threshold: float | None = None
    qbi_phase_in: float | None = None
    qualified_dividend_rate: float | None = None
    niit_rate: float | None = None
    filing_status: str = "married_joint"
    #: The **owner's own** W-2 wages from other employment. They consume the
    #: Social Security wage base first, which can make the S-Corp payroll
    #: saving nearly vanish. The wage base is per person: a spouse's salary
    #: does not consume it, and treating it as household-wide understates the
    #: payroll tax of a business owned by the lower earner.
    other_wages: float = 0.0
    #: Household taxable income from outside the business, before deductions.
    #: Household-wide, unlike `other_wages`, because the §199A threshold test
    #: is on the return's taxable income.
    other_taxable_income: float = 0.0
    #: Standard or itemised deductions. Optional, but its absence overstates
    #: taxable income and can wrongly place the household above the QBI
    #: threshold, so the caller is told when it is missing.
    deductions_total: float | None = None

    @property
    def known(self) -> bool:
        return (self.marginal_rate is not None
                and self.ss_wage_base is not None
                and self.qbi_threshold is not None
                and self.qbi_phase_in is not None)

    @property
    def missing(self) -> list[str]:
        names = {
            "assumptions.marginal_tax_rate": self.marginal_rate,
            "assumptions.ss_wage_base": self.ss_wage_base,
            "assumptions.qbi_threshold": self.qbi_threshold,
            "assumptions.qbi_phase_in_range": self.qbi_phase_in,
        }
        return [k for k, v in names.items() if v is None]

    @property
    def addl_medicare_threshold(self) -> float:
        return ADDL_MEDICARE_THRESHOLD.get(
            self.filing_status, ADDL_MEDICARE_THRESHOLD["married_joint"])


@dataclass(frozen=True)
class Business:
    """The business, as the owners see it."""

    gross_revenue: float
    #: Ordinary and necessary expenses, excluding any owner salary and the
    #: employer payroll tax on it — those are modelled per structure.
    expenses: float
    sstb: bool = False
    field: str | None = None
    #: Unadjusted basis immediately after acquisition of qualified property.
    #: Only matters above the QBI threshold; `None` there is reported rather
    #: than treated as zero.
    ubia: float | None = None
    #: The lowest salary the owners can defend as reasonable compensation.
    #: Supplied, never derived — see `reasonable_salary_floor` below.
    reasonable_salary_floor: float | None = None
    #: Annual cost of running an S-Corp that a Schedule C does not incur:
    #: payroll processing, the 1120-S, state franchise or minimum tax,
    #: registered agent.
    s_corp_annual_cost: float | None = None

    @property
    def net_profit(self) -> float:
        return self.gross_revenue - self.expenses


# ── payroll taxes ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PayrollTax:
    social_security: float
    medicare: float
    additional_medicare: float
    #: The half a business deducts. Zero for a sole proprietor, where the
    #: equivalent is an above-the-line income-tax deduction instead.
    employer_share: float = 0.0

    @property
    def total(self) -> float:
        return self.social_security + self.medicare + self.additional_medicare


def se_tax(net_profit: float, p: TaxParams) -> PayrollTax:
    """Self-employment tax on Schedule C net profit.

    The FEIE does not touch this. A US citizen running a Schedule C abroad
    excludes the income from *income* tax and still pays the full 15.3%.
    """
    if net_profit <= 0 or p.ss_wage_base is None:
        return PayrollTax(0.0, 0.0, 0.0)
    base = net_profit * SE_BASE_FACTOR
    ss_room = max(0.0, p.ss_wage_base - p.other_wages)
    ss = min(base, ss_room) * SS_RATE
    med = base * MEDICARE_RATE
    over = max(0.0, base + p.other_wages - p.addl_medicare_threshold)
    addl = min(over, base) * ADDL_MEDICARE_RATE
    return PayrollTax(ss, med, addl)


def fica_on_wages(wages: float, p: TaxParams) -> PayrollTax:
    """FICA on W-2 wages, both halves.

    The employer half is a deductible business expense, so it reduces the
    distribution — and therefore QBI — rather than being free.
    """
    if wages <= 0 or p.ss_wage_base is None:
        return PayrollTax(0.0, 0.0, 0.0)
    ss_room = max(0.0, p.ss_wage_base - p.other_wages)
    ss = min(wages, ss_room) * SS_RATE
    med = wages * MEDICARE_RATE
    over = max(0.0, wages + p.other_wages - p.addl_medicare_threshold)
    addl = min(over, wages) * ADDL_MEDICARE_RATE
    employer = (ss + med) / 2.0
    return PayrollTax(ss, med, addl, employer_share=employer)


# ── §199A ───────────────────────────────────────────────────────────────────


@dataclass
class QBI:
    deduction: float
    tentative: float
    wage_limit: float | None
    #: "below_threshold" | "phase_in" | "wage_limited" | "sstb_phased_out"
    regime: str
    applicable_pct: float = 1.0
    findings: list[str] = field(default_factory=list)

    @property
    def limited(self) -> bool:
        return self.deduction < self.tentative - 0.5


def qbi_deduction(
    *,
    qbi: float,
    w2_wages: float,
    ubia: float | None,
    taxable_income_before_qbi: float,
    sstb: bool,
    p: TaxParams,
) -> QBI:
    """§199A, including the SSTB phase-out and the W-2 wage limit.

    The three regimes are the whole point. Which one applies is decided by
    *taxable income*, not by business profit — so a spouse's salary can push a
    business over the threshold and change the salary answer.
    """
    if not p.known:
        return QBI(0.0, 0.0, None, "unknown")
    if qbi <= 0:
        return QBI(0.0, 0.0, None, "no_qbi")

    excess = taxable_income_before_qbi - (p.qbi_threshold or 0.0)
    span = p.qbi_phase_in or 0.0
    ratio = 0.0 if excess <= 0 else (1.0 if span <= 0 else min(1.0, excess / span))

    applicable = 1.0
    if sstb:
        applicable = 1.0 - ratio
        if applicable <= 0:
            return QBI(0.0, QBI_RATE * qbi, None, "sstb_phased_out", 0.0, findings=[
                "**QBI is fully phased out.** This is a specified service trade "
                "or business and taxable income is above the top of the phase-in "
                "range, so §199A is worth nothing here. That removes the reason "
                "to pay salary for the wage limit — salary is now a pure payroll "
                "cost again, and the lowest defensible figure wins."])
        qbi *= applicable
        w2_wages *= applicable
        if ubia is not None:
            ubia *= applicable

    tentative = QBI_RATE * qbi
    ubia_part = QBI_WAGE_PLUS_UBIA * (ubia or 0.0)
    limit = max(QBI_WAGE_ONLY * w2_wages, QBI_WAGE_PLUS_WAGE * w2_wages + ubia_part)

    if ratio <= 0:
        out = QBI(tentative, tentative, limit, "below_threshold", applicable)
        out.findings.append(
            "Taxable income is below the §199A threshold, so the W-2 wage "
            "limit does not apply at all. Salary buys no deduction here — it "
            "only costs FICA and shrinks QBI.")
        return out

    if ratio >= 1.0:
        deduction = min(tentative, limit)
        regime = "wage_limited" if deduction < tentative - 0.5 else "above_threshold"
    else:
        reduction = max(0.0, tentative - limit) * ratio
        deduction = tentative - reduction
        regime = "phase_in"

    cap = QBI_RATE * max(0.0, taxable_income_before_qbi)
    if deduction > cap:
        deduction = cap
        regime = "taxable_income_capped"

    out = QBI(deduction, tentative, limit, regime, applicable)
    if regime == "wage_limited":
        out.findings.append(
            f"**The W-2 wage limit is binding.** The deduction is capped at "
            f"{_money(limit)} (50% of W-2 wages, or 25% plus 2.5% of qualified "
            f"property) against {_money(tentative)} of tentative deduction. In "
            "this regime raising salary *increases* the deduction, which is the "
            "one case where paying yourself more is tax-efficient.")
    if ubia is None and ratio > 0:
        out.findings.append(
            "`business.ubia` is not recorded and the wage limit is in play. It "
            "is treated as zero here, which **understates** the limit for a "
            "business that owns depreciable property. Record it, or read the "
            "limit above as a floor.")
    if sstb and 0 < ratio < 1:
        out.findings.append(
            f"Specified service business inside the phase-in range: only "
            f"{applicable:.0%} of QBI, wages and property count. Every extra "
            "dollar of taxable income shrinks the deduction from both ends.")
    return out


# ── structures ──────────────────────────────────────────────────────────────


@dataclass
class Outcome:
    structure: str
    net_profit: float
    salary: float
    #: Payroll tax the owners actually bear. For an S-Corp that is both halves,
    #: because the employer is them.
    payroll_tax: float
    qbi: QBI
    taxable_income: float
    federal_income_tax: float
    state_tax: float
    entity_tax: float
    admin_cost: float
    take_home: float
    lines: list[tuple[str, float]] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    #: Set when a figure could not be computed at all.
    unavailable: str | None = None

    @property
    def total_tax(self) -> float:
        return (self.payroll_tax + self.federal_income_tax + self.state_tax
                + self.entity_tax)


def _state_tax(base: float, p: TaxParams) -> float:
    return max(0.0, base) * (p.state_rate or 0.0)


def schedule_c(b: Business, p: TaxParams) -> Outcome:
    """Sole proprietor or single-member LLC. No salary; no W-2 wages."""
    profit = b.net_profit
    pt = se_tax(profit, p)
    half_se = (pt.social_security + pt.medicare) / 2.0

    qbi_income = profit - half_se
    ti_before = max(0.0, profit - half_se + p.other_taxable_income
                    - (p.deductions_total or 0.0))
    q = qbi_deduction(qbi=qbi_income, w2_wages=0.0, ubia=b.ubia,
                      taxable_income_before_qbi=ti_before, sstb=b.sstb, p=p)

    # Only the business share of income tax is attributed here. Tax on income
    # from outside the business is identical under every structure and cancels
    # in the comparison; carrying it would only add noise to the gaps.
    taxable = max(0.0, profit - half_se - q.deduction)
    fed = taxable * (p.marginal_rate or 0.0)
    state = _state_tax(profit, p)
    take = profit - pt.total - fed - state

    o = Outcome(SCHEDULE_C, profit, 0.0, pt.total, q, taxable, fed,
                state, 0.0, 0.0, take)
    o.lines = [
        ("Net profit", profit),
        ("Self-employment tax (15.3% to the wage base)", -pt.total),
        ("Federal income tax", -fed),
        ("State income tax", -state),
        ("Take-home", take),
    ]
    o.findings.extend(q.findings)
    if q.regime in ("wage_limited", "phase_in") and not b.sstb:
        o.findings.append(
            "**A Schedule C pays no W-2 wages, so above the threshold it has "
            "no wage limit to stand on.** For a non-service business over the "
            "threshold this is frequently the whole argument for electing "
            "S-Corp status — not the payroll saving, the §199A deduction that "
            "a sole proprietorship structurally cannot claim.")
    o.findings.append(
        "Half the SE tax is deducted above the line, and that deduction also "
        "**reduces QBI** — as does a deductible self-employed health insurance "
        "premium and any employer retirement contribution. Neither of the last "
        "two is modelled here; both make the §199A figure above slightly "
        "optimistic. See `solo-retirement-plan-choice`.")
    return o


def s_corp(b: Business, p: TaxParams, salary: float) -> Outcome:
    """S-Corp election, with a given owner salary.

    The distribution is what is left after salary *and the employer half of
    FICA*, which is why moving a dollar into salary costs more than a dollar of
    distribution.
    """
    profit = b.net_profit
    salary = max(0.0, min(salary, profit))
    fica = fica_on_wages(salary, p)
    # Salary plus the employer FICA on it cannot exceed profit. Trim by fixed
    # point rather than reporting a negative distribution as if it were a plan.
    for _ in range(6):
        if profit - salary - fica.employer_share >= 0:
            break
        salary = max(0.0, profit - fica.employer_share)
        fica = fica_on_wages(salary, p)
    distribution = max(0.0, profit - salary - fica.employer_share)
    employee_fica = fica.total - fica.employer_share

    ti_before = max(0.0, salary + distribution + p.other_taxable_income
                    - (p.deductions_total or 0.0))
    q = qbi_deduction(qbi=distribution, w2_wages=salary, ubia=b.ubia,
                      taxable_income_before_qbi=ti_before, sstb=b.sstb, p=p)

    taxable_business = max(0.0, salary + distribution - q.deduction)
    fed = taxable_business * (p.marginal_rate or 0.0)
    state = _state_tax(salary + distribution, p)
    owner_payroll = fica.total  # both halves; the employer is the owner
    admin = b.s_corp_annual_cost or 0.0
    # The employer half is already out of `distribution`; only the employee
    # half is subtracted again, or it would be counted twice.
    take = salary + distribution - employee_fica - fed - state - admin

    o = Outcome(S_CORP, profit, salary, owner_payroll, q, taxable_business,
                fed, state, 0.0, admin, take)
    o.lines = [
        ("Net profit before salary", profit),
        ("W-2 salary", -salary),
        ("Employer FICA (7.65%)", -fica.employer_share),
        ("Distribution", distribution),
        ("Employee FICA", -employee_fica),
        ("Federal income tax", -fed),
        ("State income tax", -state),
        ("Cost of running the S-Corp", -admin),
        ("Take-home", take),
    ]
    o.findings.extend(q.findings)
    if b.s_corp_annual_cost is None:
        o.findings.append(
            "`business.s_corp_annual_cost` is not recorded, so the figure above "
            "is **before** the cost of running the election — payroll "
            "processing, the 1120-S, state franchise or minimum tax, registered "
            "agent. Supply it and the report states whether the election clears "
            "its own cost.")
    return o


def c_corp(b: Business, p: TaxParams, salary: float,
           distribute: bool = True) -> Outcome:
    """C-Corp, paying a salary and distributing the rest as a dividend.

    Two layers of tax and no §199A. Modelled because it is asked about, not
    because it usually wins for an owner-operator taking the cash out.
    """
    profit = b.net_profit
    salary = max(0.0, min(salary, profit))
    fica = fica_on_wages(salary, p)
    corp_income = max(0.0, profit - salary - fica.employer_share)
    corp_tax = corp_income * C_CORP_RATE
    after_corp = corp_income - corp_tax

    if p.qualified_dividend_rate is None and distribute:
        o = Outcome(C_CORP, profit, salary, fica.total, QBI(0, 0, None, "n/a"),
                    0.0, 0.0, 0.0, corp_tax, 0.0, 0.0)
        o.unavailable = (
            "`assumptions.qualified_dividend_rate` is not recorded, so the "
            "second layer of tax cannot be valued and no take-home figure is "
            "produced. The rate is bracketed by taxable income and indexed "
            "annually; supply the one that applies to this household.")
        return o

    div_rate = (p.qualified_dividend_rate or 0.0) + (p.niit_rate or 0.0)
    dividend = after_corp if distribute else 0.0
    dividend_tax = dividend * div_rate
    fed_on_salary = salary * (p.marginal_rate or 0.0)
    state = _state_tax(salary + dividend, p)
    take = (salary - (fica.total - fica.employer_share) - fed_on_salary
            + dividend - dividend_tax - state)

    o = Outcome(C_CORP, profit, salary, fica.total, QBI(0, 0, None, "n/a"),
                salary + dividend, fed_on_salary + dividend_tax, state,
                corp_tax, 0.0, take)
    o.lines = [
        ("Net profit before salary", profit),
        ("W-2 salary", -salary),
        ("Employer FICA (7.65%)", -fica.employer_share),
        ("Corporate income tax (21%)", -corp_tax),
        ("Dividend", dividend),
        ("Tax on the dividend", -dividend_tax),
        ("Employee FICA", -(fica.total - fica.employer_share)),
        ("Federal income tax on salary", -fed_on_salary),
        ("State income tax", -state),
        ("Take-home", take),
    ]
    o.findings.append(
        "**No §199A deduction exists for a C-Corp**, and the profit is taxed "
        "twice when it comes out. Retaining earnings defers the second layer "
        "rather than removing it, and retention has its own limits — the "
        "accumulated earnings tax and the personal holding company rules.")
    o.findings.append(
        "**The C-Corp figure is optimistic and should be read as a ceiling.** "
        "State *corporate* income tax and franchise tax are not modelled — the "
        "state rate here is applied only to what reaches the owners — and most "
        "states tax corporate income as well. Where the comparison is close, "
        "that omission alone can decide it.")
    o.findings.append(
        "The case for a C-Corp is usually **not** this arithmetic. It is §1202 "
        "qualified small business stock on an eventual sale, an outside "
        "investor who will not hold S-Corp shares, or a genuine need to retain "
        "capital in the business. None of those are modelled here, and the "
        "first depends entirely on an exit this skill knows nothing about.")
    return o


# ── the salary optimum ──────────────────────────────────────────────────────


@dataclass
class SalaryPoint:
    salary: float
    take_home: float
    qbi_deduction: float
    payroll_tax: float


@dataclass
class SalaryCurve:
    points: list[SalaryPoint]
    best: SalaryPoint | None
    floor: float | None
    #: "minimise" when take-home falls monotonically with salary,
    #: "interior" when the wage limit creates a genuine optimum.
    shape: str = "unknown"
    findings: list[str] = field(default_factory=list)

    @property
    def at_floor(self) -> bool:
        return (self.best is not None and self.floor is not None
                and abs(self.best.salary - self.floor) < 1.0)


def salary_curve(b: Business, p: TaxParams, *, steps: int = SWEEP_STEPS) -> SalaryCurve:
    """Sweep owner salary and find the take-home maximum.

    The sweep starts at the reasonable-salary floor when one is supplied, and
    at zero when one is not — a zero-salary S-Corp is not a recommendation, it
    is the left-hand end of a curve, and the report says so.
    """
    profit = b.net_profit
    if profit <= 0 or not p.known:
        return SalaryCurve([], None, b.reasonable_salary_floor)

    lo = b.reasonable_salary_floor or 0.0
    lo = min(lo, profit)
    hi = profit
    step = max(1.0, (hi - lo) / steps)

    points: list[SalaryPoint] = []
    s = lo
    while s <= hi + 0.5:
        o = s_corp(b, p, s)
        points.append(SalaryPoint(s, o.take_home, o.qbi.deduction, o.payroll_tax))
        s += step
    best = max(points, key=lambda pt: pt.take_home)

    curve = SalaryCurve(points, best, b.reasonable_salary_floor)
    first, last = points[0], points[-1]
    if best.salary <= first.salary + step:
        curve.shape = "minimise"
    elif best.salary >= last.salary - step:
        curve.shape = "maximise"
    else:
        curve.shape = "interior"

    if curve.shape == "minimise":
        curve.findings.append(
            "**Take-home falls monotonically as salary rises.** Every dollar "
            "moved from distribution to salary costs payroll tax and shrinks "
            "QBI, and nothing pushes the other way. The optimum is therefore "
            "the *lowest defensible* salary, and 'defensible' is the binding "
            "constraint — not arithmetic.")
    elif curve.shape == "interior":
        curve.findings.append(
            f"**There is a genuine interior optimum at about "
            f"{_money(best.salary)}** — {best.salary / profit:.0%} of "
            "pre-salary profit. Below it the §199A wage limit is throwing away "
            "deduction; above it payroll tax costs more than the deduction is "
            "worth. This is the case a 'pay yourself as little as possible' "
            "rule of thumb gets wrong.")
        spread = best.take_home - first.take_home
        curve.findings.append(
            f"Moving from the floor to the optimum is worth {_money(spread)} a "
            "year on these figures. The curve is flat near the top, so being "
            "approximately right is worth nearly as much as being exactly "
            "right — do not over-fit the salary to the dollar.")
    elif curve.shape == "maximise":
        curve.findings.append(
            "**Take-home rises all the way to a full-salary S-Corp**, which "
            "means the election is buying nothing here: there is no "
            "distribution left to shelter from payroll tax. Check the Schedule "
            "C comparison before electing.")

    if b.reasonable_salary_floor is None:
        curve.findings.append(
            "**No reasonable-salary floor is recorded**, so the sweep runs from "
            "zero. A zero or token salary is the single most reliable way to "
            "attract an S-Corp audit, and the IRS can recharacterise "
            "distributions as wages with penalties and interest. This skill "
            "will not invent the figure — it depends on what the work is, what "
            "comparable people are paid for it, and how much of the profit is "
            "your labour rather than your capital. Get it from comparable "
            "compensation data and record it in `business.reasonable_salary_floor`.")
    return curve


# ── the comparison ──────────────────────────────────────────────────────────


@dataclass
class Comparison:
    outcomes: list[Outcome]
    curve: SalaryCurve
    params_known: bool
    missing: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    def by_structure(self, name: str) -> Outcome | None:
        for o in self.outcomes:
            if o.structure == name:
                return o
        return None

    @property
    def best(self) -> Outcome | None:
        usable = [o for o in self.outcomes if o.unavailable is None]
        return max(usable, key=lambda o: o.take_home) if usable else None


def compare(b: Business, p: TaxParams, *, salary: float | None = None) -> Comparison:
    """Schedule C against S-Corp at its best salary, against C-Corp."""
    if not p.known:
        return Comparison([], SalaryCurve([], None, b.reasonable_salary_floor),
                          False, p.missing, findings=[
            "**Cannot compare structures.** The indexed figures below are "
            "missing from the facts file, and without them there is no way to "
            "tell which §199A regime this household is in — which is the only "
            "thing the salary answer depends on. They are asked for rather "
            "than held in the repository because an annual figure baked into a "
            "skill goes stale silently."])

    curve = salary_curve(b, p)
    chosen = salary if salary is not None else (curve.best.salary if curve.best else 0.0)

    sc = schedule_c(b, p)
    s = s_corp(b, p, chosen)
    c = c_corp(b, p, chosen)
    cmp_ = Comparison([sc, s, c], curve, True)

    gap = s.take_home - sc.take_home
    cost = b.s_corp_annual_cost
    if cost is None:
        cmp_.findings.append(
            f"S-Corp is {_money(abs(gap))}/yr {'ahead of' if gap > 0 else 'behind'} "
            "Schedule C **before the cost of running it**. Record "
            "`business.s_corp_annual_cost` — payroll processing, the 1120-S, "
            "state franchise or minimum tax, registered agent — and this "
            "becomes a verdict rather than a number.")
    else:
        # `s.take_home` already has the cost subtracted, so `gap` is net.
        if gap <= 0:
            cmp_.findings.append(
                f"**The S-Corp election loses {_money(-gap)}/yr net of its "
                f"{_money(cost)} running cost.** Stay on Schedule C. The "
                "election is not a one-way door, but it is a standing "
                "obligation: quarterly payroll filings that must happen "
                "whether or not the business had a good year.")
        elif gap < cost * (ROI_MULTIPLE - 1):
            cmp_.findings.append(
                f"**Marginal.** The election nets {_money(gap)}/yr after a "
                f"{_money(cost)} running cost — under {ROI_MULTIPLE:.0f}× the "
                "cost, which is the point at which a recurring administrative "
                "obligation stops being worth the saving. A single missed "
                "payroll filing penalty eats a year of this.")
        else:
            cmp_.findings.append(
                f"**The S-Corp election nets {_money(gap)}/yr** after its "
                f"{_money(cost)} running cost, at a salary of "
                f"{_money(chosen)}. That clears the cost comfortably.")

    if p.other_wages > 0:
        cmp_.findings.append(
            f"{_money(p.other_wages)} of outside W-2 wages already consume the "
            "Social Security wage base. Most of the S-Corp payroll saving is "
            "the 12.4% OASDI piece, so once the base is used up the election "
            "saves only the 2.9% Medicare rate on the sheltered distribution — "
            "frequently less than it costs to run.")

    if p.deductions_total is None:
        cmp_.findings.append(
            "`assumptions.deductions_total` is not recorded, so taxable income "
            "is computed **before** the standard or itemised deduction. That "
            "overstates it, and an overstated taxable income can place the "
            "household above the §199A threshold when it is actually below — "
            "which flips the salary advice from 'minimise' to 'optimise'. If "
            "the household is anywhere near the threshold, supply it.")
    return cmp_


# ── cross-border ────────────────────────────────────────────────────────────


def cross_border_flags(*, tax_home_abroad: bool) -> list[str]:
    """What entity choice does and does not do for an owner-operator abroad.

    Flags only. The residency and exclusion arithmetic belongs to the
    cross-border cluster; two skills each modelling an S-Corp election would be
    the duplication this repository keeps catching.
    """
    if not tax_home_abroad:
        return []
    return [
        "**The foreign earned income exclusion does not exclude "
        "self-employment tax.** It is an *income tax* exclusion. A US citizen "
        "running a Schedule C from abroad can exclude the profit from income "
        "tax and still owes the full 15.3% on it — which can make the whole "
        "structure comparison above swing on a tax the exclusion never "
        "touched. See `feie-vs-ftc`.",
        "The exception is a **totalization agreement**: where one exists and "
        "the owner is covered by the foreign social security system, US SE tax "
        "can be eliminated with a certificate of coverage. Whether one applies "
        "is a country question — see the cross-border country table — and it "
        "is not assumed here.",
        "Excluded income is **not** qualified business income, so §199A and "
        "the FEIE interact badly: excluding the profit also removes the "
        "deduction the salary optimum above is built on. Do not read the "
        "salary curve as valid without checking which income is excluded.",
        "Incorporating abroad, or running a US entity from abroad, raises "
        "permanent-establishment, controlled-foreign-corporation and local "
        "registration questions this skill does not model. It owns entity "
        "choice; it does not own residency.",
    ]


# ── owner-only retirement plans ─────────────────────────────────────────────
#
# These live here rather than in a module of their own because the contribution
# base is an entity question: a Schedule C computes it from net earnings from
# self-employment, an S-Corp from W-2 salary, and the two give different
# answers from the same profit. §415(c) and the catch-up rules come from
# `limits.py` — this does not recompute space that is already tabulated.


#: Employer contribution rate as a share of W-2 compensation. For a
#: self-employed person the same 25% applied to net earnings *after* the
#: contribution works out at 20% of pre-contribution earnings.
EMPLOYER_RATE_W2 = 0.25
EMPLOYER_RATE_SELF_EMPLOYED = 0.20


@dataclass
class PlanOption:
    name: str
    employee_deferral: float
    catch_up: float
    employer: float
    total: float | None
    capped_by: str | None = None
    findings: list[str] = field(default_factory=list)


@dataclass
class PlanChoice:
    options: list[PlanOption]
    limits_known: bool
    year: int
    findings: list[str] = field(default_factory=list)

    @property
    def best(self) -> PlanOption | None:
        usable = [o for o in self.options if o.total is not None]
        return max(usable, key=lambda o: o.total or 0) if usable else None


def employer_contribution_base(
    *, net_profit: float | None, w2_salary: float | None, p: TaxParams
) -> tuple[float, str]:
    """The compensation the employer piece is a percentage of.

    Schedule C: net earnings from self-employment, i.e. net profit less half
    the SE tax, times 20%. S-Corp: W-2 salary only — **distributions are not
    compensation and buy no plan space.** That is the interaction people miss
    when they minimise salary for payroll-tax reasons and then discover the
    plan they wanted no longer fits.
    """
    if w2_salary is not None:
        return w2_salary * EMPLOYER_RATE_W2, "W-2 salary"
    if net_profit is None:
        return 0.0, "unknown"
    pt = se_tax(net_profit, p)
    net_se = net_profit - (pt.social_security + pt.medicare) / 2.0
    return max(0.0, net_se) * EMPLOYER_RATE_SELF_EMPLOYED, "net self-employment earnings"


def solo_plan_options(
    *,
    net_profit: float | None,
    w2_salary: float | None,
    age: int | None,
    year: int | None,
    p: TaxParams,
) -> PlanChoice:
    """Solo 401(k) against SEP IRA, for an owner-only business.

    The finding is usually decisive and structural rather than marginal: a
    Solo 401(k) allows an **elective deferral on top of** the employer piece; a
    SEP allows only the employer piece. At any income where the employer piece
    alone does not already reach §415(c), the Solo 401(k) shelters more — by
    roughly the deferral limit.
    """
    lim = _limits.for_year(year)
    choice = PlanChoice([], lim.known, year or 0)
    if not lim.known:
        choice.findings.append(
            f"No statutory limits are tabulated for {year}, so no contribution "
            "figure is produced. `limits.py` returns UNKNOWN for a year it has "
            "not been given rather than quietly applying last year's numbers. "
            "See `reference-data-refresh`.")
        return choice

    employer, base_label = employer_contribution_base(
        net_profit=net_profit, w2_salary=w2_salary, p=p)
    catch = _limits.catch_up_for_age(age, lim)
    deferral_limit = lim.elective_deferral or 0

    sep_total = min(employer, lim.total_additions or 0)
    sep = PlanOption("SEP IRA", 0.0, 0.0, sep_total, sep_total,
                     capped_by="§415(c)" if sep_total < employer else None)
    sep.findings.append(
        "A SEP has **no elective deferral and no catch-up.** Everything must "
        "come from the employer percentage, so below the income where that "
        "percentage alone reaches §415(c), a SEP simply shelters less.")
    sep.findings.append(
        "A SEP also requires **proportional contributions for every eligible "
        "employee** at the same percentage of pay. That is costless while the "
        "business is owner-only and expensive the year it is not — which is "
        "the failure mode: the plan was chosen for its simplicity and becomes "
        "the reason a first hire is unaffordable.")

    compensation = w2_salary if w2_salary is not None else max(0.0, net_profit or 0.0)
    deferral = min(float(deferral_limit), max(0.0, compensation))
    # §415(c) caps deferral plus employer; the catch-up sits outside it, which
    # is why the ceiling exceeds the headline number. Both facts come from
    # `limits.py` — nothing here recomputes them.
    additions = min(deferral + employer, float(lim.total_additions or 0))
    solo_total = additions + float(catch)
    solo = PlanOption("Solo 401(k)", deferral, float(catch), employer,
                      solo_total,
                      capped_by="§415(c)"
                      if deferral + employer > (lim.total_additions or 0) else None)
    solo.findings.append(
        f"Elective deferral of up to {_money(deferral_limit)} **on top of** the "
        f"{EMPLOYER_RATE_W2:.0%}/{EMPLOYER_RATE_SELF_EMPLOYED:.0%} employer "
        "piece, plus catch-up which sits outside §415(c). Both come from the "
        "same person; the plan just counts them separately.")
    if catch:
        solo.findings.append(
            f"{_money(catch)} of catch-up at this age, and it sits **outside** "
            "§415(c) — which is why the ceiling exceeds the headline number. "
            "See `contribution-space-audit`; this skill does not recompute it.")

    db = PlanOption("Defined benefit", 0.0, 0.0, 0.0, None,
                    capped_by="actuarial")
    db.findings.append(
        "**No figure, deliberately.** A defined benefit plan is limited by "
        "§415(b) — a *benefit* limit — and the deductible contribution is "
        "whatever an enrolled actuary certifies is needed to fund it, given "
        "age, compensation history and assumed returns. It is routinely "
        "$100k–$300k+ for an older high-income owner, which is the reason to "
        "look at it, and it cannot be estimated responsibly without the "
        "actuary.")
    db.findings.append(
        "It is also a **funding commitment**, not an annual election: the "
        "contribution is largely mandatory in bad years too, and terminating "
        "early has consequences. Right for cash-rich, stable, high-income "
        "owner-operators over roughly 45; wrong for volatile income.")

    choice.options = [solo, sep, db]
    gap = (solo.total or 0) - (sep.total or 0)
    if gap > 0:
        choice.findings.append(
            f"**The Solo 401(k) shelters {_money(gap)} more than the SEP** on "
            f"the same {base_label}. The gap is the elective deferral, which a "
            "SEP has no equivalent of.")
    elif (solo.total or 0) == (sep.total or 0) and solo.total:
        choice.findings.append(
            "Both plans reach the §415(c) ceiling on this income, so the "
            "sheltering is identical and the choice turns on the other "
            "differences: the SEP's obligation to employees, the Solo 401(k)'s "
            "Roth option and loan provision, and Form 5500-EZ once plan assets "
            "pass $250,000.")

    if w2_salary is not None:
        choice.findings.append(
            f"The employer piece is {EMPLOYER_RATE_W2:.0%} of **W-2 salary "
            f"only** — {_money(w2_salary)} here. S-Corp distributions are not "
            "compensation and buy no plan space, so a salary minimised for "
            "payroll-tax reasons also caps the retirement plan. That is a real "
            "cost of the S-Corp salary decision and belongs in "
            "`entity-structure-comparison` alongside it.")
    else:
        choice.findings.append(
            "For a Schedule C the employer contribution is itself deductible "
            "against QBI, so the after-tax value of a dollar contributed is "
            "less than the marginal rate suggests — the §199A deduction "
            "shrinks by 20 cents of that dollar too.")
    return choice


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
