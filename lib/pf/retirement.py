"""Retirement adequacy, drawdown order, conversion windows, and claiming age.

## Wrap or reimplement — ROADMAP open question 1, answered here

**Reimplemented, deliberately simply.** Mature open-source tools already do
Monte Carlo, detailed Roth conversion optimisation and tax-aware withdrawal
sequencing far better than this ever will. Three reasons not to wrap one:

1. **Dependencies.** The whole premise is a small auditable library that runs
   with essentially nothing installed. A heavy modelling dependency undoes
   that, and it is the thing that makes these skills reviewable.
2. **A single number from a black box is worse than a transparent range.** A
   forty-year projection reported to the dollar invites a confidence nobody
   should have. What changes decisions here is the *framing* and the
   *sensitivity*, not the third significant figure.
3. **The decision content is not in the simulation.** Ordering withdrawals,
   spotting the conversion window, understanding survivor benefits — none of
   that needs Monte Carlo.

So: deterministic real-return projection, an explicit sensitivity table, and a
loud pointer to specialist tools for anything needing distributions. The one
thing this must never do is imply more precision than it has.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import limits as _limits

#: Withdrawal rates to report. The middle is the conventional figure; the band
#: is what honest uncertainty looks like. A 0.5pp difference moves the target
#: by roughly 15%, which is the point of showing all three.
WITHDRAWAL_RATES = (0.035, 0.040, 0.045)
DEFAULT_WITHDRAWAL_RATE = 0.040

#: Real (after-inflation) returns to project across. Everything in this module
#: is real — today's money throughout — because mixing a nominal return into
#: real spending is a documented defect class.
REAL_RETURN_SCENARIOS = (0.03, 0.05, 0.07)
DEFAULT_REAL_RETURN = 0.05

MAX_PROJECTION_YEARS = 60


@dataclass
class Readiness:
    target: float
    assets: float
    annual_savings: float
    real_return: float
    withdrawal_rate: float
    years_to_target: float | None
    age_at_target: float | None
    findings: list[str] = field(default_factory=list)

    @property
    def already_there(self) -> bool:
        return self.assets >= self.target


def target_for(annual_spending: float, withdrawal_rate: float) -> float:
    return annual_spending / withdrawal_rate


def project(assets: float, annual_savings: float, real_return: float,
            years: float) -> float:
    """Future value in **today's money**, contributions at year end."""
    if years <= 0:
        return assets
    growth = (1 + real_return) ** years
    if real_return == 0:
        return assets + annual_savings * years
    return assets * growth + annual_savings * (growth - 1) / real_return


def years_to(target: float, assets: float, annual_savings: float,
             real_return: float) -> float | None:
    """First whole year at which the projection reaches the target."""
    if assets >= target:
        return 0.0
    if annual_savings <= 0 and real_return <= 0:
        return None
    for y in range(1, MAX_PROJECTION_YEARS + 1):
        if project(assets, annual_savings, real_return, y) >= target:
            return float(y)
    return None


def assess_readiness(
    *,
    annual_spending: float,
    assets: float,
    annual_savings: float,
    current_age: int | None,
    withdrawal_rate: float = DEFAULT_WITHDRAWAL_RATE,
    real_return: float = DEFAULT_REAL_RETURN,
) -> Readiness:
    target = target_for(annual_spending, withdrawal_rate)
    n = years_to(target, assets, annual_savings, real_return)
    r = Readiness(
        target=target, assets=assets, annual_savings=annual_savings,
        real_return=real_return, withdrawal_rate=withdrawal_rate,
        years_to_target=n,
        age_at_target=(current_age + n) if (current_age is not None and n is not None) else None,
    )

    if n is None:
        r.findings.append(
            "**The target is not reached within "
            f"{MAX_PROJECTION_YEARS} years** at these assumptions. Either "
            "spending, savings, or the target itself needs to change — the "
            "projection is telling you the plan does not close, not that it "
            "closes late."
        )
    elif r.already_there:
        r.findings.append(
            "**Assets already exceed the target at this withdrawal rate.** "
            "The binding question stops being accumulation and becomes "
            "sequencing, taxes, and what the money is for."
        )

    r.findings.append(
        "Every figure here is **real** — today's money, discounted at a real "
        "return. A nominal projection produces a much larger and entirely "
        "meaningless number."
    )
    r.findings.append(
        "**This is a deterministic projection, not a simulation.** It assumes "
        "a constant real return, which no real sequence delivers. Its value is "
        "the sensitivity table, not the point estimate — and it says nothing "
        "about sequence-of-returns risk, which is the dominant danger in the "
        "first few years of drawdown. For distributions rather than a single "
        "path, use a dedicated Monte Carlo tool."
    )
    return r


def sensitivity(
    *, annual_spending: float, assets: float, annual_savings: float,
    current_age: int | None,
) -> list[dict]:
    """Years to target across the plausible parameter space.

    The honest output of this skill. A single number implies a precision that
    a forty-year projection cannot support; the spread across this grid is the
    actual answer.
    """
    rows = []
    for wr in WITHDRAWAL_RATES:
        target = target_for(annual_spending, wr)
        row = {"withdrawal_rate": wr, "target": target}
        for rr in REAL_RETURN_SCENARIOS:
            n = years_to(target, assets, annual_savings, rr)
            row[rr] = {
                "years": n,
                "age": (current_age + n) if (current_age is not None and n is not None) else None,
            }
        rows.append(row)
    return rows


# ── drawdown ────────────────────────────────────────────────────────────────

DEFAULT_SEQUENCE = [
    ("taxable", "Taxable brokerage",
     "Gains only are taxed, at long-term rates if held. Spending it first also "
     "removes the drag of taxable dividends and lets the sheltered accounts "
     "keep compounding untaxed."),
    ("tax_deferred", "Traditional 401(k) / IRA",
     "Fully taxable as ordinary income. Drawing it down before RMDs begin is "
     "what keeps the forced distributions from landing in a higher bracket."),
    ("roth", "Roth",
     "Tax-free and not subject to lifetime RMDs, so it should compound "
     "longest. It is also the best asset to leave to heirs."),
]


@dataclass
class Drawdown:
    sequence: list[tuple[str, str, str]]
    findings: list[str] = field(default_factory=list)


def drawdown_guidance(
    *, current_age: int | None, ages: _limits.RetirementAges,
    has_taxable: bool, has_tax_deferred: bool, has_roth: bool,
) -> Drawdown:
    d = Drawdown(sequence=list(DEFAULT_SEQUENCE))

    d.findings.append(
        "**The default order is a starting point, not the answer.** Strict "
        "sequencing leaves low brackets unused in early retirement and then "
        "forces high-bracket withdrawals later. The better version blends: "
        "spend from taxable while deliberately filling the low brackets with "
        "tax-deferred withdrawals or conversions."
    )

    if not has_roth and has_tax_deferred:
        d.findings.append(
            "**No Roth balance recorded.** Every dollar of retirement income "
            "will be taxable as ordinary income, with no lever to manage the "
            "bracket in a given year. That is what makes the conversion "
            "window valuable — see `roth-conversion-window`."
        )
    if not has_taxable and has_tax_deferred:
        d.findings.append(
            "**No taxable balance recorded.** Without it there is nothing to "
            "spend in early retirement that does not generate ordinary income, "
            "which removes most of the bracket-management flexibility and can "
            "also complicate pre-59½ access."
        )

    if ages.known:
        d.findings.append(
            f"Dates that shape the sequence: penalty-free IRA access at "
            f"**{ages.ira_penalty_free_age}**, Rule of 55 access to a "
            f"workplace plan on separation at **{ages.rule_of_55_age}**, "
            f"Social Security from **{ages.ss_earliest}**, RMDs beginning at "
            f"**{ages.rmd_age}**."
        )
        if current_age is not None and current_age < 59:
            d.findings.append(
                "**Retiring before 59½ needs an access plan, not just a "
                "number.** The Rule of 55 (separation in or after the year you "
                "turn 55, workplace plan only, not an IRA) and §72(t) "
                "substantially equal periodic payments are the usual routes. "
                "Rolling a 401(k) to an IRA *forfeits* the Rule of 55 — a "
                "common and irreversible mistake."
            )
    else:
        d.findings.append(
            "Birth year not recorded, so the statutory ages cannot be "
            "resolved. They differ by birth year and they moved recently."
        )

    d.findings.append(
        "**Asset location matters as much as the order.** Bonds and other "
        "income-producing assets belong in tax-deferred accounts; the highest "
        "expected-return assets belong in the Roth, because that is where "
        "growth is never taxed."
    )
    return d


# ── conversion window ───────────────────────────────────────────────────────


@dataclass
class ConversionWindow:
    opens_age: int | None
    closes_age: int | None
    years: int | None
    findings: list[str] = field(default_factory=list)

    @property
    def exists(self) -> bool:
        return bool(self.years and self.years > 0)


def conversion_window(
    *, retirement_age: int | None, ages: _limits.RetirementAges,
    claim_age: int | None = None,
) -> ConversionWindow:
    """The gap between employment income stopping and RMDs plus Social
    Security starting — the lowest-tax years most people will ever have."""
    if retirement_age is None or not ages.known:
        return ConversionWindow(
            None, None, None,
            ["Needs a planned retirement age and a birth year."])

    closes = min(ages.rmd_age, claim_age or ages.ss_latest)
    years = max(0, closes - retirement_age)
    w = ConversionWindow(retirement_age, closes, years)

    if years <= 0:
        w.findings.append(
            "**No window.** Retirement and the start of RMDs or benefits "
            "coincide, so there are no low-income years to convert into. "
            "Conversions are still possible but they compete with other "
            "income rather than filling empty brackets."
        )
        return w

    w.findings.append(
        f"**A {years}-year window, roughly ages {retirement_age} to {closes}.** "
        "Employment income has stopped; RMDs and benefits have not started. "
        "These are usually the lowest-taxable-income years of an entire adult "
        "life, and the brackets they leave empty are used or wasted — they do "
        "not carry forward."
    )
    w.findings.append(
        "**Convert to fill a bracket, not to a fixed amount.** Compute the "
        "headroom to the top of the target bracket each year and convert that "
        "much. A fixed annual figure either wastes headroom or spills into the "
        "next bracket."
    )
    w.findings.append(
        "**The knock-on effects are what catch people.** Conversions raise "
        "modified AGI, which can raise Medicare premiums two years later "
        "(IRMAA), reduce ACA premium subsidies if retiring before Medicare "
        "eligibility, and affect how Social Security is taxed. None of that "
        "makes conversions wrong; all of it belongs in the arithmetic."
    )
    w.findings.append(
        "**Pay the conversion tax from taxable funds, never from the "
        "converted amount.** Paying from the conversion shrinks the balance "
        "that was the whole point, and before 59½ the withheld portion is "
        "itself a penalised distribution."
    )
    return w


# ── social security ─────────────────────────────────────────────────────────

#: Delayed retirement credits per year past full retirement age.
DELAYED_CREDIT_PER_YEAR = 0.08

#: Reduction per year for the first 36 months of early claiming, then a
#: smaller rate beyond.
EARLY_REDUCTION_FIRST_3Y = 0.0667
EARLY_REDUCTION_BEYOND = 0.05


def benefit_multiplier(claim_age: float, full_age: float) -> float:
    """Benefit relative to the full-retirement-age amount."""
    if claim_age >= full_age:
        return 1 + DELAYED_CREDIT_PER_YEAR * min(claim_age - full_age, 70 - full_age)
    early = full_age - claim_age
    first = min(early, 3.0)
    beyond = max(0.0, early - 3.0)
    return 1 - (first * EARLY_REDUCTION_FIRST_3Y + beyond * EARLY_REDUCTION_BEYOND)


def claiming_table(ages: _limits.RetirementAges) -> list[dict]:
    if not ages.known or ages.ss_full is None:
        return []
    return [
        {"age": a, "multiplier": benefit_multiplier(a, ages.ss_full)}
        for a in range(ages.ss_earliest, ages.ss_latest + 1)
    ]


def claiming_guidance(*, ages: _limits.RetirementAges,
                      single_earner_household: bool) -> list[str]:
    out: list[str] = []
    if not ages.known or ages.ss_full is None:
        out.append(
            "Full retirement age cannot be resolved — it steps in months "
            "across the 1955–1959 birth years, and this table deliberately "
            "does not approximate it. Get the exact figure from your Social "
            "Security statement rather than accepting a rounded one."
        )
        return out

    out.append(
        f"Full retirement age **{ages.ss_full}**. Claiming at "
        f"{ages.ss_earliest} costs roughly "
        f"{1 - benefit_multiplier(ages.ss_earliest, ages.ss_full):.0%} "
        f"permanently; waiting to {ages.ss_latest} adds roughly "
        f"{benefit_multiplier(ages.ss_latest, ages.ss_full) - 1:.0%}."
    )
    out.append(
        "**The benefit is inflation-adjusted and lasts as long as you do**, "
        "which makes delaying less an investment decision than the purchase "
        "of longevity insurance. Framing it as a break-even calculation "
        "against an assumed death date misses what it is actually for: the "
        "risk being insured is living a long time, not dying early."
    )
    if single_earner_household:
        out.append(
            "**For a single-income couple this is mostly a survivor decision, "
            "and that is usually the whole argument.** When one spouse dies "
            "the household keeps the *larger* of the two benefits, not both. "
            "Delaying the higher earner's claim raises the floor under the "
            "survivor for the rest of their life — often decades — and a "
            "non-earning spouse has no benefit record of their own to fall "
            "back on. This consideration routinely outweighs the break-even "
            "arithmetic and is routinely left out of it."
        )
    out.append(
        "Claiming early while still working can also trigger the earnings "
        "test, withholding benefits above an annual threshold."
    )
    return out
