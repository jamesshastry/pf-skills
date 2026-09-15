"""US statutory contribution limits, by year.

Same pattern as `jurisdiction.py`, and for the same reason: a year that is not
in this table returns `UNKNOWN` and every skill that needs it says so. It never
silently applies last year's number.

⚠️ **These are the highest-risk constants in this repository.** Every other
threshold here is a judgement that can be argued about; these are facts that
change annually and are simply wrong once stale. A skill quoting a superseded
limit is worse than one that refuses to quote any, because it will be believed.

Verify before relying on them:
https://www.irs.gov/retirement-plans/plan-participant-employee/retirement-topics-401k-and-profit-sharing-plan-contribution-limits
https://www.irs.gov/publications/p969   (HSA)

Adding a year means adding every field and updating `verified_on`. A partially
filled year is worse than a missing one.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Limits:
    year: int
    known: bool
    #: §402(g) elective deferral limit — pre-tax and Roth combined.
    elective_deferral: int | None = None
    #: Age-50 catch-up. Sits *outside* the §415(c) total-additions limit.
    catch_up_50: int | None = None
    #: SECURE 2.0 enhanced catch-up, ages 60–63 only.
    catch_up_60_63: int | None = None
    #: §415(c) total annual additions — employee + employer + after-tax.
    #: Excludes catch-up.
    total_additions: int | None = None
    #: §401(a)(17) compensation cap for benefit calculations.
    compensation_limit: int | None = None
    ira_contribution: int | None = None
    ira_catch_up: int | None = None
    hsa_self_only: int | None = None
    hsa_family: int | None = None
    hsa_catch_up_55: int | None = None
    #: Where these came from, and when they were last checked by a human.
    source: str = ""
    verified_on: str = ""


CATCH_UP_AGE = 50
ENHANCED_CATCH_UP_AGES = (60, 63)
HSA_CATCH_UP_AGE = 55

_TABLE: dict[int, Limits] = {
    2025: Limits(
        year=2025,
        known=True,
        elective_deferral=23_500,
        catch_up_50=7_500,
        catch_up_60_63=11_250,
        total_additions=70_000,
        compensation_limit=350_000,
        ira_contribution=7_000,
        ira_catch_up=1_000,
        hsa_self_only=4_300,
        hsa_family=8_550,
        hsa_catch_up_55=1_000,
        source="IRS annual cost-of-living adjustments for 2025",
        verified_on="unverified — check against irs.gov before relying",
    ),
    2026: Limits(
        year=2026,
        known=True,
        elective_deferral=24_500,
        catch_up_50=8_000,
        catch_up_60_63=11_250,
        total_additions=72_000,
        compensation_limit=360_000,
        ira_contribution=7_500,
        ira_catch_up=1_100,
        hsa_self_only=4_400,
        hsa_family=8_750,
        hsa_catch_up_55=1_000,
        source="IRS annual cost-of-living adjustments for 2026",
        verified_on="unverified — check against irs.gov before relying",
    ),
}


@dataclass(frozen=True)
class RetirementAges:
    """Statutory ages, which depend on birth year rather than calendar year.

    In the same module as the contribution limits because they are the same
    kind of fact — set by legislation, changed by legislation, and wrong once
    stale. Registered with `provenance.py` alongside them.
    """

    known: bool
    birth_year: int | None = None
    #: First required minimum distribution. SECURE 2.0 moved this twice.
    rmd_age: int | None = None
    #: Earliest Social Security claim.
    ss_earliest: int | None = None
    #: Full retirement age.
    ss_full: int | None = None
    #: Latest useful claim — delayed credits stop accruing.
    ss_latest: int | None = None
    #: Penalty-free withdrawal from an IRA.
    ira_penalty_free_age: float | None = None
    #: Rule of 55: separation-year access to a workplace plan.
    rule_of_55_age: int | None = None
    source: str = ""
    verified_on: str = ""

RETIREMENT_AGES_SOURCE = (
    "SECURE Act 2.0 §107 (RMD age); Social Security Act full retirement age "
    "schedule; IRC §72(t)"
)
RETIREMENT_AGES_VERIFIED = "unverified — check against irs.gov and ssa.gov"


def retirement_ages(birth_year: int | None) -> RetirementAges:
    """Birth-year-banded statutory ages.

    Bands, not a formula: the full-retirement-age schedule steps in months for
    1955–1959 birth years and this deliberately does not model that precision.
    Anyone in that band is told to check the exact figure rather than given a
    rounded one that looks authoritative.
    """
    if birth_year is None:
        return RetirementAges(known=False)

    if birth_year >= 1960:
        rmd, fra = 75, 67
    elif birth_year >= 1951:
        rmd, fra = 73, None  # FRA steps in months across this band
    else:
        rmd, fra = 73, 66

    return RetirementAges(
        known=True,
        birth_year=birth_year,
        rmd_age=rmd,
        ss_earliest=62,
        ss_full=fra,
        ss_latest=70,
        ira_penalty_free_age=59.5,
        rule_of_55_age=55,
        source=RETIREMENT_AGES_SOURCE,
        verified_on=RETIREMENT_AGES_VERIFIED,
    )


def for_year(year: int | None) -> Limits:
    if year is None:
        return Limits(year=0, known=False)
    return _TABLE.get(year, Limits(year=year, known=False))


def years_available() -> list[int]:
    return sorted(_TABLE)


# ── derived space ───────────────────────────────────────────────────────────


def catch_up_for_age(age: int | None, lim: Limits) -> int:
    """Catch-up available at this age.

    The 60–63 enhanced catch-up *replaces* the age-50 amount for those years;
    it does not stack on top of it.
    """
    if age is None or not lim.known or age < CATCH_UP_AGE:
        return 0
    lo, hi = ENHANCED_CATCH_UP_AGES
    if lo <= age <= hi and lim.catch_up_60_63:
        return lim.catch_up_60_63
    return lim.catch_up_50 or 0


def employer_plan_space(age: int | None, lim: Limits) -> int | None:
    """Total that can land in the plan this year, from all sources.

    §415(c) plus catch-up. The catch-up sits outside §415(c), which is why the
    ceiling exceeds the headline number people quote.
    """
    if not lim.known or lim.total_additions is None:
        return None
    return lim.total_additions + catch_up_for_age(age, lim)


def ira_space(age: int | None, lim: Limits) -> int | None:
    if not lim.known or lim.ira_contribution is None:
        return None
    extra = (lim.ira_catch_up or 0) if (age or 0) >= CATCH_UP_AGE else 0
    return lim.ira_contribution + extra


def hsa_space(coverage: str | None, age: int | None, lim: Limits) -> int | None:
    if not lim.known or coverage in (None, "none"):
        return None
    base = lim.hsa_family if coverage == "family" else lim.hsa_self_only
    if base is None:
        return None
    extra = (lim.hsa_catch_up_55 or 0) if (age or 0) >= HSA_CATCH_UP_AGE else 0
    return base + extra
