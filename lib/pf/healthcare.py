"""Health cover between retirement and Medicare, Medicare timing, and long-term care.

## The one idea

**Modified AGI is a single lever that three different skills want to pull in two
opposite directions, and nothing in this repository was watching it.**

`roth-conversion-window` (shipped) tells a household to *raise* taxable income in
the years between retiring and RMDs, to use brackets that would otherwise go
empty. Premium tax credits taper against MAGI, so `aca-subsidy-optimization`
tells the same household to *suppress* MAGI. IRMAA looks back two years, so MAGI
at 63 sets a Medicare premium at 65 — a third pull on the same lever.

For a household retiring before 65 these are **the same calendar years**. Review
finding A6. This module therefore does not just compute subsidies; it imports
`retirement.conversion_window`, intersects it with the gap years and the IRMAA
lookback, and reports the overlap as a named conflict. Two skills giving opposite
instructions silently is the defect; surfacing it is the deliverable.

The resolution is not "pick one". It is that the window **partitions** into
segments with different binding constraints, and the segments have very different
effective marginal rates. `segment_conversion_window` computes that partition.

## What this module refuses

**Every year-specific figure.** Federal poverty levels, the applicable-percentage
schedule, benchmark silver premiums, IRMAA tier thresholds, the Part B standard
premium and the Part D national base premium are all annual, all published, and
all absent from this repository on purpose — review finding A3 records
`limits.py` as an unverified tax-code mirror that must not grow before it is
verified.

They come from `assumptions.*` in the facts file or the report states the
structure and refuses the figure. A confident subsidy number computed from a
stale poverty level is worse than no number: it will be believed, and the taper
makes the error compound.

**Whether the 400% cliff is in force.** The 400% line is statutory — IRC
§36B(c)(1)(A). Whether it has been suspended for a given plan year is a policy
question that has flipped twice, so `assumptions.aca_cliff_applies` is asked for,
never assumed. Getting it wrong inverts the advice at the most consequential
point on the curve.

**State Medicaid expansion status.** Asked for, not tabulated. A fifty-state
table is exactly the growth A8 warns about, and the household knows its own state.

## Basis

All dollar figures are **nominal, current-year**, not real. The ACA and Medicare
figures are annual parameters that are re-set each year rather than indexed
quantities that can be projected, so discounting them would imply a model that
does not exist. This is deliberately the opposite convention from
`retirement.py`, which is real throughout — when the two are combined in a
report, say which is which.

The long-term-care section is the exception and says so inline: care costs are
projected forward, so they are stated in **today's money against today's assets**,
which is the real basis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import retirement as _ret

#: The absorb/transfer boundary is defined in `auto.py` and imported, not
#: restated. "Insure what you cannot absorb" is one rule in this repository and
#: it must have one pair of numbers. The *denominator* differs — see
#: `assess_ltc`, which measures against investable assets rather than liquid —
#: and that difference is stated in the report rather than hidden in a constant.
from .auto import ABSORB_SEVERE, ABSORB_TRIVIAL  # noqa: F401

# ── Medicare structure ──────────────────────────────────────────────────────

#: Medicare eligibility on age. Statutory and stable; unlike the dollar figures
#: below it has not moved, which is why it is here and they are not.
MEDICARE_AGE = 65

#: IRMAA is determined from the tax return two years prior. This is the whole
#: reason a conversion at 63 raises a premium at 65.
IRMAA_LOOKBACK_YEARS = 2

#: Initial Enrolment Period: three months before the month of the 65th
#: birthday, that month, and three months after.
IEP_MONTHS = 7
IEP_MONTHS_BEFORE = 3
IEP_MONTHS_AFTER = 3

#: Special Enrolment Period after group coverage from *current* employment ends.
#: Part B and Part A. COBRA and retiree coverage do not start this clock.
SEP_PART_B_MONTHS = 8

#: Part D SEP runs on a 63-day creditable-coverage rule rather than a month
#: count, which is why it is expressed in days.
CREDITABLE_COVERAGE_GAP_DAYS = 63

#: Part B late-enrolment penalty: 10% for each full 12-month period the person
#: could have had Part B and did not. Permanent, for as long as they hold Part B.
PART_B_PENALTY_PER_12M = 0.10

#: Part D late-enrolment penalty: 1% of the national base beneficiary premium
#: per full uncovered month. Also permanent. The base premium is an annual
#: figure and is not held here.
PART_D_PENALTY_PER_MONTH = 0.01

#: Quarters of Medicare-covered employment for premium-free Part A.
PART_A_QUARTERS_REQUIRED = 40

#: The employee count that decides whether a group plan pays primary. At 20 or
#: more the group plan is primary and Part B can safely be delayed. Below 20,
#: **Medicare is primary** — the group plan may pay as though Medicare had paid
#: its share, leaving the household exposed for a gap it does not know it has.
SEP_EMPLOYER_MIN_EMPLOYEES = 20

#: HSA contributions must stop this many months before Part A enrolment,
#: because Part A can be granted retroactively for up to this period. Any
#: contribution inside it is an excess contribution. Interacts with `hsa-review`.
HSA_STOP_MONTHS_BEFORE_PART_A = 6

# ── ACA structure ───────────────────────────────────────────────────────────

#: IRC §36B(c)(1)(A) sets the upper bound for premium tax credit eligibility at
#: 400% of the federal poverty level. Statutory and structural — but whether it
#: is *in force* for a plan year has been suspended and restored, so
#: `SubsidyParams.cliff_applies` is an input, never a default.
CLIFF_FPL_PCT = 4.00

#: Lower bound of premium tax credit eligibility. Below this, in a state that
#: did not expand Medicaid, there is a coverage gap: too poor for a subsidy, too
#: rich for Medicaid. **MAGI can be too low**, which is the finding most
#: "suppress your income" advice omits.
PTC_FLOOR_FPL_PCT = 1.00

#: ACA Medicaid expansion level: 133% of FPL plus a 5-point income disregard.
#: In an expansion state, MAGI below this routes to Medicaid rather than to a
#: subsidised marketplace plan — a different programme with different providers
#: and, in some states, estate recovery.
MEDICAID_EXPANSION_FPL_PCT = 1.38

MEDICARE_SOURCE = (
    "42 U.S.C. §1395c and §1395o (entitlement at 65); §1395p and 42 C.F.R. "
    "§407.14 (the seven-month Initial Enrolment Period); §1395p(i) (the "
    "eight-month Special Enrolment Period); §1395r(b) (the Part B late "
    "enrolment penalty); §1395w-113(b) (the Part D penalty and the 63-day "
    "creditable-coverage rule); §1395r(i) (the IRMAA two-year lookback); "
    "§1395i-2 and 42 C.F.R. §406.10 (40 quarters for premium-free Part A); "
    "§1395y(b)(1)(A) (the 20-employee Medicare-secondary-payer test); "
    "IRS Publication 969 and §223(b)(7) (the six-month retroactive Part A "
    "window that ends HSA eligibility)"
)
MEDICARE_VERIFIED = (
    "unverified — check against medicare.gov, cms.gov and irs.gov Pub. 969")

ACA_SOURCE = (
    "IRC §36B(c)(1)(A) (premium tax credit eligibility between 100% and 400% "
    "of the federal poverty level); 42 U.S.C. §1396a(a)(10)(A)(i)(VIII) and "
    "§1396a(e)(14)(I) (the 133% Medicaid expansion level plus the 5-point "
    "income disregard)"
)
ACA_VERIFIED = (
    "unverified — check against healthcare.gov and irs.gov; note in "
    "particular that whether the 400% cliff is *in force* for a plan year is "
    "an input (`SubsidyParams.cliff_applies`), never a default here")

#: How close to the cliff counts as dangerous. A household within this fraction
#: of the threshold should treat its MAGI estimate as a control variable, not a
#: forecast: a December capital gain distribution can cross it.
CLIFF_PROXIMITY_WARN = 0.10

#: Step used when reporting the marginal cost of additional MAGI. Small enough
#: to sit inside one band of the applicable-percentage schedule, large enough
#: that the answer is not rounding noise.
MAGI_STEP = 1_000.0

# ── long-term care structure ────────────────────────────────────────────────

#: Planning duration for a significant care need. Roughly the central case: most
#: care episodes are shorter, and the mean is dragged up by a long tail.
LTC_PLANNING_YEARS = 3

#: The tail the decision is actually about. A three-year episode is a large bill;
#: a five-plus-year episode is what removes a surviving spouse's retirement.
LTC_TAIL_YEARS = 5

#: Care need is not independent between spouses in the way a naive model assumes
#: — but the case that breaks a plan is **one** spouse in care while the other
#: still needs the portfolio to fund a normal retirement. That is the scenario
#: `assess_ltc` tests, not the joint case.
LTC_SIMULTANEOUS = False


# ── ACA: parameters ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SubsidyParams:
    """Everything year-specific about the premium tax credit.

    Nothing in this dataclass has a default that is a number. Absent means
    absent, and the assessment reports structure without a figure.
    """

    year: int | None = None
    #: Federal poverty level for a one-person household, and the increment per
    #: additional person. Published annually by HHS.
    fpl_base: float | None = None
    fpl_per_additional: float | None = None
    fpl_as_of: str | None = None
    #: Annual premium of the second-lowest-cost silver plan for this household
    #: on its own exchange. The subsidy is computed against this plan whether or
    #: not the household buys it.
    benchmark_premium_annual: float | None = None
    #: Whether the 400% FPL eligibility ceiling applies for this plan year.
    cliff_applies: bool | None = None
    #: Piecewise-linear applicable-percentage schedule as (fpl_pct, share of
    #: income the household is expected to contribute). Interpolated between
    #: points; flat outside the ends.
    applicable_pct_schedule: tuple[tuple[float, float], ...] | None = None
    #: Whether the state expanded Medicaid. Decides what happens below the floor.
    medicaid_expansion_state: bool | None = None
    source: str = ""

    @property
    def fpl_known(self) -> bool:
        return self.fpl_base is not None and self.fpl_per_additional is not None

    @property
    def computable(self) -> bool:
        return bool(
            self.fpl_known
            and self.benchmark_premium_annual is not None
            and self.applicable_pct_schedule
            and self.cliff_applies is not None
        )

    def missing(self) -> list[str]:
        out = []
        if self.fpl_base is None:
            out.append("assumptions.fpl_base")
        if self.fpl_per_additional is None:
            out.append("assumptions.fpl_per_additional_person")
        if self.benchmark_premium_annual is None:
            out.append("assumptions.aca_benchmark_premium_annual")
        if not self.applicable_pct_schedule:
            out.append("assumptions.aca_applicable_pct_schedule")
        if self.cliff_applies is None:
            out.append("assumptions.aca_cliff_applies")
        return out


def params_from_assumptions(a: dict | None) -> SubsidyParams:
    """Build `SubsidyParams` from an `assumptions` mapping.

    Lives here rather than in each runner because two skills need it and the
    conflict they report must be quantified identically in both. A household
    reading one report saying "16.9%" and another saying "not quantified" would
    reasonably conclude the tooling disagrees with itself — which is the exact
    class of defect this cluster exists to prevent.
    """
    a = a or {}
    sched = a.get("aca_applicable_pct_schedule")
    return SubsidyParams(
        year=a.get("fpl_year"),
        fpl_base=a.get("fpl_base"),
        fpl_per_additional=a.get("fpl_per_additional_person"),
        fpl_as_of=a.get("fpl_as_of"),
        benchmark_premium_annual=a.get("aca_benchmark_premium_annual"),
        cliff_applies=a.get("aca_cliff_applies"),
        applicable_pct_schedule=(
            tuple((float(x), float(y)) for x, y in sched) if sched else None),
        medicaid_expansion_state=a.get("medicaid_expansion_state"),
    )


def fpl_for(household_size: int, p: SubsidyParams) -> float | None:
    """Federal poverty level for a household of this size."""
    if not p.fpl_known or household_size < 1:
        return None
    return p.fpl_base + p.fpl_per_additional * (household_size - 1)


def fpl_pct(magi: float, fpl: float | None) -> float | None:
    if not fpl:
        return None
    return magi / fpl


def applicable_pct(pct_of_fpl: float,
                   schedule: tuple[tuple[float, float], ...] | None) -> float | None:
    """Expected contribution as a share of income, interpolated.

    The published schedule is a set of anchor points with linear interpolation
    between them. Outside the ends it is flat — stepping off the end of a table
    is exactly where a silently-extrapolated number would be wrong.
    """
    if not schedule:
        return None
    pts = sorted(schedule)
    if pct_of_fpl <= pts[0][0]:
        return pts[0][1]
    if pct_of_fpl >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= pct_of_fpl <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (pct_of_fpl - x0) / (x1 - x0)
    return pts[-1][1]  # pragma: no cover - unreachable given the bounds above


@dataclass(frozen=True)
class SubsidyPoint:
    """The subsidy at one MAGI, and why it is what it is."""

    magi: float
    fpl: float | None
    pct_of_fpl: float | None
    applicable_pct: float | None
    expected_contribution: float | None
    benchmark: float | None
    subsidy: float | None
    eligible: bool | None
    reason: str = ""


def subsidy_at(magi: float, household_size: int, p: SubsidyParams) -> SubsidyPoint:
    """Annual premium tax credit at a given MAGI.

    `subsidy = benchmark premium - (applicable percentage x MAGI)`, floored at
    zero. The credit is computed against the benchmark plan regardless of which
    plan is bought, which is why a cheaper plan does not reduce the credit.
    """
    fpl = fpl_for(household_size, p)
    pct = fpl_pct(magi, fpl)

    if not p.computable or pct is None:
        return SubsidyPoint(magi, fpl, pct, None, None,
                            p.benchmark_premium_annual, None, None,
                            "Cannot be determined — see the missing inputs.")

    if pct < PTC_FLOOR_FPL_PCT:
        if p.medicaid_expansion_state:
            reason = (f"Below {PTC_FLOOR_FPL_PCT:.0%} of FPL in an expansion "
                      "state — this routes to Medicaid, not to a subsidised "
                      "marketplace plan.")
        elif p.medicaid_expansion_state is False:
            reason = (f"Below {PTC_FLOOR_FPL_PCT:.0%} of FPL in a "
                      "non-expansion state — **the coverage gap**: no premium "
                      "tax credit and no Medicaid.")
        else:
            reason = (f"Below {PTC_FLOOR_FPL_PCT:.0%} of FPL. What happens "
                      "next depends on whether the state expanded Medicaid, "
                      "which is not recorded.")
        return SubsidyPoint(magi, fpl, pct, None, None,
                            p.benchmark_premium_annual, None, False, reason)

    if p.cliff_applies and pct > CLIFF_FPL_PCT:
        return SubsidyPoint(
            magi, fpl, pct, None, None, p.benchmark_premium_annual, 0.0, False,
            f"Above {CLIFF_FPL_PCT:.0%} of FPL with the cliff in force — "
            "the entire credit is lost, not tapered.")

    ap = applicable_pct(pct, p.applicable_pct_schedule)
    expected = ap * magi
    sub = max(0.0, p.benchmark_premium_annual - expected)
    return SubsidyPoint(magi, fpl, pct, ap, expected,
                        p.benchmark_premium_annual, sub, True,
                        "Eligible." if sub > 0 else
                        "Eligible, but the expected contribution already "
                        "exceeds the benchmark premium, so the credit is zero.")


@dataclass(frozen=True)
class Taper:
    """What the next dollar of MAGI costs in lost subsidy."""

    step: float
    subsidy_before: float | None
    subsidy_after: float | None
    lost_per_step: float | None
    #: Subsidy lost per dollar of extra MAGI. An implicit marginal tax rate,
    #: stacking on top of whatever income-tax bracket applies.
    marginal_rate: float | None
    crosses_cliff: bool
    headroom_to_cliff: float | None


def taper_at(magi: float, household_size: int, p: SubsidyParams,
             step: float = MAGI_STEP) -> Taper:
    """The marginal cost of additional MAGI — the number the conflict turns on.

    This is what makes the conflict with `roth-conversion-window` quantifiable:
    the taper is a marginal tax rate that does not appear in any bracket table,
    and it is paid on exactly the income a conversion deliberately creates.
    """
    fpl = fpl_for(household_size, p)
    before = subsidy_at(magi, household_size, p)
    after = subsidy_at(magi + step, household_size, p)

    headroom = None
    crosses = False
    if fpl and p.cliff_applies:
        cliff_magi = CLIFF_FPL_PCT * fpl
        headroom = cliff_magi - magi
        crosses = magi <= cliff_magi < magi + step

    if before.subsidy is None or after.subsidy is None:
        return Taper(step, before.subsidy, after.subsidy, None, None,
                     crosses, headroom)

    lost = before.subsidy - after.subsidy
    return Taper(step, before.subsidy, after.subsidy, lost,
                 lost / step if step else None, crosses, headroom)


# ── the gap years ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Gap:
    """Years between retiring and Medicare, funded on the individual market."""

    retirement_age: int | None
    medicare_age: int
    years: int | None

    @property
    def exists(self) -> bool:
        return bool(self.years and self.years > 0)


def gap_years(retirement_age: int | None,
              medicare_age: int = MEDICARE_AGE) -> Gap:
    if retirement_age is None:
        return Gap(None, medicare_age, None)
    return Gap(retirement_age, medicare_age,
               max(0, medicare_age - retirement_age))


# ── A6: the conflict ────────────────────────────────────────────────────────

CONFLICT_SUBSIDY_VS_CONVERSION = "ACA subsidy taper vs Roth conversion window"
CONFLICT_IRMAA_VS_CONVERSION = "IRMAA two-year lookback vs Roth conversion window"

#: Keys into `conflicts.REGISTRY`, which is the canonical catalogue of which
#: contradictions exist. This module does not duplicate that catalogue — it
#: *quantifies* two of its entries, computing the actual overlapping ages and,
#: where subsidy parameters are supplied, the marginal-rate comparison.
#:
#: The division of labour: the registry answers "does this conflict apply to
#: this household", cheaply and for every pair. This answers "and how much
#: does it cost", expensively and for two. A test asserts these keys exist,
#: so the two cannot drift apart.
REGISTRY_KEY_SUBSIDY = "conversions-vs-aca"
REGISTRY_KEY_IRMAA = "conversions-vs-irmaa"

#: Labels for what binds in a given segment of the conversion window.
BINDS_SUBSIDY = "ACA subsidy"
BINDS_IRMAA = "IRMAA"


@dataclass(frozen=True)
class Segment:
    """A run of years inside the conversion window with one set of constraints.

    The output that actually resolves A6. "There is a conflict" is not
    actionable; "these three years are clean, these five are not, and here is
    what each costs" is.
    """

    start_age: int
    end_age: int  # exclusive
    constraints: tuple[str, ...]

    @property
    def years(self) -> int:
        return self.end_age - self.start_age

    @property
    def clean(self) -> bool:
        return not self.constraints


@dataclass
class Conflict:
    name: str
    #: Skills that disagree. Named so the report can point at them.
    skills: tuple[str, ...]
    overlap_years: int
    overlap_ages: tuple[int, int] | None
    detail: str
    quantified: list[str] = field(default_factory=list)
    #: Key into `conflicts.REGISTRY`. Set so the quantified finding and the
    #: catalogue entry are provably the same conflict rather than two
    #: independently authored descriptions of one problem.
    registry_key: str = ""

    @property
    def live(self) -> bool:
        return self.overlap_years > 0


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int] | None:
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    return (lo, hi) if hi > lo else None


def segment_conversion_window(
    *, window: _ret.ConversionWindow, retirement_age: int | None,
    medicare_age: int = MEDICARE_AGE,
) -> list[Segment]:
    """Partition the conversion window by which MAGI constraint binds.

    Three intervals overlay the window: the ACA gap
    `[retirement, medicare)`, the IRMAA lookback `[medicare - 2, close)`, and
    the window itself. Their boundaries cut the window into segments, and the
    segments have materially different effective marginal rates.
    """
    if not window.exists or window.opens_age is None or window.closes_age is None:
        return []

    w = (window.opens_age, window.closes_age)
    aca = (retirement_age, medicare_age) if retirement_age is not None else None
    irmaa = (medicare_age - IRMAA_LOOKBACK_YEARS, window.closes_age)

    cuts = {w[0], w[1]}
    for iv in (aca, irmaa):
        if iv:
            for x in iv:
                if w[0] < x < w[1]:
                    cuts.add(x)
    edges = sorted(cuts)

    out: list[Segment] = []
    for lo, hi in zip(edges, edges[1:]):
        binds = []
        if aca and _overlap((lo, hi), aca):
            binds.append(BINDS_SUBSIDY)
        if _overlap((lo, hi), irmaa):
            binds.append(BINDS_IRMAA)
        out.append(Segment(lo, hi, tuple(binds)))
    return out


def magi_conflicts(
    *,
    retirement_age: int | None,
    window: _ret.ConversionWindow,
    medicare_age: int = MEDICARE_AGE,
    taper: Taper | None = None,
    subsidy: SubsidyPoint | None = None,
) -> list[Conflict]:
    """Detect where `roth-conversion-window` and this cluster disagree.

    Review finding A6. `roth-conversion-window` is shipped and tells the
    household to raise MAGI in the window. This tells it to suppress MAGI in the
    gap years and again in the IRMAA lookback. Where those intervals intersect,
    two skills in this repository give opposite instructions, and until now
    nothing noticed.

    Quantified as far as the inputs allow and no further: with subsidy
    parameters the trade-off becomes a marginal-rate comparison; without them
    the conflict is still reported, because its *existence* does not depend on
    the figures.
    """
    out: list[Conflict] = []
    if not window.exists or window.opens_age is None or window.closes_age is None:
        return out
    w = (window.opens_age, window.closes_age)

    # ── conflict 1: the subsidy taper ───────────────────────────────────────
    aca_iv = (retirement_age, medicare_age) if retirement_age is not None else None
    ov = _overlap(w, aca_iv) if aca_iv else None
    years = (ov[1] - ov[0]) if ov else 0
    c1 = Conflict(
        registry_key=REGISTRY_KEY_SUBSIDY,
        name=CONFLICT_SUBSIDY_VS_CONVERSION,
        skills=("roth-conversion-window", "aca-subsidy-optimization"),
        overlap_years=years,
        overlap_ages=ov,
        detail=(
            f"`roth-conversion-window` reports a window at ages {w[0]}–{w[1]} "
            f"and tells you to **raise** taxable income inside it. Premium tax "
            f"credits taper against MAGI, so for ages {ov[0]}–{ov[1]} this "
            f"skill tells you to **suppress** exactly the same number. "
            f"**{years} years are governed by both instructions.**"
            if ov else
            f"The conversion window (ages {w[0]}–{w[1]}) does not overlap the "
            f"pre-Medicare gap, so the subsidy taper does not constrain "
            f"conversions."
        ),
    )
    if ov and taper is not None and taper.marginal_rate is not None:
        c1.quantified.append(
            f"**The taper is an unlisted marginal tax rate of "
            f"{taper.marginal_rate:.1%}.** Every extra dollar of MAGI in a gap "
            f"year loses that much premium credit, *on top of* the income tax "
            f"on the conversion. A conversion filling a 12% bracket is "
            f"therefore being done at roughly "
            f"{0.12 + taper.marginal_rate:.0%}, and one filling a 22% bracket "
            f"at roughly {0.22 + taper.marginal_rate:.0%}. Neither figure "
            f"appears in any bracket table.")
    if ov and subsidy is not None and subsidy.subsidy:
        c1.quantified.append(
            f"At the recorded MAGI the credit is worth "
            f"**${subsidy.subsidy:,.0f}/yr**, so **${subsidy.subsidy * years:,.0f}** "
            f"is on the table across the {years} overlapping years. That is the "
            f"sum a conversion programme is spending, and it is not usually "
            f"counted as part of the conversion tax.")
    if ov and taper is not None and taper.headroom_to_cliff is not None:
        if taper.headroom_to_cliff > 0:
            c1.quantified.append(
                f"**The cliff is the hard ceiling: ${taper.headroom_to_cliff:,.0f} "
                f"of additional MAGI in a gap year.** Convert one dollar past it "
                f"and the entire remaining credit is lost at once. This is the "
                f"single number to plan the conversion against — not a bracket "
                f"top.")
        else:
            c1.quantified.append(
                f"MAGI is already **${-taper.headroom_to_cliff:,.0f} above** the "
                f"{CLIFF_FPL_PCT:.0%} FPL cliff, so there is no credit left to "
                f"lose. The conflict is dormant at this income — and it "
                f"reverses: the question becomes whether MAGI can be brought "
                f"*below* the cliff, which points the other way from "
                f"conversions.")
    if ov and not c1.quantified:
        c1.quantified.append(
            "**Not quantified** — the subsidy parameters are not in the facts "
            "file, so the size of the trade-off cannot be computed. The "
            "conflict is real regardless; only its magnitude is unknown.")
    out.append(c1)

    # ── conflict 2: the IRMAA lookback ──────────────────────────────────────
    irmaa_iv = (medicare_age - IRMAA_LOOKBACK_YEARS, w[1])
    ov2 = _overlap(w, irmaa_iv)
    years2 = (ov2[1] - ov2[0]) if ov2 else 0
    c2 = Conflict(
        registry_key=REGISTRY_KEY_IRMAA,
        name=CONFLICT_IRMAA_VS_CONVERSION,
        skills=("roth-conversion-window", "medicare-enrollment-timing"),
        overlap_years=years2,
        overlap_ages=ov2,
        detail=(
            f"IRMAA is set from the return filed **{IRMAA_LOOKBACK_YEARS} years "
            f"earlier**, so MAGI from age "
            f"{medicare_age - IRMAA_LOOKBACK_YEARS} onward prices Medicare "
            f"premiums from {medicare_age} onward. Conversions at ages "
            f"{ov2[0]}–{ov2[1]} raise premiums two years later — "
            f"**{years2} years of the window are affected.**"
            if ov2 else
            "The conversion window closes before the IRMAA lookback begins, so "
            "conversions do not reach Medicare premiums."
        ),
    )
    if ov2:
        c2.quantified.append(
            "**IRMAA is a step, not a slope.** One dollar over a threshold "
            "costs the whole surcharge for the year, on both Part B and Part D, "
            "per person. For a couple that doubles it. The thresholds are "
            "annual figures and are deliberately not held in this repository — "
            "supply `assumptions.irmaa_tiers` to have the distance to the next "
            "step computed.")
        c2.quantified.append(
            "It is also **appealable on a life-changing event**, and retirement "
            "is one of them (SSA-44). A premium priced off a final working year "
            "can often be reduced — a conversion is *not* a qualifying event, "
            "but the work stoppage in the same window is.")
    out.append(c2)
    return out


def resolution_notes(segments: list[Segment]) -> list[str]:
    """How to use the partition. Ordering, not a recommendation to convert."""
    out: list[str] = []
    if not segments:
        return out

    clean = [s for s in segments if s.clean]
    irmaa_only = [s for s in segments if s.constraints == (BINDS_IRMAA,)]
    subsidy_only = [s for s in segments if s.constraints == (BINDS_SUBSIDY,)]
    both = [s for s in segments if len(s.constraints) > 1]

    def _spans(ss):
        return ", ".join(f"{s.start_age}–{s.end_age}" for s in ss)

    if clean:
        out.append(
            f"**{sum(s.years for s in clean)} unconstrained year(s): ages "
            f"{_spans(clean)}.** Neither the subsidy nor IRMAA reaches these. "
            f"Convert here **first** — this is free window, and it is the "
            f"cheapest conversion capacity the household will ever have.")
    if irmaa_only:
        out.append(
            f"**{sum(s.years for s in irmaa_only)} year(s) constrained by "
            f"IRMAA only: ages {_spans(irmaa_only)}.** Convert here **next**. "
            f"An IRMAA step costs a defined surcharge for one year per person; "
            f"a subsidy cliff costs the whole credit. The IRMAA cost is "
            f"bounded and knowable, which makes these years cheaper than the "
            f"gap years even though they are not free.")
    if subsidy_only:
        out.append(
            f"**{sum(s.years for s in subsidy_only)} year(s) constrained by "
            f"the subsidy only: ages {_spans(subsidy_only)}.** These are "
            f"pre-Medicare years outside the IRMAA lookback, so a conversion "
            f"costs the taper but nothing later. Convert here **after** the "
            f"IRMAA-only years and only up to the cliff headroom — past the "
            f"cliff the marginal cost is not a rate, it is the whole credit.")
    if both:
        out.append(
            f"**{sum(s.years for s in both)} year(s) constrained by both: ages "
            f"{_spans(both)}.** Both the subsidy and the future Medicare "
            f"premium respond to MAGI here. Convert **last and least**, and "
            f"only up to the cliff headroom.")
    out.append(
        "**This ordering is not a recommendation to convert.** It says that "
        "*if* conversions happen, the sequence above is strictly cheaper than "
        "converting evenly across the window, which is what a bracket-filling "
        "rule read on its own would produce.")
    return out


# ── ACA assessment ──────────────────────────────────────────────────────────


@dataclass
class AcaAssessment:
    gap: Gap
    household_size: int
    params: SubsidyParams
    magi: float | None
    point: SubsidyPoint | None
    taper: Taper | None
    conflicts: list[Conflict] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    weakest_input: str = ""


def assess_aca(
    *,
    retirement_age: int | None,
    household_size: int,
    magi: float | None,
    params: SubsidyParams,
    window: _ret.ConversionWindow,
    medicare_age: int = MEDICARE_AGE,
) -> AcaAssessment:
    gap = gap_years(retirement_age, medicare_age)
    point = subsidy_at(magi, household_size, params) if magi is not None else None
    tap = taper_at(magi, household_size, params) if magi is not None else None

    a = AcaAssessment(
        gap=gap, household_size=household_size, params=params, magi=magi,
        point=point, taper=tap,
        conflicts=magi_conflicts(retirement_age=retirement_age, window=window,
                                 medicare_age=medicare_age, taper=tap,
                                 subsidy=point),
        segments=segment_conversion_window(
            window=window, retirement_age=retirement_age,
            medicare_age=medicare_age),
    )

    if retirement_age is None:
        a.findings.append(
            "**No planned retirement age recorded**, so the gap cannot be "
            "sized. This is the input the whole skill turns on.")
    elif not gap.exists:
        a.findings.append(
            f"**No gap.** Retirement at {retirement_age} is at or after "
            f"Medicare eligibility at {medicare_age}, so there are no years to "
            f"fund on the individual market. Go to `medicare-enrollment-timing` "
            f"instead.")
    else:
        a.findings.append(
            f"**{gap.years} year(s) to fund privately**, ages "
            f"{retirement_age} to {medicare_age}. Health cover is not a "
            f"line item in these years, it is a constraint on income — which "
            f"is a different kind of planning problem from the one a "
            f"retirement projection solves.")

    if not params.computable:
        a.findings.append(
            "**The subsidy figure is refused, not estimated.** Missing: "
            + ", ".join(f"`{m}`" for m in params.missing())
            + ". These are annual, published, and change every year; a figure "
            "computed from last year's poverty level would be believed and "
            "would be wrong, and the taper makes the error compound rather "
            "than cancel.")
    elif magi is None:
        a.findings.append(
            "**No expected gap-year MAGI recorded** "
            "(`assumptions.expected_magi_in_gap_years`). The parameters are "
            "present, so supplying it turns every figure in this report on. "
            "Unknown is not zero — a zero would produce a maximum subsidy and "
            "the most confident possible wrong answer.")
    else:
        assert point is not None
        if point.pct_of_fpl is not None:
            a.findings.append(
                f"MAGI of ${magi:,.0f} against a household-of-"
                f"{household_size} poverty level of ${point.fpl:,.0f} is "
                f"**{point.pct_of_fpl:.0%} of FPL**. That percentage, not the "
                f"dollar amount, is what the credit is computed from.")
        if point.eligible is False:
            a.findings.append(f"⚠️ {point.reason}")
        if point.subsidy:
            a.findings.append(
                f"Estimated credit **${point.subsidy:,.0f}/yr** against a "
                f"benchmark premium of ${point.benchmark:,.0f}, leaving an "
                f"expected contribution of ${point.expected_contribution:,.0f}.")
        if point.pct_of_fpl is not None and point.pct_of_fpl < MEDICAID_EXPANSION_FPL_PCT:
            a.findings.append(
                f"⚠️ **MAGI can be too low.** At {point.pct_of_fpl:.0%} of FPL "
                f"this household is at or below the "
                f"{MEDICAID_EXPANSION_FPL_PCT:.0%} expansion level. Suppressing "
                f"MAGI further does not buy a larger credit — it changes "
                f"programme, to Medicaid in an expansion state or to the "
                f"coverage gap in one that did not expand. Advice to 'keep "
                f"income low' has a floor, and it is rarely mentioned.")
        if tap is not None and tap.headroom_to_cliff is not None \
                and 0 < tap.headroom_to_cliff <= CLIFF_PROXIMITY_WARN * magi:
            a.findings.append(
                f"⚠️ **Within {CLIFF_PROXIMITY_WARN:.0%} of the cliff** — "
                f"${tap.headroom_to_cliff:,.0f} of headroom. At this distance "
                f"MAGI is a control variable, not a forecast: a December "
                f"capital gain distribution, a rebalance, or an unplanned "
                f"withdrawal can cross it and cost the whole credit.")

    a.findings.append(
        "**The credit is reconciled on the tax return.** What is taken monthly "
        "in advance is an estimate against a MAGI that is not final until "
        "December. Estimate high rather than low: overstating income means a "
        "refund, understating it means repaying the excess, and above 400% of "
        "FPL with the cliff in force the repayment is the entire year's "
        "advance credit.")
    a.findings.append(
        "**MAGI here is not AGI and not the MAGI used elsewhere.** For the "
        "premium tax credit it is AGI plus tax-exempt interest, plus untaxed "
        "Social Security, plus excluded foreign earned income. Each of the "
        "definitions in the tax code differs slightly and they are routinely "
        "conflated — the tax-exempt interest add-back in particular surprises "
        "households holding municipal bonds precisely to keep income down.")

    a.weakest_input = (
        "`assumptions.expected_magi_in_gap_years` — a forecast of a number "
        "several years out, made by the household, that the entire result is "
        "linear in. Everything else here is a published parameter; this one is "
        "a guess, and near the cliff a 10% error in it changes the answer "
        "completely."
    )
    return a


# ── Medicare ────────────────────────────────────────────────────────────────


def part_b_penalty_rate(full_years_late: int) -> float:
    """Permanent Part B surcharge as a fraction of the standard premium."""
    return max(0, full_years_late) * PART_B_PENALTY_PER_12M


def part_d_penalty_rate(uncovered_months: int) -> float:
    """Permanent Part D surcharge as a fraction of the national base premium."""
    return max(0, uncovered_months) * PART_D_PENALTY_PER_MONTH


@dataclass(frozen=True)
class IrmaaTier:
    magi_threshold: float
    part_b_monthly: float
    part_d_monthly: float


@dataclass(frozen=True)
class IrmaaPosition:
    magi: float
    tier_index: int | None
    surcharge_monthly_per_person: float | None
    next_threshold: float | None
    headroom: float | None
    step_cost_annual_per_person: float | None


def irmaa_position(magi: float, tiers: list[IrmaaTier]) -> IrmaaPosition:
    """Where a MAGI sits against supplied IRMAA tiers, and the next step's cost.

    Tiers are an input. They are annual figures published by CMS and holding
    them here would grow exactly the unverified table review finding A3 says to
    stop growing.
    """
    if not tiers:
        return IrmaaPosition(magi, None, None, None, None, None)
    ordered = sorted(tiers, key=lambda t: t.magi_threshold)

    idx = None
    for i, t in enumerate(ordered):
        if magi >= t.magi_threshold:
            idx = i
    current = ordered[idx] if idx is not None else None
    surcharge = (current.part_b_monthly + current.part_d_monthly) if current else 0.0

    nxt = None
    for t in ordered:
        if t.magi_threshold > magi:
            nxt = t
            break

    step = None
    if nxt is not None:
        step = ((nxt.part_b_monthly + nxt.part_d_monthly) - surcharge) * 12

    return IrmaaPosition(
        magi, idx, surcharge,
        nxt.magi_threshold if nxt else None,
        (nxt.magi_threshold - magi) if nxt else None,
        step)


@dataclass
class MedicareAssessment:
    current_age: int | None
    medicare_age: int
    years_away: int | None
    part_a_premium_free: bool | None
    sep_available: bool | None
    irmaa: IrmaaPosition | None
    irmaa_magi_year_age: int | None
    findings: list[str] = field(default_factory=list)
    weakest_input: str = ""


def assess_medicare(
    *,
    current_age: int | None,
    working_past_65: bool | None,
    employer_employees: int | None,
    coverage_is_current_employment: bool | None,
    part_a_quarters: int | None,
    magi: float | None,
    irmaa_tiers: list[IrmaaTier] | None,
    contributing_to_hsa: bool | None,
    medicare_age: int = MEDICARE_AGE,
) -> MedicareAssessment:
    a = MedicareAssessment(
        current_age=current_age,
        medicare_age=medicare_age,
        years_away=(medicare_age - current_age) if current_age is not None else None,
        part_a_premium_free=(None if part_a_quarters is None
                             else part_a_quarters >= PART_A_QUARTERS_REQUIRED),
        sep_available=None,
        irmaa=(irmaa_position(magi, irmaa_tiers)
               if magi is not None and irmaa_tiers else None),
        irmaa_magi_year_age=(medicare_age - IRMAA_LOOKBACK_YEARS),
    )

    # ── the window ──────────────────────────────────────────────────────────
    a.findings.append(
        f"**The Initial Enrolment Period is {IEP_MONTHS} months**: the "
        f"{IEP_MONTHS_BEFORE} months before the month of the "
        f"{medicare_age}th birthday, that month, and the {IEP_MONTHS_AFTER} "
        f"after. Enrolling in the first three is what avoids a gap in cover; "
        f"enrolling later in the window delays the start date.")

    if working_past_65 is None:
        a.findings.append(
            "**Not recorded whether employment continues past "
            f"{medicare_age}** (`healthcare.working_past_65`). It decides "
            "whether the enrolment window is the Initial Enrolment Period or a "
            "Special Enrolment Period, which is the whole question.")
    elif working_past_65:
        if employer_employees is None:
            a.findings.append(
                "⚠️ **Employer size is not recorded and it is the load-bearing "
                "fact** (`healthcare.employer_employees`). At "
                f"{SEP_EMPLOYER_MIN_EMPLOYEES}+ employees the group plan pays "
                "primary and Part B can be delayed safely. Below that, "
                "**Medicare is primary** — the group plan can pay as though "
                "Medicare had already paid its share, so not enrolling leaves "
                "an uninsured gap the household does not know it has, and "
                "usually discovers at a claim.")
            a.sep_available = None
        elif employer_employees >= SEP_EMPLOYER_MIN_EMPLOYEES:
            a.sep_available = True
            a.findings.append(
                f"**{employer_employees} employees — the group plan is "
                f"primary.** Part B can be delayed without penalty while that "
                f"coverage continues, and an **{SEP_PART_B_MONTHS}-month Special "
                f"Enrolment Period** opens when the employment or the coverage "
                f"ends, whichever comes first.")
        else:
            a.sep_available = False
            a.findings.append(
                f"⚠️ **{employer_employees} employees — below the "
                f"{SEP_EMPLOYER_MIN_EMPLOYEES} threshold, so Medicare is "
                f"primary.** Enrol in Part B at {medicare_age} regardless of "
                f"the group plan. The plan is entitled to pay only what it "
                f"would owe as secondary, which means the Medicare share is "
                f"simply unpaid. This is the most expensive misunderstanding in "
                f"Medicare timing.")
    else:
        a.sep_available = False
        a.findings.append(
            f"**Not working past {medicare_age}, so the Initial Enrolment "
            f"Period is the window.** There is no Special Enrolment Period to "
            f"fall back on. Miss it and the next general opportunity is "
            f"January–March, with the late-enrolment penalty attached.")

    if coverage_is_current_employment is False:
        a.findings.append(
            "⚠️ **COBRA, retiree coverage and marketplace plans are not "
            "coverage from current employment.** None of them creates a Part B "
            "Special Enrolment Period, and none of them is creditable for Part "
            "B. A household that treats eighteen months of COBRA as a bridge "
            "past 65 accrues the permanent penalty for the whole of it. This is "
            "the single most common and most expensive error in this skill's "
            "subject matter.")

    # ── penalties ───────────────────────────────────────────────────────────
    a.findings.append(
        f"**The Part B penalty is {PART_B_PENALTY_PER_12M:.0%} of the standard "
        f"premium for every full 12 months of eligibility without enrolment, "
        f"and it is permanent** — two years late means "
        f"{part_b_penalty_rate(2):.0%} added for life, not for two years. The "
        f"standard premium itself is an annual figure and is not held here; "
        f"supply `assumptions.part_b_standard_premium_monthly` for a dollar "
        f"amount.")
    a.findings.append(
        f"**The Part D penalty is {PART_D_PENALTY_PER_MONTH:.0%} of the "
        f"national base beneficiary premium per uncovered month, also "
        f"permanent**, and it applies even to someone who takes no "
        f"prescriptions — the penalty is for the gap, not for the claims. "
        f"Creditable drug coverage must not lapse for more than "
        f"{CREDITABLE_COVERAGE_GAP_DAYS} days. Ask the employer plan in "
        f"writing whether it is creditable; the notice is a legal requirement "
        f"and it is routinely filed unread.")

    if a.part_a_premium_free is True:
        a.findings.append(
            f"**Part A is premium-free** — {part_a_quarters} quarters recorded "
            f"against the {PART_A_QUARTERS_REQUIRED} required.")
    elif a.part_a_premium_free is False:
        a.findings.append(
            f"⚠️ **Only {part_a_quarters} of the "
            f"{PART_A_QUARTERS_REQUIRED} quarters needed for premium-free Part "
            f"A.** Part A is then purchasable but not free, and a spouse's "
            f"record may qualify the household instead. Worth resolving early: "
            f"the shortfall is fixable with additional covered employment, and "
            f"only before {medicare_age}.")
    else:
        a.findings.append(
            f"Quarters of covered employment not recorded "
            f"(`healthcare.part_a_quarters`), so whether Part A is premium-free "
            f"cannot be determined. {PART_A_QUARTERS_REQUIRED} quarters is the "
            f"threshold; the figure is on the Social Security statement.")

    # ── IRMAA ───────────────────────────────────────────────────────────────
    a.findings.append(
        f"**IRMAA looks back {IRMAA_LOOKBACK_YEARS} years.** The premium at "
        f"{medicare_age} is priced from the return for the year the household "
        f"turns {medicare_age - IRMAA_LOOKBACK_YEARS} — which is usually a "
        f"final working year or a conversion year, and is therefore usually "
        f"the worst year to be measured on. See "
        f"`aca-subsidy-optimization` for the overlap with the conversion "
        f"window; the two skills are describing one decision.")
    if a.irmaa and a.irmaa.tier_index is not None:
        a.findings.append(
            f"At MAGI ${magi:,.0f} the surcharge is "
            f"**${a.irmaa.surcharge_monthly_per_person:,.2f}/month per "
            f"person** across Parts B and D. For a couple both enrolled, "
            f"double it.")
    if a.irmaa and a.irmaa.headroom is not None:
        a.findings.append(
            f"**${a.irmaa.headroom:,.0f} of headroom to the next tier**, which "
            f"costs a further "
            f"${a.irmaa.step_cost_annual_per_person:,.0f}/yr per person if "
            f"crossed. It is a step, not a slope — one dollar over pays the "
            f"whole step.")
    elif magi is not None and not irmaa_tiers:
        a.findings.append(
            "IRMAA tiers not supplied (`assumptions.irmaa_tiers`), so the "
            "distance to the next step is not computed. The thresholds are "
            "published annually by CMS and are deliberately not stored in this "
            "repository.")
    a.findings.append(
        "**IRMAA is appealable after a life-changing event**, and work "
        "stoppage is one — file SSA-44 rather than paying a surcharge priced "
        "off a final working year. A Roth conversion is *not* a qualifying "
        "event, which is precisely why conversion years need planning and "
        "retirement years often do not.")

    # ── HSA interaction ─────────────────────────────────────────────────────
    if contributing_to_hsa:
        a.findings.append(
            f"⚠️ **HSA contributions must stop "
            f"{HSA_STOP_MONTHS_BEFORE_PART_A} months before Part A begins.** "
            f"Part A can be granted retroactively up to that far back, and any "
            f"contribution inside the retroactive period is an excess "
            f"contribution with a penalty attached. Claiming Social Security "
            f"also enrols Part A automatically, which catches people who never "
            f"chose to enrol at all. Cross-check `hsa-review` — the two skills "
            f"share this constraint and only this one names the deadline.")

    a.weakest_input = (
        "`healthcare.employer_employees` — a single integer that flips the "
        "Part B answer from 'safe to delay' to 'enrol now or be uninsured for "
        "the Medicare share'. It is also the fact a household is least likely "
        "to have checked, and counts can change year to year."
    )
    return a


# ── long-term care ──────────────────────────────────────────────────────────

SELF_INSURE = "self_insure"
TRANSFER = "transfer"
PARTIAL = "partial"


@dataclass
class LtcAssessment:
    annual_cost: float | None
    cost_as_of: str | None
    planning_cost: float | None
    tail_cost: float | None
    investable: float
    share_planning: float | None
    share_tail: float | None
    verdict: str  # self_insure | partial | transfer | unknown
    #: Portfolio remaining after a tail-length episode, and the spending it
    #: still supports at the library's withdrawal rate.
    residual_assets: float | None
    residual_supportable_spending: float | None
    survivor_shortfall: float | None
    #: The tail case costs at least the whole portfolio. Not a large shortfall
    #: but a total one, and the survivor arithmetic under it is academic.
    exhausted: bool = False
    findings: list[str] = field(default_factory=list)
    weakest_input: str = ""


def assess_ltc(
    *,
    annual_cost: float | None,
    cost_as_of: str | None,
    investable_assets: float,
    survivor_annual_spending: float | None,
    has_policy: bool,
    policy_type: str | None,
    withdrawal_rate: float = _ret.DEFAULT_WITHDRAWAL_RATE,
) -> LtcAssessment:
    """Apply the repository's insurance rule to the largest uninsured tail risk.

    The rule is `auto.py`'s and is imported, not restated: **insure what you
    cannot absorb.** The denominator differs, and the difference matters. An
    auto total loss is measured against liquid assets because it is settled in
    weeks. A care episode is a multi-year drain on the same portfolio that funds
    the rest of retirement, so it is measured against investable assets — and
    the test that decides the answer is not the share, it is what the *survivor*
    is left with.

    Real basis: today's cost against today's assets. Care cost inflation has run
    above general inflation, so this understates the exposure and says so.
    """
    planning = annual_cost * LTC_PLANNING_YEARS if annual_cost else None
    tail = annual_cost * LTC_TAIL_YEARS if annual_cost else None
    share_p = (planning / investable_assets) if (planning and investable_assets) else None
    share_t = (tail / investable_assets) if (tail and investable_assets) else None

    # Floored at zero. A negative portfolio is not a portfolio, and rendering
    # one invites reading the shortfall as merely large rather than total.
    exhausted = tail is not None and tail >= investable_assets
    residual = max(0.0, investable_assets - tail) if tail is not None else None
    supportable = (residual * withdrawal_rate) if residual is not None else None
    shortfall = None
    if supportable is not None and survivor_annual_spending is not None:
        shortfall = max(0.0, survivor_annual_spending - supportable)

    if share_t is None:
        verdict = "unknown"
    elif share_t >= ABSORB_SEVERE or (shortfall or 0) > 0:
        verdict = TRANSFER
    elif share_t <= ABSORB_TRIVIAL:
        verdict = SELF_INSURE
    else:
        verdict = PARTIAL

    a = LtcAssessment(
        annual_cost=annual_cost, cost_as_of=cost_as_of, exhausted=exhausted,
        planning_cost=planning, tail_cost=tail,
        investable=investable_assets, share_planning=share_p,
        share_tail=share_t, verdict=verdict, residual_assets=residual,
        residual_supportable_spending=supportable,
        survivor_shortfall=shortfall,
    )

    if annual_cost is None:
        a.findings.append(
            "**No care cost recorded** (`healthcare.ltc.annual_cost_today`), "
            "so nothing here is sized. The figure is regional and moves faster "
            "than general inflation, which is why it is asked for rather than "
            "held in the repository — a national average applied to a "
            "high-cost metro understates the exposure by a wide margin, in the "
            "direction of doing nothing.")
        a.weakest_input = "`healthcare.ltc.annual_cost_today` — absent."
        return a

    a.findings.append(
        f"At ${annual_cost:,.0f}/yr, a {LTC_PLANNING_YEARS}-year episode costs "
        f"**${planning:,.0f}** and a {LTC_TAIL_YEARS}-year episode "
        f"**${tail:,.0f}**, in today's money. The decision is about the tail, "
        f"not the central case: most episodes are shorter than the mean and the "
        f"mean is dragged up by the long ones. Insurance is for the long ones.")

    if share_t is not None:
        a.findings.append(
            f"The {LTC_TAIL_YEARS}-year figure is **{share_t:.0%} of "
            f"${investable_assets:,.0f} investable assets** "
            f"(the {LTC_PLANNING_YEARS}-year figure is {share_p:.0%}). The "
            f"absorb bands are the same ones `auto-insurance-review` uses — "
            f"under {ABSORB_TRIVIAL:.0%} self-insure, over {ABSORB_SEVERE:.0%} "
            f"transfer — but measured against investable rather than liquid "
            f"assets, because a care episode draws on the retirement portfolio "
            f"over years rather than settling in weeks.")

    if exhausted:
        a.findings.append(
            f"⚠️ **The {LTC_TAIL_YEARS}-year case costs more than the entire "
            f"investable portfolio** (${tail:,.0f} against "
            f"${investable_assets:,.0f}). There is no residual to run a "
            f"survivor test against — the portfolio is gone before the episode "
            f"ends, and what follows is a Medicaid spend-down rather than a "
            f"funding plan. At this ratio the question is not whether to "
            f"insure but whether cover can be obtained and afforded.")

    if shortfall is not None and shortfall > 0:
        a.findings.append(
            f"⚠️ **This is the test that decides it, and it fails.** After a "
            f"{LTC_TAIL_YEARS}-year episode the portfolio is "
            f"${residual:,.0f}, supporting ${supportable:,.0f}/yr at "
            f"{withdrawal_rate:.1%} — against a survivor needing "
            f"${survivor_annual_spending:,.0f}. A **${shortfall:,.0f}/yr "
            f"shortfall for the rest of the survivor's life.** The risk being "
            f"insured is not the care bill. It is impoverishing the spouse who "
            f"did not need care.")
    elif shortfall == 0:
        a.findings.append(
            f"After a {LTC_TAIL_YEARS}-year episode the portfolio is "
            f"${residual:,.0f}, still supporting ${supportable:,.0f}/yr at "
            f"{withdrawal_rate:.1%} against a survivor need of "
            f"${survivor_annual_spending:,.0f}. **The survivor test passes**, "
            f"which is the substantive argument for self-insuring — stronger "
            f"than the percentage-of-assets test above it.")
    else:
        a.findings.append(
            "**Survivor spending not recorded**, so the test that actually "
            "decides this is not run. The percentage-of-assets band is a "
            "screen; the survivor test is the answer. Supply "
            "`healthcare.ltc.survivor_annual_spending`.")

    if verdict == SELF_INSURE:
        a.findings.append(
            f"**Verdict: self-insure.** At {share_t:.0%} of investable assets "
            f"the tail case does not change the plan. Earmark rather than "
            f"insure — and revisit if assets fall or the cost assumption rises, "
            f"because this verdict is a ratio and both sides of it move.")
    elif verdict == TRANSFER:
        a.findings.append(
            "**Verdict: transfer at least the tail.** The exposure is past the "
            "line this repository uses for every other insurance decision. "
            "Note what transferring means here: cover the *duration* tail, not "
            "the first dollar. A policy with a long elimination period and a "
            "long benefit period insures the part that cannot be absorbed and "
            "is far cheaper than one that pays from day one — which is the "
            "opposite of how these are usually sold.")
    elif verdict == PARTIAL:
        a.findings.append(
            f"**Verdict: partial.** At {share_t:.0%} the tail is material but "
            f"not ruinous. A policy covering part of the daily benefit, with a "
            f"long elimination period funded from assets, is the proportionate "
            f"answer. Full coverage here is buying back a risk already largely "
            f"absorbed.")

    if has_policy:
        a.findings.append(
            f"A policy of type `{policy_type or 'unrecorded'}` is in force. "
            f"Check three things on it: whether the benefit is "
            f"**inflation-adjusted** (a fixed daily benefit written years ago "
            f"buys a fraction of what it did), the **elimination period** "
            f"against liquid assets, and the **benefit period** — the tail is "
            f"what is being insured, so a three-year benefit period leaves the "
            f"exact scenario that motivated the purchase uncovered.")
    else:
        a.findings.append("No long-term care policy recorded.")

    # ── the honest part about traditional policies ──────────────────────────
    a.findings.append(
        "**Traditional long-term care insurance has a bad history and it is "
        "not a footnote.** Carriers priced early blocks assuming policyholders "
        "would lapse at normal rates and interest rates would stay high. "
        "Neither happened. In-force blocks have since carried repeated "
        "rate increases, approved by regulators, in some cases cumulatively "
        "large enough to force holders to reduce benefits or drop cover — "
        "after paying premiums for decades, at the age when the policy was "
        "about to matter. **The premium on a traditional policy is not "
        "guaranteed, and the increase arrives when it is hardest to absorb.** "
        "Anyone buying one should price a scenario in which it goes up "
        "substantially and ask whether they would still pay it.")
    a.findings.append(
        "**Hybrid life-LTC policies answer that specific objection and "
        "introduce different ones.** The premium is usually guaranteed and an "
        "unused benefit pays as a death benefit, so the money is not lost — "
        "which is the real reason people buy them. Against that: far less care "
        "benefit per premium dollar, a large sum tied up in a low-return "
        "contract, and a surrender value that makes the illustration look "
        "better than the internal return actually is. **Do not compare them on "
        "premium.** Compare maximum benefit per dollar and ask what the "
        "committed capital would otherwise have earned — the same arithmetic "
        "`life-insurance-review` applies to cash-value policies.")
    a.findings.append(
        "**Self-insuring is a real answer, not a failure to decide** — but "
        "only if it is funded and named. An unlabelled 'the portfolio will "
        "cover it' is how the survivor ends up short. If the verdict above is "
        "self-insure, the follow-through is an earmarked share of the "
        "portfolio and a written statement of who arranges care.")
    a.findings.append(
        "**Medicaid is the actual backstop for most households, and it is "
        "means-tested.** It pays for custodial care only after a spend-down, "
        "with a lookback on transfers and state-specific community-spouse "
        "protections and estate recovery. Those rules are state law and are "
        "**not** modelled here — this skill will not tell you whether a "
        "transfer is safe, and anyone considering one needs an elder-law "
        "attorney in their own state.")
    a.findings.append(
        "**Medicare does not pay for long-term care.** It covers limited "
        "skilled nursing after a qualifying hospital stay, not custodial care, "
        "which is what the multi-year episode above consists of. This is the "
        "most widespread single misconception in the subject and it is the "
        "reason households arrive at 80 with no plan.")
    if cost_as_of:
        a.findings.append(
            f"Cost basis dated {cost_as_of}. **Care cost inflation has run "
            f"above general inflation**, so a figure in today's money "
            f"understates an episode thirty years out — this report is real, "
            f"today-money throughout, and does not project that excess.")

    a.weakest_input = (
        "`healthcare.ltc.annual_cost_today` — regional, self-reported, and the "
        "figure every dollar above is a multiple of. A national average in a "
        "high-cost metro understates it badly, and the error runs in the "
        "direction of doing nothing."
    )
    return a
