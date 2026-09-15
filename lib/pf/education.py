"""Education funding: the gap, the ordering rule, and 529 mechanics.

## The ordering rule is the whole skill

**Retirement funding comes before education funding.** Not as a preference —
as an asymmetry:

    You can borrow for education. You cannot borrow for retirement.

A household that underfunds retirement to fully fund college converts a
solvable problem into an unsolvable one, and the children inherit the
consequence anyway in the form of parents who cannot support themselves. Every
other finding in this module is subordinate to that, and the report says so
before it says anything about a gap.

## A 529 has exactly one beneficiary

Households think of "the college fund". The form names one child. With more
than one child and one account, either the balance is earmarked for one of
them or the beneficiary gets changed mid-stream — which is permitted, and is
a decision rather than an assumption. The module reports pooled accounts as
unallocated rather than dividing them, because dividing them would invent an
allocation nobody made.

## State benefits are jurisdiction-specific and frequently absent

Some states deduct 529 contributions from state income tax; some have no
income tax so the question does not arise; and some — California among the
largest — tax income and offer no deduction at all. Same cited-table pattern
as `jurisdiction.py`: a state is in the table only if checked, and anything
else returns unknown.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Education costs have historically outrun general inflation. Used when the
#: facts file does not supply a rate.
DEFAULT_COST_INFLATION = 0.05

#: Real return assumed on education savings. Deliberately below the
#: retirement default: money needed on a fixed near date cannot be invested
#: the same way as money needed in thirty years.
DEFAULT_REAL_RETURN = 0.03

#: Typical age at which study begins, when not supplied.
DEFAULT_START_AGE = 18
DEFAULT_YEARS_OF_STUDY = 4

#: Inside this many years of the money being needed, an equity-heavy glide
#: path is taking a risk the timetable cannot absorb — the bill arrives on a
#: fixed date whatever the market did.
GLIDE_DERISK_YEARS = 3

#: Federal aid assessment rates. A parent-owned 529 is assessed as a parent
#: asset; the same money held in the student's name is assessed far harder.
PARENT_ASSET_ASSESSMENT = 0.0564
STUDENT_ASSET_ASSESSMENT = 0.20

#: SECURE 2.0 529-to-Roth rollover. Lifetime cap per beneficiary, minimum
#: account age, and a look-back that excludes recent contributions.
ROTH_ROLLOVER_LIFETIME_CAP = 35_000
ROTH_ROLLOVER_MIN_ACCOUNT_YEARS = 15
ROTH_ROLLOVER_CONTRIBUTION_LOOKBACK_YEARS = 5


@dataclass(frozen=True)
class StateBenefit:
    state: str
    known: bool
    has_income_tax: bool | None = None
    deduction_available: bool | None = None
    note: str = ""
    source: str = ""
    verified_on: str = ""


_STATE_529: dict[str, StateBenefit] = {
    "CA": StateBenefit(
        "CA", True, has_income_tax=True, deduction_available=False,
        note="California taxes income and offers no state deduction or credit "
             "for 529 contributions. The in-state plan therefore has no tax "
             "advantage over any other state's plan — choose on fees and "
             "investment options alone.",
        source="CA Rev. & Tax. Code — no 529 contribution deduction",
        verified_on="unverified — check against ftb.ca.gov",
    ),
    "TX": StateBenefit(
        "TX", True, has_income_tax=False, deduction_available=False,
        note="Texas levies no state income tax, so a state deduction cannot "
             "exist and the in-state plan carries no tax advantage. Choose on "
             "fees and investment options alone.",
        source="No state personal income tax",
        verified_on="unverified — check against comptroller.texas.gov",
    ),
}

STATE_529_SOURCE = "state 529 income-tax treatment"
STATE_529_VERIFIED = "unverified — check each state's revenue authority"


def state_benefit(state: str | None) -> StateBenefit:
    if not state:
        return StateBenefit("??", False)
    return _STATE_529.get(state.strip().upper(), StateBenefit(state.upper(), False))


def states_available() -> list[str]:
    return sorted(_STATE_529)


# ── projection ──────────────────────────────────────────────────────────────


@dataclass
class ChildPlan:
    member_id: str
    age: int | None
    years_until_start: float | None
    years_of_study: int
    annual_cost_today: float
    projected_cost: float
    allocated_savings: float
    projected_savings: float
    gap: float
    findings: list[str] = field(default_factory=list)

    @property
    def funded_share(self) -> float:
        return (self.projected_savings / self.projected_cost
                if self.projected_cost else 0.0)


@dataclass
class EducationPlan:
    children: list[ChildPlan] = field(default_factory=list)
    unallocated_savings: float = 0.0
    findings: list[str] = field(default_factory=list)
    mechanics: list[str] = field(default_factory=list)

    @property
    def total_projected_cost(self) -> float:
        return sum(c.projected_cost for c in self.children)

    @property
    def total_gap(self) -> float:
        return sum(max(0.0, c.gap) for c in self.children)


def project_cost(annual_cost_today: float, years_until_start: float,
                 years_of_study: int, inflation: float) -> float:
    """Total nominal cost, inflating each year of study separately.

    Inflating the whole bill to the start date understates it: year four costs
    three more years of inflation than year one.
    """
    total = 0.0
    for y in range(years_of_study):
        total += annual_cost_today * (1 + inflation) ** (years_until_start + y)
    return total


def grow(value: float, years: float, real_return: float) -> float:
    return value * (1 + real_return) ** max(0.0, years)


def plan_for(
    children_raw: list[dict],
    *,
    members: list[dict],
    accounts: list[dict],
    cost_inflation: float = DEFAULT_COST_INFLATION,
    real_return: float = DEFAULT_REAL_RETURN,
    state: str | None = None,
) -> EducationPlan:
    by_id = {m.get("id"): m for m in members}
    p = EducationPlan()

    # Allocate accounts to beneficiaries. An account with no beneficiary is
    # reported unallocated rather than split — splitting would invent an
    # allocation nobody made, and a 529 names exactly one person.
    allocated: dict[str, float] = {}
    for acc in accounts or []:
        ben = acc.get("beneficiary")
        val = float(acc.get("value") or 0)
        if ben:
            allocated[ben] = allocated.get(ben, 0.0) + val
        else:
            p.unallocated_savings += val

    for row in children_raw or []:
        mid = row.get("member")
        m = by_id.get(mid, {})
        age = m.get("age")
        start = row.get("start_age", DEFAULT_START_AGE)
        years_of_study = int(row.get("years_of_study") or DEFAULT_YEARS_OF_STUDY)
        cost = float(row.get("annual_cost_today") or 0)

        until = max(0.0, start - age) if age is not None else None
        projected = (project_cost(cost, until, years_of_study, cost_inflation)
                     if until is not None else 0.0)
        saved = allocated.get(mid, 0.0)
        grown = grow(saved, until or 0, real_return)

        c = ChildPlan(
            member_id=mid, age=age, years_until_start=until,
            years_of_study=years_of_study, annual_cost_today=cost,
            projected_cost=projected, allocated_savings=saved,
            projected_savings=grown, gap=projected - grown,
        )

        if age is None:
            c.findings.append(
                "No age recorded, so the timetable cannot be computed. "
                "Years-until-enrolment drives everything here."
            )
        elif until == 0:
            c.findings.append(
                "**Already at or past enrolment age.** The bill is current, "
                "not future — this is a cash-flow question now, and any "
                "balance earmarked here should already be out of equities."
            )
        elif until <= GLIDE_DERISK_YEARS:
            c.findings.append(
                f"**{until:.0f} year(s) until the first bill.** Money needed "
                f"on a fixed near date should not be exposed to a market that "
                f"can be down when it arrives. Check the glide path — an "
                f"age-based option usually handles this, a static equity "
                f"allocation does not."
            )
        if saved == 0 and p.unallocated_savings:
            c.findings.append(
                "No account names this child. See the pooled-balance note."
            )
        p.children.append(c)

    if p.unallocated_savings:
        named = sum(1 for c in p.children if c.allocated_savings > 0)
        p.findings.append(
            f"**{_money(p.unallocated_savings)} of education savings is not "
            f"attributed to a named beneficiary**, and {len(p.children) - named} "
            "child(ren) have no account naming them. A 529 has exactly one "
            "beneficiary at a time. If the household thinks of this as a "
            "shared college fund, the form does not — either it is earmarked "
            "for one child, or the beneficiary gets changed mid-stream, which "
            "is permitted but is a decision rather than an assumption. Check "
            "the account and record who is named."
        )

    return p


# ── mechanics ───────────────────────────────────────────────────────────────


def mechanics_notes(*, state: str | None, has_leftover_risk: bool) -> list[str]:
    out: list[str] = []
    sb = state_benefit(state)

    if not sb.known:
        out.append(
            f"**529 state-tax treatment for {state or 'this state'} is not in "
            "the table.** Some states deduct contributions, some have no "
            "income tax, and some tax income and offer nothing. Check before "
            "assuming the in-state plan is the right one — where there is no "
            "deduction, it has no tax advantage over any other state's plan "
            "and should be chosen on fees alone."
        )
    else:
        out.append(f"**{sb.state}:** {sb.note}")

    out.append(
        "**Financial aid treats a parent-owned 529 lightly** — assessed at "
        f"about {PARENT_ASSET_ASSESSMENT:.2%} of value, against "
        f"{STUDENT_ASSET_ASSESSMENT:.0%} for assets held in the student's own "
        "name. Moving money into a child's name to save tax can cost more in "
        "lost aid than it saves."
    )

    if has_leftover_risk:
        out.append(
            f"**Leftover balances are no longer trapped, but the escape is "
            f"capped.** Under SECURE 2.0 a 529 can be rolled to the "
            f"beneficiary's Roth IRA up to "
            f"{_money(ROTH_ROLLOVER_LIFETIME_CAP)} in a lifetime, and only if "
            f"the account has existed at least "
            f"{ROTH_ROLLOVER_MIN_ACCOUNT_YEARS} years. Contributions from the "
            f"last {ROTH_ROLLOVER_CONTRIBUTION_LOOKBACK_YEARS} years are "
            "ineligible, the rollover counts against the beneficiary's annual "
            "Roth limit, and they need earned income to support it. Useful, "
            "slow, and not a reason to overfund."
        )
        out.append(
            "The other routes for a leftover balance: change the beneficiary "
            "to another qualifying family member, hold it for a future "
            "generation, or withdraw and pay tax plus a penalty on the "
            "earnings only — the contributions always come back untaxed."
        )

    out.append(
        "**Superfunding** lets five years of gift-tax annual exclusions be "
        "made at once, front-loading growth. It uses up those years of "
        "exclusion for that beneficiary, so it interacts with any other "
        "gifting."
    )
    return out


def ordering_rule(*, retirement_on_track: bool | None,
                  retirement_age_at_target: float | None) -> list[str]:
    """The finding that outranks every other in this module."""
    out = [
        "**Retirement funding comes before education funding.** Not a "
        "preference — an asymmetry: **you can borrow for education and you "
        "cannot borrow for retirement.** A household that underfunds "
        "retirement to fully fund college converts a solvable problem into an "
        "unsolvable one, and the children inherit the consequence anyway."
    ]
    if retirement_on_track is True:
        at = (f" — the target is reached around age "
              f"{retirement_age_at_target:.0f}" if retirement_age_at_target else "")
        out.append(
            f"Retirement is on track at the central assumptions{at}, so "
            "education funding is not competing with it. That is the "
            "condition under which the rest of this report is worth acting on."
        )
    elif retirement_on_track is False:
        out.append(
            "⚠️ **Retirement is not on track at the central assumptions.** "
            "Any gap below should be closed by borrowing, by the student "
            "working, by a cheaper institution, or by accepting a partial "
            "contribution — not by diverting retirement savings."
        )
    else:
        out.append(
            "Retirement status was not computed, so the ordering rule cannot "
            "be applied to this household. Run `retirement-readiness` first; "
            "it decides whether any of this is affordable."
        )
    return out


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
