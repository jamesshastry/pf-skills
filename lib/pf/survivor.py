"""How much capital a household needs if an income stops.

This is the engine `life-insurance-review` and `disability-insurance-review`
both consume. It exists as its own module — and its own skill — because both
questions reduce to the same one, and computing it twice guarantees two
answers that eventually disagree.

Everything here is a **capital-needs** calculation: present-value the shortfall
between what the survivors need and what they will still receive, subtract what
they already have, and the remainder is what insurance is for. The alternative
approach in common use — a multiple of income — is a rule of thumb that ignores
the balance sheet entirely and is wrong in both directions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Share of current household spending the survivors still incur. One fewer
#: adult removes some consumption but almost none of the fixed costs: housing,
#: utilities, insurance and transport barely move. A benchmark, not a
#: measurement — override it with a real post-loss budget where one exists.
SURVIVOR_SPENDING_FACTOR = 0.75

#: Real (inflation-adjusted) discount rate for present-valuing the shortfall.
#: Deliberately conservative: the survivor's portfolio must fund spending
#: *and* survive sequence risk with no further contributions.
REAL_DISCOUNT_RATE = 0.03

#: Planning horizon for the surviving adult.
LIFE_EXPECTANCY_AGE = 90

#: Age at which a dependent stops being a financial dependent.
DEPENDENCY_END_AGE = 22

#: Funeral, estate administration, probate, and the professional fees that
#: arrive in the first year.
FINAL_EXPENSES = 20_000


@dataclass
class SurvivorNeed:
    insured_id: str
    survivor_age: int | None
    horizon_years: int
    annual_need: float
    surviving_income: float
    annual_shortfall: float
    capital_for_income: float
    final_expenses: float
    education_obligation: float
    assets_available: float
    total_need: float
    notes: list[str] = field(default_factory=list)

    @property
    def net_need(self) -> float:
        """Capital required beyond what the household already holds."""
        return max(0.0, self.total_need - self.assets_available)


def pv_annuity(annual: float, years: float, rate: float = REAL_DISCOUNT_RATE) -> float:
    """Present value of `annual` received for `years`, in today's money.

    Real rate against a real cash flow. Mixing a nominal rate with real
    spending is a documented defect class; keep both sides real.
    """
    if years <= 0:
        return 0.0
    if rate == 0:
        return annual * years
    return annual * (1 - (1 + rate) ** -years) / rate


def compute(
    *,
    insured_id: str,
    members: list[dict],
    annual_spending: float,
    assets_available: float,
    education_obligation: float | None = None,
    spending_factor: float = SURVIVOR_SPENDING_FACTOR,
    non_citizen_survivor: bool = False,
) -> SurvivorNeed:
    insured = next((m for m in members if m.get("id") == insured_id), {})
    others = [m for m in members if m.get("id") != insured_id]
    adults = [m for m in others if m.get("role") in ("primary", "spouse", "other")]
    dependents = [m for m in others if m.get("role") == "dependent"]

    survivor_age = next((a.get("age") for a in adults if a.get("age")), None)
    horizon = (
        LIFE_EXPECTANCY_AGE - survivor_age
        if survivor_age
        else LIFE_EXPECTANCY_AGE - (insured.get("age") or 40)
    )
    horizon = max(0, horizon)

    annual_need = annual_spending * spending_factor
    surviving_income = float(sum(a.get("income_annual") or 0 for a in adults))
    shortfall = max(0.0, annual_need - surviving_income)

    capital = pv_annuity(shortfall, horizon)
    education = float(education_obligation or 0)

    need = SurvivorNeed(
        insured_id=insured_id,
        survivor_age=survivor_age,
        horizon_years=horizon,
        annual_need=annual_need,
        surviving_income=surviving_income,
        annual_shortfall=shortfall,
        capital_for_income=capital,
        final_expenses=FINAL_EXPENSES,
        education_obligation=education,
        assets_available=assets_available,
        total_need=capital + FINAL_EXPENSES + education,
    )

    if non_citizen_survivor:
        need.notes.append(
            "**The surviving spouse is not a US citizen.** The unlimited "
            "marital deduction does not apply, so assets passing to them may "
            "be reduced by estate tax unless a QDOT is in place. This figure "
            "is a *need*, not a projection of what will arrive — see "
            "`citizenship-status-review` and `estate-document-review`."
        )

    if survivor_age is None:
        need.notes.append(
            "No surviving adult age on file, so the horizon is estimated from "
            "the insured's age. Add `age` to the surviving member."
        )
    if education_obligation is None and dependents:
        need.notes.append(
            f"{len(dependents)} dependent(s) on file but no education "
            "obligation supplied, so **none is included**. If college is "
            "intended, add `household.education_obligation` — it is often the "
            "largest single line in this calculation."
        )
    if surviving_income == 0 and adults:
        need.notes.append(
            "The surviving adult has no recorded income. A single-income "
            "household carries the whole need on insurance and assets, with "
            "no earnings to fall back on — and re-entering the workforce "
            "after a long absence rarely replaces a senior salary."
        )
    if dependents and survivor_age:
        youngest = min((d.get("age") or 0) for d in dependents)
        years_to_independence = max(0, DEPENDENCY_END_AGE - youngest)
        gap_start = survivor_age + years_to_independence
        if gap_start < 62:
            need.notes.append(
                f"**The gap decade.** Dependents become independent in about "
                f"{years_to_independence} year(s), when the survivor is "
                f"{gap_start}. Survivor benefits for a caregiver generally "
                f"stop then and do not resume until their own retirement — "
                f"roughly {62 - gap_start} years funded entirely from capital."
            )
    return need
