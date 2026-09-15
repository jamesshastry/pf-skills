"""Investment property: the §469 gate first, then the deal arithmetic.

`housing.py` is about the home someone lives in. This module is about property
bought to produce income, and it exists to encode one ordering:

## The gate runs before the model

A rental loss is **passive** under §469. Passive losses offset passive income,
not W-2 income. Three doors open onto the wage income, and for a full-time
employee most of them are shut:

1. the **$25,000 allowance** for an active participant, which phases out over a
   MAGI band and is gone entirely above it — so it is unavailable to exactly
   the households that go looking for it;
2. **REPS**, which needs 750+ hours in real property trades *and* more than
   half of all working time. The second test, not the first, is what a
   full-time W-2 job makes close to unattainable, and it is heavily audited;
3. the **short-stay exception** — an average customer stay of seven days or
   less makes the activity *not a rental activity* under the regulations. It is
   then an ordinary trade or business, and **material participation alone**
   unlocks the loss against wage income without any of the REPS tests.

A disallowed loss is **suspended, not lost**: it carries forward and is
released on a fully taxable disposition of the activity. That matters for the
cost-segregation screen, where accelerating a deduction the household cannot
currently use converts a tax saving into a deferred one.

Running `underwrite()` or `screen_cost_segregation()` and quoting an after-tax
return without passing `assess_gate()` first produces a number that is simply
wrong for most W-2 investors. The skills are ordered accordingly.

## Which figures live here, and which do not

Two different kinds of number, treated differently on purpose.

**Structural tests** — 750 hours, more than 50% of working time, 7 days, the
100-hour material participation test — are module constants. They define the
*shape* of each door, they have not moved since 1986, and putting them in a
facts file would invite a household to edit the statute.

**Rates and dollar figures** — the allowance, the phase-out band, the marginal
rate, the long-term capital gain rate, the unrecaptured §1250 rate, NIIT, state
tax, the bonus depreciation percentage — come from the facts file and are
**refused when absent**. These drift with the year and with legislation, and
`REVIEW.md` A3 already records one unverified tax-code mirror in this
repository. This module does not add a second.

## Basis

Everything here is **nominal and pre-tax at the property level**. Cap rate,
cash-on-cash, DSCR and IRR are all computed on cash flows before the investor's
own income tax, which is the convention lenders and brokers use. The tax layer
sits in the gate, the exchange model and the cost-segregation screen, and is
never silently folded into a return figure.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

from pf.housing import amortise, monthly_payment

# ── §469: the structural tests ──────────────────────────────────────────────

#: Reg. §1.469-1T(e)(3)(ii)(A). An average customer stay at or below this makes
#: the activity **not a rental activity** — so the per se passive rule in
#: §469(c)(2) never attaches and material participation is enough. This is the
#: only door a full-time employee can realistically walk through.
SHORT_STAY_DAYS = 7.0

#: §469(c)(7)(B)(ii). Hours in real property trades or businesses required for
#: Real Estate Professional Status.
REPS_MIN_HOURS = 750.0

#: §469(c)(7)(B)(i). More than half of *all* personal services performed in any
#: trade or business must be in real property trades. A 2,000-hour W-2 job makes
#: this the binding test, not the 750 hours, and it is what audits attack.
REPS_MAJORITY_SHARE = 0.50

#: Reg. §1.469-5T(a)(3). One of the seven material participation tests: more
#: than 100 hours **and** more than any other individual, including any paid
#: manager or cleaner. The cleaner is usually what defeats it on a short-stay
#: property.
MATERIAL_PARTICIPATION_HOURS = 100.0

#: Reg. §1.469-5T(a)(1). The unconditional safe harbour — 500 hours needs no
#: comparison against anyone else.
MATERIAL_PARTICIPATION_SAFE_HARBOUR_HOURS = 500.0

#: §469(i)(3)(A). The allowance falls by this share of each dollar of MAGI
#: above the phase-out floor, which is why a $50,000 band fully consumes a
#: $25,000 allowance.
ALLOWANCE_PHASEOUT_RATE = 0.50

PASSIVE_LOSS_SOURCE = (
    "IRC §469(c)(2) and Reg. §1.469-1T(e)(3)(ii)(A) (the seven-day average "
    "stay that takes an activity out of 'rental activity'); §469(c)(7)(B)(i) "
    "and (ii) (the more-than-half and 750-hour Real Estate Professional "
    "tests); Reg. §1.469-5T(a)(1) and (a)(3) (the 500-hour safe harbour and "
    "the 100-hour-and-most tests); §469(i)(3)(A) (the 50% phase-out rate on "
    "the special allowance). The allowance amount and its MAGI floor are "
    "**not** here — they are read from the facts file"
)
PASSIVE_LOSS_VERIFIED = (
    "unverified — check against irs.gov Publication 925 and the text of §469")

EXCHANGE_SOURCE = (
    "IRC §1031(a)(3)(A) and (B) — 45 calendar days to identify replacement "
    "property in writing, and 180 calendar days to close, or the due date of "
    "the return for the year of the transfer if that comes first"
)
EXCHANGE_VERIFIED = (
    "unverified — check against irs.gov Form 8824 instructions")

RECOVERY_SOURCE = (
    "IRC §168(c) — 27.5-year straight-line recovery for residential rental "
    "property and 39-year for non-residential real property, both under the "
    "general depreciation system"
)
RECOVERY_VERIFIED = (
    "unverified — check against irs.gov Publication 527 and Publication 946")

# ── Underwriting thresholds ─────────────────────────────────────────────────

#: The floor most agency and DSCR lenders underwrite to. Below it the property
#: does not service its own debt with any margin and the borrower is the
#: reserve.
DSCR_LENDER_FLOOR = 1.20

#: Where a deal stops depending on everything going right. Between the floor
#: and here a deal is financeable but has roughly one bad quarter of slack.
DSCR_COMFORT = 1.25

#: Vacancy assumed when none is supplied. A pro-forma with zero vacancy is the
#: single most common overstatement in a broker's package; assuming zero here
#: would reproduce the error rather than catch it.
DEFAULT_VACANCY_RATE = 0.05

#: Non-payment and turnover loss beyond physical vacancy, when not supplied.
DEFAULT_CREDIT_LOSS_RATE = 0.01

#: Capital reserve as a share of gross rent when not supplied. **Deliberately
#: outside NOI** — see `net_operating_income` — but inside cash flow, because
#: roofs are not optional.
DEFAULT_CAPEX_RESERVE_RATE = 0.05

#: Selling costs at exit as a share of sale price — commission dominates.
DEFAULT_SELLING_COST_RATE = 0.07

#: A cap rate below this on a leveraged residential deal means the return is
#: coming from appreciation, not from the asset. Not a rejection, a relabelling.
THIN_CAP_RATE = 0.05

# ── 1031 clocks ─────────────────────────────────────────────────────────────

#: §1031(a)(3)(A). Calendar days from closing on the relinquished property to
#: identify replacement property **in writing to the Qualified Intermediary**.
#: Not extendable for any reason short of a declared disaster.
EXCHANGE_IDENTIFY_DAYS = 45

#: §1031(a)(3)(B). Calendar days to close — or the tax return due date for the
#: year of sale if that falls first, which it does for a Q4 sale unless the
#: return is extended.
EXCHANGE_CLOSE_DAYS = 180

# ── Cost segregation ────────────────────────────────────────────────────────

#: §168(c). Straight-line recovery period for residential rental property.
RESIDENTIAL_RECOVERY_YEARS = 27.5

#: §168(c). Non-residential real property.
COMMERCIAL_RECOVERY_YEARS = 39.0

#: Screening range for the share of depreciable basis a study typically
#: reclassifies to 5/7/15-year property. A **range, not an estimate** — the
#: actual figure is the output of the engineering study this screen exists to
#: decide whether to commission.
RECLASS_SHARE_LOW = 0.15
RECLASS_SHARE_HIGH = 0.30

#: Present-value benefit must exceed the study fee by this multiple before
#: commissioning one is obviously right. Below it the screen is inside its own
#: error bars and the answer is "get a quote and a free feasibility estimate",
#: not "yes".
MIN_BENEFIT_TO_COST = 3.0


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _money(x: float) -> str:
    return f"${x:,.0f}"


# ── Door 1: the $25,000 allowance ───────────────────────────────────────────


def allowance_available(
    magi: float,
    *,
    allowance: float | None,
    phaseout_start: float | None,
    phaseout_end: float | None,
) -> float | None:
    """§469(i) allowance after phase-out, or None if the figures are absent.

    Returns None rather than a guess. The allowance and the band are statutory
    dollar figures; this module refuses to carry its own copy of them.
    """
    if allowance is None or phaseout_start is None or phaseout_end is None:
        return None
    if magi <= phaseout_start:
        return float(allowance)
    if magi >= phaseout_end:
        return 0.0
    reduction = (magi - phaseout_start) * ALLOWANCE_PHASEOUT_RATE
    return max(0.0, float(allowance) - reduction)


# ── The gate ────────────────────────────────────────────────────────────────


@dataclass
class ActivityGate:
    """One rental activity, and whether its loss can reach wage income."""

    label: str
    avg_stay_days: float | None
    is_rental_activity: bool | None
    materially_participates: bool | None
    door: str | None
    expected_loss: float
    suspended_carryforward: float
    deductible_against_wages: float | None
    suspended_this_year: float | None
    findings: list[str] = field(default_factory=list)

    @property
    def open(self) -> bool:
        return self.door is not None


@dataclass
class GateResult:
    activities: list[ActivityGate]
    magi: float
    allowance: float | None
    reps_hours_met: bool | None
    reps_majority_met: bool | None
    reps: bool | None
    grouping_election: bool
    findings: list[str] = field(default_factory=list)

    @property
    def any_open(self) -> bool:
        return any(a.open for a in self.activities)

    @property
    def total_suspended(self) -> float:
        return sum(
            (a.suspended_this_year or 0.0) + a.suspended_carryforward
            for a in self.activities
        )


def assess_gate(
    activities: list[dict],
    *,
    magi: float,
    active_participation: bool | None = None,
    hours_real_property: float | None = None,
    hours_all_work: float | None = None,
    grouping_election: bool = False,
    allowance: float | None = None,
    phaseout_start: float | None = None,
    phaseout_end: float | None = None,
) -> GateResult:
    """Can these losses offset wage income? Runs before any deal model.

    Doors are tested in the order a W-2 household can actually use them:
    short-stay first, REPS second, the allowance last — which is the reverse of
    the order they are usually presented in.
    """
    reps_hours_met = (
        None if hours_real_property is None else hours_real_property >= REPS_MIN_HOURS
    )
    reps_majority_met = None
    if hours_real_property is not None and hours_all_work:
        reps_majority_met = (
            hours_real_property > REPS_MAJORITY_SHARE * hours_all_work
        )
    reps = None
    if reps_hours_met is not None and reps_majority_met is not None:
        reps = reps_hours_met and reps_majority_met

    allow = allowance_available(
        magi,
        allowance=allowance,
        phaseout_start=phaseout_start,
        phaseout_end=phaseout_end,
    )

    result = GateResult(
        activities=[],
        magi=magi,
        allowance=allow,
        reps_hours_met=reps_hours_met,
        reps_majority_met=reps_majority_met,
        reps=reps,
        grouping_election=grouping_election,
    )

    if allowance is None or phaseout_start is None or phaseout_end is None:
        result.findings.append(
            "**The $25,000 allowance cannot be evaluated.** "
            "`assumptions.passive_loss_allowance`, "
            "`assumptions.passive_loss_phaseout_start` and "
            "`assumptions.passive_loss_phaseout_end` are statutory dollar "
            "figures and this library will not carry its own copy of them. "
            "Supply them, or treat the allowance door as unresolved — not as "
            "closed."
        )
    elif allow == 0.0:
        result.findings.append(
            f"**Allowance door: closed.** MAGI of {_money(magi)} is at or above "
            f"the {_money(phaseout_end)} phase-out ceiling, so the "
            f"{_money(allowance)} allowance is fully phased out. It reduces by "
            f"{ALLOWANCE_PHASEOUT_RATE:.0%} of every dollar above "
            f"{_money(phaseout_start)}, which is why a household that earns "
            "enough to want it cannot have it."
        )
    elif allow is not None and allow > 0:
        if active_participation is False:
            result.findings.append(
                f"{_money(allow)} of allowance survives the phase-out, but "
                "`active_participation` is recorded as false and the allowance "
                "requires it. Active participation is a low bar — approving "
                "tenants, setting rents, authorising repairs — but it is not "
                "nothing, and a full-service property manager can defeat it."
            )
        elif active_participation is None:
            result.findings.append(
                f"{_money(allow)} of allowance may survive the phase-out, but "
                "`active_participation` is not recorded. Unknown is not false "
                "here; go and establish it."
            )
        else:
            result.findings.append(
                f"**Allowance door: partially open.** {_money(allow)} of loss "
                f"can offset wage income, phased down from "
                f"{_money(allowance)} by MAGI of {_money(magi)}. This is a "
                "household-wide cap across all activities, not per property."
            )

    if reps is True:
        result.findings.append(
            f"**REPS door: both tests pass** on the hours recorded "
            f"({hours_real_property:,.0f} in real property trades of "
            f"{hours_all_work:,.0f} total). This is the most heavily audited "
            "position in the individual tax code. It survives on a "
            "contemporaneous log — dates, hours, description — kept as you go. "
            "A reconstruction written the week the notice arrives has been "
            "rejected repeatedly in Tax Court."
        )
    elif reps is False:
        why = []
        if reps_hours_met is False:
            why.append(
                f"{hours_real_property:,.0f} hours is below the "
                f"{REPS_MIN_HOURS:,.0f}-hour floor"
            )
        if reps_majority_met is False:
            why.append(
                f"{hours_real_property:,.0f} of {hours_all_work:,.0f} total "
                f"working hours is not more than "
                f"{REPS_MAJORITY_SHARE:.0%} — this is the test a full-time job "
                "makes close to unattainable, and it is tested per spouse, not "
                "per household"
            )
        result.findings.append("**REPS door: closed** — " + "; ".join(why) + ".")
    else:
        result.findings.append(
            "**REPS door: unresolved.** `hours_real_property` and "
            "`hours_all_work` are not both recorded, so neither test can be "
            "run. Do not assume it fails; do not assume it passes."
        )

    if grouping_election:
        result.findings.append(
            "A **grouping election** under Reg. §1.469-9(g) is recorded: all "
            "rental interests are treated as one activity, so material "
            "participation is tested once against the combined hours rather "
            "than property by property. That is what makes REPS workable for a "
            "multi-property portfolio — and it cuts the other way on exit, "
            "because suspended losses are only released when the **entire "
            "grouped activity** is disposed of, not when one property sells."
        )
    elif len(activities) > 1:
        result.findings.append(
            f"{len(activities)} activities and no grouping election recorded. "
            "Material participation is then tested **separately for each "
            "property**, which is how a portfolio that clears the hours in "
            "aggregate fails on every individual property. Consider "
            "Reg. §1.469-9(g) — but read the disposition consequence above "
            "first; the election is not revocable at will."
        )

    allowance_pool = allow if (allow and active_participation) else 0.0

    for i, a in enumerate(activities):
        label = a.get("label") or f"activity #{i + 1}"
        loss = abs(float(a.get("expected_loss") or 0.0))
        carry = abs(float(a.get("suspended_losses") or 0.0))
        stay = a.get("avg_stay_days")
        hours = a.get("material_participation_hours")
        most = a.get("most_hours_of_anyone")

        g = ActivityGate(
            label=label,
            avg_stay_days=None if stay is None else float(stay),
            is_rental_activity=None if stay is None else float(stay) > SHORT_STAY_DAYS,
            materially_participates=None,
            door=None,
            expected_loss=loss,
            suspended_carryforward=carry,
            deductible_against_wages=None,
            suspended_this_year=None,
        )

        if hours is None:
            g.findings.append(
                "Participation hours are not recorded, so material "
                "participation cannot be tested. This is the weakest input in "
                "the whole gate and the one an examiner asks for first."
            )
        else:
            h = float(hours)
            if h >= MATERIAL_PARTICIPATION_SAFE_HARBOUR_HOURS:
                g.materially_participates = True
                g.findings.append(
                    f"{h:,.0f} hours clears the "
                    f"{MATERIAL_PARTICIPATION_SAFE_HARBOUR_HOURS:,.0f}-hour "
                    "safe harbour outright — no comparison against anyone else "
                    "needed."
                )
            elif h > MATERIAL_PARTICIPATION_HOURS and most is True:
                g.materially_participates = True
                g.findings.append(
                    f"{h:,.0f} hours, and more than any other individual — "
                    "material participation on the 100-hour test."
                )
            elif h > MATERIAL_PARTICIPATION_HOURS and most is None:
                g.findings.append(
                    f"{h:,.0f} hours clears 100, but whether that is more than "
                    "any other individual is not recorded. Count the cleaner "
                    "and the manager: on a short-stay property the cleaning "
                    "hours usually exceed the owner's, and that single fact "
                    "defeats the test."
                )
            else:
                g.materially_participates = False
                g.findings.append(
                    f"{h:,.0f} hours does not establish material participation"
                    + (
                        " — someone else does more."
                        if most is False
                        else f" — the 100-hour test needs more than "
                        f"{MATERIAL_PARTICIPATION_HOURS:,.0f} hours *and* more "
                        "than anyone else."
                    )
                )

        if stay is None:
            g.findings.append(
                "`avg_stay_days` is not recorded, so the short-stay exception "
                "cannot be tested. It is the average stay across the year, "
                "computed as total rental days divided by number of "
                "bookings — not the typical booking, and not the nightly "
                "minimum."
            )
        elif g.is_rental_activity is False:
            g.findings.append(
                f"Average stay of {float(stay):.1f} days is at or below "
                f"{SHORT_STAY_DAYS:.0f}, so under "
                "Reg. §1.469-1T(e)(3)(ii)(A) this is **not a rental "
                "activity**. The per se passive rule never attaches, and "
                "material participation alone decides it."
            )

        if g.is_rental_activity is False and g.materially_participates:
            g.door = "short_stay"
        elif reps and g.materially_participates:
            g.door = "reps"

        if g.door:
            g.deductible_against_wages = loss + carry
            g.suspended_this_year = 0.0
            g.findings.append(
                f"**Open via {g.door.replace('_', '-')}.** "
                f"{_money(loss)} of current loss"
                + (
                    f" and {_money(carry)} of suspended carryforward"
                    if carry
                    else ""
                )
                + " is non-passive and reaches wage income."
            )
        elif allowance_pool > 0:
            used = min(loss, allowance_pool)
            allowance_pool -= used
            g.door = "allowance" if used > 0 else None
            g.deductible_against_wages = used
            g.suspended_this_year = loss - used
            g.findings.append(
                f"{_money(used)} deductible under the allowance; "
                f"{_money(loss - used)} suspends. The carryforward of "
                f"{_money(carry)} is **not** released by the allowance — only "
                "by passive income or by disposition."
            )
        else:
            g.deductible_against_wages = 0.0
            g.suspended_this_year = loss
            g.findings.append(
                f"**Shut.** {_money(loss)} suspends and carries forward "
                "indefinitely. It is not lost: it offsets future passive "
                "income, and the whole accumulated balance is released in full "
                "on a fully taxable disposition of the activity to an "
                "unrelated party."
            )

        result.activities.append(g)

    if not result.any_open:
        result.findings.append(
            "**No door is open.** Any after-tax return, cost-segregation "
            "benefit or depreciation shelter quoted on these properties should "
            "assume a marginal benefit of **zero this year** — the deduction is "
            "deferred to disposition, not denied, but it is not this year's "
            "money and must not be discounted as if it were."
        )
    return result


# ── Underwriting ────────────────────────────────────────────────────────────


def net_operating_income(
    *,
    gross_rent: float,
    other_income: float = 0.0,
    vacancy_rate: float,
    credit_loss_rate: float,
    operating_expenses: float,
) -> float:
    """NOI = collected income less operating expenses.

    **Debt service and capital expenditure are excluded, on purpose.** NOI is a
    property-level figure: it has to be the same number regardless of how the
    buyer financed it, or cap rate stops comparing anything. Folding the
    mortgage into NOI is the classic error, and it flatters a cash purchase and
    punishes a leveraged one for no economic reason.

    Capex is excluded for a different reason — it is lumpy capital, not an
    annual operating cost — but it is real, so `underwrite()` puts it back in
    the cash flow line below NOI.
    """
    collected = gross_rent * (1.0 - vacancy_rate - credit_loss_rate)
    return collected + other_income - operating_expenses


def irr(cashflows: list[float]) -> float | None:
    """IRR by bisection. None when the sign never changes."""
    if not cashflows or all(c >= 0 for c in cashflows) or all(c <= 0 for c in cashflows):
        return None

    def npv(rate: float) -> float:
        return sum(c / (1.0 + rate) ** t for t, c in enumerate(cashflows))

    lo, hi = -0.9999, 10.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2.0
        f_mid = npv(mid)
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0


@dataclass
class YearRow:
    year: int
    gross_rent: float
    noi: float
    debt_service: float
    capex: float
    cash_flow: float


@dataclass
class Underwriting:
    label: str
    price: float
    cash_invested: float
    loan: float
    annual_debt_service: float
    noi_year1: float
    cap_rate: float | None
    cash_on_cash: float | None
    dscr: float | None
    years: list[YearRow]
    net_sale_proceeds: float
    irr: float | None
    equity_multiple: float | None
    findings: list[str] = field(default_factory=list)

    @property
    def financeable(self) -> bool | None:
        if self.dscr is None:
            return None
        return self.dscr >= DSCR_LENDER_FLOOR


def underwrite(deal: dict) -> Underwriting:
    """Year-1 metrics plus a multi-year IRR. Nominal, pre-investor-tax."""
    label = deal.get("label") or "unnamed deal"
    price = float(deal.get("price") or 0.0)
    closing_costs = float(deal.get("closing_costs") or 0.0)
    down = float(deal.get("down_payment") or 0.0)
    loan = max(0.0, price - down)
    rate = float(deal.get("loan_rate") or 0.0)
    term = int(deal.get("loan_term_years") or 30)
    hold = int(deal.get("hold_years") or 5)

    gross_rent = float(deal.get("gross_rent_monthly") or 0.0) * 12.0
    other_income = float(deal.get("other_income_monthly") or 0.0) * 12.0

    findings: list[str] = []

    vac = deal.get("vacancy_rate")
    if vac is None:
        vac = DEFAULT_VACANCY_RATE
        findings.append(
            f"No vacancy rate recorded; assumed {_pct(DEFAULT_VACANCY_RATE)}. "
            "A package quoting zero vacancy is quoting a number that has never "
            "occurred over a full holding period."
        )
    credit = deal.get("credit_loss_rate")
    if credit is None:
        credit = DEFAULT_CREDIT_LOSS_RATE
        findings.append(
            f"No credit-loss rate recorded; assumed "
            f"{_pct(DEFAULT_CREDIT_LOSS_RATE)} for non-payment and turnover on "
            "top of physical vacancy."
        )
    capex_rate = deal.get("capex_reserve_rate")
    if capex_rate is None:
        capex_rate = DEFAULT_CAPEX_RESERVE_RATE
        findings.append(
            f"No capital reserve recorded; assumed "
            f"{_pct(DEFAULT_CAPEX_RESERVE_RATE)} of gross rent. It is outside "
            "NOI by definition and inside cash flow by necessity."
        )
    selling_rate = deal.get("selling_cost_rate")
    if selling_rate is None:
        selling_rate = DEFAULT_SELLING_COST_RATE
        findings.append(
            f"No selling-cost rate recorded; assumed {_pct(DEFAULT_SELLING_COST_RATE)} "
            "of sale price at exit."
        )

    vac, credit = float(vac), float(credit)
    capex_rate, selling_rate = float(capex_rate), float(selling_rate)

    opex_map = deal.get("operating_expenses") or {}
    opex = float(sum(float(v or 0.0) for v in opex_map.values()))
    if not opex_map:
        findings.append(
            "**No operating expenses recorded.** NOI, cap rate, cash-on-cash "
            "and DSCR are all therefore overstated, and by an unknown amount. "
            "Treat every figure below as an upper bound, not an estimate."
        )

    rent_growth = float(deal.get("rent_growth") or 0.0)
    expense_growth = float(deal.get("expense_growth") or rent_growth)
    appreciation = float(deal.get("appreciation") or 0.0)

    ds = monthly_payment(loan, rate, term) * 12.0
    cash_invested = down + closing_costs

    rows: list[YearRow] = []
    for t in range(1, hold + 1):
        rent_t = gross_rent * (1.0 + rent_growth) ** (t - 1)
        other_t = other_income * (1.0 + rent_growth) ** (t - 1)
        opex_t = opex * (1.0 + expense_growth) ** (t - 1)
        noi_t = net_operating_income(
            gross_rent=rent_t,
            other_income=other_t,
            vacancy_rate=vac,
            credit_loss_rate=credit,
            operating_expenses=opex_t,
        )
        capex_t = rent_t * capex_rate
        rows.append(
            YearRow(t, rent_t, noi_t, ds, capex_t, noi_t - ds - capex_t)
        )

    noi1 = rows[0].noi if rows else 0.0
    cap_rate = noi1 / price if price else None
    coc = (rows[0].cash_flow / cash_invested) if (rows and cash_invested) else None
    dscr = (noi1 / ds) if ds else None

    sale_price = price * (1.0 + appreciation) ** hold
    _, _, balance = amortise(loan, rate, term, hold * 12)
    net_sale = sale_price - sale_price * selling_rate - balance

    flows = [-cash_invested] + [r.cash_flow for r in rows]
    if flows:
        flows[-1] += net_sale
    deal_irr = irr(flows)
    total_back = sum(r.cash_flow for r in rows) + net_sale
    multiple = (total_back / cash_invested) if cash_invested else None

    u = Underwriting(
        label=label,
        price=price,
        cash_invested=cash_invested,
        loan=loan,
        annual_debt_service=ds,
        noi_year1=noi1,
        cap_rate=cap_rate,
        cash_on_cash=coc,
        dscr=dscr,
        years=rows,
        net_sale_proceeds=net_sale,
        irr=deal_irr,
        equity_multiple=multiple,
        findings=findings,
    )

    if dscr is not None:
        if dscr < DSCR_LENDER_FLOOR:
            u.findings.append(
                f"**DSCR of {dscr:.2f} is below the {DSCR_LENDER_FLOOR:.2f} "
                "lender floor.** Most DSCR and agency programmes will not "
                "write it at this leverage. The fix is a larger down payment "
                "or a lower price, not a more optimistic rent — and if the "
                "property cannot service its own debt, the borrower's W-2 is "
                "the reserve."
            )
        elif dscr < DSCR_COMFORT:
            u.findings.append(
                f"DSCR of {dscr:.2f} clears the {DSCR_LENDER_FLOOR:.2f} floor "
                f"but sits under {DSCR_COMFORT:.2f}. That is roughly one bad "
                "quarter of slack: a single extended vacancy or one insurance "
                "renewal puts it underwater."
            )
        else:
            u.findings.append(
                f"DSCR of {dscr:.2f} clears the {DSCR_COMFORT:.2f} comfort "
                "level — the property services its own debt with margin."
            )

    if cap_rate is not None and cap_rate < THIN_CAP_RATE:
        u.findings.append(
            f"Cap rate of {_pct(cap_rate)} is below {_pct(THIN_CAP_RATE)}. "
            "Whatever return this deal produces is coming from appreciation "
            f"and amortisation, not from the asset's income. The "
            f"{_pct(appreciation)} appreciation assumption is therefore doing "
            "most of the work in the IRR below, and it is an assumption, not a "
            "cash flow."
        )

    if coc is not None and coc < 0:
        u.findings.append(
            f"Year-1 cash-on-cash is {_pct(coc)} — the property consumes "
            f"{_money(-rows[0].cash_flow)} of outside cash per year. That is a "
            "position, not necessarily a mistake, but it has to be funded from "
            f"somewhere for {hold} years and the funding has to be named."
        )

    u.findings.append(
        f"Weakest input: the **{_pct(appreciation)} appreciation** assumption — "
        f"{_money(net_sale)} of the return arrives as sale proceeds at the "
        "horizon, so the IRR is a forecast wearing a metric's clothes. The "
        "year-1 figures above it are not."
    )
    return u


# ── 1031 exchange ───────────────────────────────────────────────────────────


@dataclass
class ExchangeResult:
    amount_realized: float
    adjusted_basis: float
    total_gain: float
    unrecaptured_1250: float
    capital_gain: float
    tax_if_sold: float | None
    net_equity: float
    equity_into_replacement: float
    cash_boot: float
    debt_boot: float
    recognized_gain: float
    tax_if_exchanged: float | None
    deferred_gain: float
    fully_deferred: bool
    identify_by: _dt.date | None
    close_by: _dt.date | None
    days_to_identify: int | None
    days_to_close: int | None
    findings: list[str] = field(default_factory=list)

    @property
    def tax_deferred(self) -> float | None:
        if self.tax_if_sold is None or self.tax_if_exchanged is None:
            return None
        return self.tax_if_sold - self.tax_if_exchanged


def _gain_tax(
    *,
    unrecaptured: float,
    capital_gain: float,
    recapture_rate: float | None,
    ltcg_rate: float | None,
    niit_rate: float | None,
    state_rate: float | None,
) -> float | None:
    if recapture_rate is None or ltcg_rate is None:
        return None
    total = unrecaptured + capital_gain
    tax = unrecaptured * recapture_rate + capital_gain * ltcg_rate
    tax += total * (niit_rate or 0.0)
    tax += total * (state_rate or 0.0)
    return tax


def model_exchange(
    x: dict,
    *,
    as_of: _dt.date | None = None,
    recapture_rate: float | None = None,
    ltcg_rate: float | None = None,
    niit_rate: float | None = None,
    state_rate: float | None = None,
    discount_rate: float | None = None,
) -> ExchangeResult:
    """Defer or pay — with depreciation recapture counted, and the clocks."""
    sale_price = float(x.get("sale_price") or 0.0)
    selling_costs = float(x.get("selling_costs") or 0.0)
    purchase_price = float(x.get("purchase_price") or 0.0)
    improvements = float(x.get("improvements") or 0.0)
    depreciation = float(x.get("accumulated_depreciation") or 0.0)
    relinquished_debt = float(x.get("relinquished_debt") or 0.0)
    replacement_value = float(x.get("replacement_value") or 0.0)
    replacement_debt = float(x.get("replacement_debt") or 0.0)

    amount_realized = sale_price - selling_costs
    adjusted_basis = purchase_price + improvements - depreciation
    total_gain = amount_realized - adjusted_basis
    unrecaptured = max(0.0, min(depreciation, total_gain))
    capital_gain = max(0.0, total_gain - unrecaptured)

    tax_if_sold = _gain_tax(
        unrecaptured=unrecaptured,
        capital_gain=capital_gain,
        recapture_rate=recapture_rate,
        ltcg_rate=ltcg_rate,
        niit_rate=niit_rate,
        state_rate=state_rate,
    )

    net_equity = amount_realized - relinquished_debt
    equity_in = replacement_value - replacement_debt
    cash_boot = max(0.0, net_equity - equity_in)
    cash_added = max(0.0, equity_in - net_equity)
    debt_relief = max(0.0, relinquished_debt - replacement_debt)
    debt_boot = max(0.0, debt_relief - cash_added)
    total_boot = cash_boot + debt_boot
    recognized = max(0.0, min(total_boot, total_gain))

    recognized_unrecaptured = min(recognized, unrecaptured)
    recognized_ltcg = recognized - recognized_unrecaptured
    tax_if_exchanged = _gain_tax(
        unrecaptured=recognized_unrecaptured,
        capital_gain=recognized_ltcg,
        recapture_rate=recapture_rate,
        ltcg_rate=ltcg_rate,
        niit_rate=niit_rate,
        state_rate=state_rate,
    )

    sale_date = x.get("sale_date")
    if isinstance(sale_date, _dt.datetime):
        sale_date = sale_date.date()
    elif isinstance(sale_date, str):
        try:
            sale_date = _dt.date.fromisoformat(sale_date)
        except ValueError:
            sale_date = None
    elif not isinstance(sale_date, _dt.date):
        sale_date = None

    identify_by = close_by = None
    if sale_date:
        identify_by = sale_date + _dt.timedelta(days=EXCHANGE_IDENTIFY_DAYS)
        close_by = sale_date + _dt.timedelta(days=EXCHANGE_CLOSE_DAYS)
        due = x.get("tax_return_due")
        if isinstance(due, _dt.datetime):
            due = due.date()
        elif isinstance(due, str):
            try:
                due = _dt.date.fromisoformat(due)
            except ValueError:
                due = None
        if isinstance(due, _dt.date) and due < close_by:
            close_by = due

    d_id = (identify_by - as_of).days if (identify_by and as_of) else None
    d_cl = (close_by - as_of).days if (close_by and as_of) else None

    fully_deferred = (
        replacement_value >= amount_realized
        and equity_in >= net_equity - 1e-9
        and recognized == 0.0
    )

    r = ExchangeResult(
        amount_realized=amount_realized,
        adjusted_basis=adjusted_basis,
        total_gain=total_gain,
        unrecaptured_1250=unrecaptured,
        capital_gain=capital_gain,
        tax_if_sold=tax_if_sold,
        net_equity=net_equity,
        equity_into_replacement=equity_in,
        cash_boot=cash_boot,
        debt_boot=debt_boot,
        recognized_gain=recognized,
        tax_if_exchanged=tax_if_exchanged,
        deferred_gain=total_gain - recognized,
        fully_deferred=fully_deferred,
        identify_by=identify_by,
        close_by=close_by,
        days_to_identify=d_id,
        days_to_close=d_cl,
    )

    if recapture_rate is None or ltcg_rate is None:
        r.findings.append(
            "**No tax figure is reported.** "
            "`assumptions.depreciation_recapture_rate` and "
            "`assumptions.ltcg_rate` are missing, and this module will not "
            "supply rates from its own memory of the code. The gain "
            "composition above is still correct and is the part that matters: "
            f"{_money(unrecaptured)} of it is unrecaptured §1250 gain taxed at "
            "a **higher rate than long-term capital gain**, which is the "
            "component people leave out of the do-I-bother arithmetic."
        )
    else:
        r.findings.append(
            f"Gain splits {_money(unrecaptured)} unrecaptured §1250 at "
            f"{_pct(recapture_rate)} and {_money(capital_gain)} long-term gain "
            f"at {_pct(ltcg_rate)}"
            + (f", plus {_pct(niit_rate)} NIIT" if niit_rate else "")
            + (f" and {_pct(state_rate)} state" if state_rate else "")
            + ". Depreciation you **were allowed or allowable** is recaptured "
            "whether or not you actually claimed it — skipping depreciation "
            "does not avoid this."
        )

    if cash_boot > 0:
        r.findings.append(
            f"**Cash boot of {_money(cash_boot)}.** Net equity of "
            f"{_money(net_equity)} exceeds the {_money(equity_in)} going into "
            "the replacement, and the difference is taxable now, gain first. "
            "Cash boot is not offset by taking on more debt."
        )
    if debt_boot > 0:
        r.findings.append(
            f"**Mortgage boot of {_money(debt_boot)}** — the subtle one. "
            f"Relinquished debt of {_money(relinquished_debt)} is being "
            f"replaced with {_money(replacement_debt)}, and debt relief is "
            "income. Injecting "
            f"{_money(debt_boot)} of outside cash into the exchange offsets "
            "it dollar for dollar; taking on more replacement debt also works. "
            "Doing neither produces a tax bill with no cash arriving to pay it."
        )
    if recognized == 0.0 and total_gain > 0:
        r.findings.append(
            f"No boot: the full {_money(total_gain)} defers into the "
            "replacement property, which takes a carryover basis. The gain is "
            "postponed, not forgiven — it compounds into every subsequent "
            "exchange until a taxable sale, or until a step-up at death "
            "eliminates it. Plan for one of those two endings deliberately."
        )

    if not fully_deferred and total_gain > 0:
        r.findings.append(
            "**Full deferral fails the rule of thumb.** Buy replacement "
            f"property of equal or greater value ({_money(amount_realized)}) "
            f"and reinvest all net equity ({_money(net_equity)}). This "
            f"replacement is {_money(replacement_value)} with "
            f"{_money(equity_in)} of equity going in."
        )

    if identify_by and close_by:
        r.findings.append(
            f"**Clocks: identify in writing by {identify_by.isoformat()}** "
            f"({EXCHANGE_IDENTIFY_DAYS} days) **and close by "
            f"{close_by.isoformat()}** ({EXCHANGE_CLOSE_DAYS} days, or the "
            "return due date for the year of sale if earlier — file an "
            "extension if a Q4 sale would otherwise truncate this). Both run "
            "from the closing on the relinquished property, both are calendar "
            "days, and neither is extendable."
            + (
                f" As of the facts date, {d_id} days remain to identify and "
                f"{d_cl} to close."
                if d_id is not None
                else ""
            )
        )
        if d_id is not None and d_id < 0:
            r.findings.append(
                "**The identification window has already passed.** If nothing "
                "was identified in writing to the QI inside it, the exchange "
                "has failed and this is a taxable sale. Model it as one."
            )
    else:
        r.findings.append(
            "No `sale_date` recorded, so the 45- and 180-day clocks cannot be "
            "dated. They are the part of an exchange that actually fails."
        )

    r.findings.append(
        "**The Qualified Intermediary must hold the proceeds continuously.** "
        "If the seller ever has the right to receive, pledge or borrow against "
        "the funds — including money routed briefly through their own "
        "account — constructive receipt invalidates the entire exchange "
        "retroactively. Engage the QI **before** closing; it cannot be fixed "
        "afterwards."
    )
    r.findings.append(
        "Identify a **backup**. A DST interest can be named as a second or "
        "third identified property and closed quickly, which converts a failed "
        "search at day 44 into a partial deferral rather than a full tax bill. "
        "It is illiquid and fee-heavy, so it is a fallback, not a plan."
    )

    if (
        discount_rate is not None
        and r.tax_deferred
        and x.get("deferral_years")
    ):
        yrs = float(x["deferral_years"])
        pv = r.tax_deferred * (1.0 - 1.0 / (1.0 + discount_rate) ** yrs)
        r.findings.append(
            f"Deferring {_money(r.tax_deferred)} for {yrs:.0f} years at "
            f"{_pct(discount_rate)} is worth about {_money(pv)} in present "
            "value. Weigh that against QI fees, a compressed search, and the "
            "risk of overpaying for a replacement because the clock was "
            "running — the commonest way an exchange loses money while "
            "succeeding on paper."
        )
    return r


# ── Cost segregation screen ─────────────────────────────────────────────────


@dataclass
class CostSegScreen:
    label: str
    depreciable_basis: float
    recovery_years: float
    reclass_low: float
    reclass_high: float
    accelerated_deduction_low: float | None
    accelerated_deduction_high: float | None
    tax_benefit_low: float | None
    tax_benefit_high: float | None
    pv_benefit_low: float | None
    pv_benefit_high: float | None
    study_cost: float | None
    benefit_to_cost: float | None
    gate_open: bool | None
    worth_commissioning: bool | None
    findings: list[str] = field(default_factory=list)


def screen_cost_segregation(
    p: dict,
    *,
    gate_open: bool | None,
    marginal_rate: float | None,
    bonus_rate: float | None,
    discount_rate: float | None,
    state_rate: float | None = None,
) -> CostSegScreen:
    """Would a study plausibly pay for itself? Not a study, and not close.

    A real cost segregation study is an engineering exercise: a site visit, a
    take-off of every component, and an allocation defensible under audit. This
    function decides only whether the economics are in the region where paying
    for one makes sense, using a **range** for the reclassified share because
    the actual figure is the study's output, not its input.
    """
    label = p.get("label") or "unnamed property"
    basis = float(p.get("depreciable_basis") or 0.0)
    kind = (p.get("property_type") or "residential").lower()
    recovery = (
        RESIDENTIAL_RECOVERY_YEARS
        if kind.startswith("resid")
        else COMMERCIAL_RECOVERY_YEARS
    )
    study_cost = p.get("study_cost")
    study_cost = None if study_cost is None else float(study_cost)
    hold = float(p.get("hold_years") or 0.0)

    low = basis * RECLASS_SHARE_LOW
    high = basis * RECLASS_SHARE_HIGH

    s = CostSegScreen(
        label=label,
        depreciable_basis=basis,
        recovery_years=recovery,
        reclass_low=low,
        reclass_high=high,
        accelerated_deduction_low=None,
        accelerated_deduction_high=None,
        tax_benefit_low=None,
        tax_benefit_high=None,
        pv_benefit_low=None,
        pv_benefit_high=None,
        study_cost=study_cost,
        benefit_to_cost=None,
        gate_open=gate_open,
        worth_commissioning=None,
    )

    s.findings.append(
        f"Screening range only: a study typically reclassifies "
        f"{_pct(RECLASS_SHARE_LOW)}–{_pct(RECLASS_SHARE_HIGH)} of depreciable "
        "basis to 5-, 7- and 15-year property. The real number depends on the "
        "building, and producing it **is** the study. Land is never "
        "depreciable and must already be excluded from "
        "`depreciable_basis` — if the purchase price was entered here, every "
        "figure below is overstated."
    )

    if bonus_rate is None or marginal_rate is None:
        s.findings.append(
            "**No benefit figure is reported.** "
            "`assumptions.bonus_depreciation_rate` and "
            "`assumptions.marginal_tax_rate` are required, and the bonus "
            "percentage in particular is legislated and has changed in most "
            "recent years. The structure holds without them: reclassified "
            f"basis of {_money(low)}–{_money(high)} would otherwise recover "
            f"over {recovery:.1f} years."
        )
        return s

    def accel(reclassed: float) -> float:
        # Year-1 deduction under bonus, less the straight-line the same basis
        # would have produced anyway. Only the difference is acceleration.
        return reclassed * bonus_rate - reclassed / recovery

    s.accelerated_deduction_low = accel(low)
    s.accelerated_deduction_high = accel(high)
    combined_rate = marginal_rate + (state_rate or 0.0)
    s.tax_benefit_low = s.accelerated_deduction_low * combined_rate
    s.tax_benefit_high = s.accelerated_deduction_high * combined_rate

    if gate_open is False:
        s.pv_benefit_low = 0.0
        s.pv_benefit_high = 0.0
        s.worth_commissioning = False
        s.findings.append(
            "**The gate is shut, so the benefit is zero this year.** The "
            f"{_money(s.tax_benefit_low)}–{_money(s.tax_benefit_high)} above is "
            "what the deduction would be worth *if it could be deducted*. It "
            "cannot: it enlarges a suspended passive loss instead, released "
            "only against future passive income or on disposition. "
            "**Accelerating a loss you cannot use is worth nothing** — and it "
            "costs the study fee. Run `passive-loss-eligibility` first and "
            "come back if a door opens."
        )
        return s

    if gate_open is None:
        s.findings.append(
            "Passive-loss eligibility is unresolved, so the figures below are "
            "conditional on a door being open. Resolve the gate before "
            "spending anything."
        )

    if discount_rate is None or hold <= 0:
        s.findings.append(
            "No discount rate or holding period recorded, so the timing "
            "benefit cannot be present-valued — and timing is the entire "
            "benefit. The gross year-1 figures below are not the value of the "
            "study."
        )
    else:
        factor = 1.0 - 1.0 / (1.0 + discount_rate) ** hold
        s.pv_benefit_low = s.tax_benefit_low * factor
        s.pv_benefit_high = s.tax_benefit_high * factor
        s.findings.append(
            f"Cost segregation is a **timing** benefit, not a permanent one. "
            f"Over a {hold:.0f}-year hold at {_pct(discount_rate)}, deferring "
            f"{_money(s.tax_benefit_low)}–{_money(s.tax_benefit_high)} of tax "
            f"is worth {_money(s.pv_benefit_low)}–{_money(s.pv_benefit_high)} "
            "today. Quoting the year-1 saving as the value of the study "
            "overstates it by the whole reversal."
        )
        if study_cost:
            s.benefit_to_cost = s.pv_benefit_low / study_cost
            s.worth_commissioning = s.benefit_to_cost >= MIN_BENEFIT_TO_COST
            verdict = (
                f"clears the {MIN_BENEFIT_TO_COST:.0f}× bar"
                if s.worth_commissioning
                else f"does not clear the {MIN_BENEFIT_TO_COST:.0f}× bar, so "
                "the screen is inside its own error bars — get a free "
                "feasibility estimate before paying for the study"
            )
            s.findings.append(
                f"At the conservative end, present-value benefit of "
                f"{_money(s.pv_benefit_low)} against a {_money(study_cost)} "
                f"fee is {s.benefit_to_cost:.1f}× — {verdict}."
            )

    s.findings.append(
        "**Recapture reverses part of it on sale.** The reclassified 5- and "
        "7-year personal property is §1245 property, recaptured at **ordinary "
        "income rates** rather than the §1250 rate that applies to the "
        "building. If the marginal rate at sale exceeds the unrecaptured §1250 "
        "rate, the study has converted some future capital-rate gain into "
        "future ordinary income — a rate cost, not just a timing one. A short "
        "hold makes that worse, because the deferral has less time to be worth "
        "anything."
    )
    s.findings.append(
        "Weakest input: the reclassified share. Everything above moves "
        "linearly with it, and it is a range precisely because nobody knows it "
        "until an engineer walks the building."
    )
    return s
