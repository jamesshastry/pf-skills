"""Life insurance: in-force analysis, coverage gap, and the cash-value trap.

Two questions, in order. **Is there enough?** — against the capital need from
`survivor`, not a multiple of income. **Is what exists the right shape?** —
which is where permanent policies sold as investments come apart.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

PERMANENT_TYPES = ("whole", "universal", "variable_universal", "indexed_universal")

#: A permanent policy's internal return has to beat this to be defensible as
#: the investment it was sold as. Below it, the same premium in a boring index
#: fund with separate term cover wins on both return and death benefit.
DEFENSIBLE_REAL_RETURN = 0.03

#: Group cover is discounted, not ignored. It is real while employed, and the
#: correlation is the problem: the job ending and needing the cover are not
#: independent events, and a layoff removes both at once.
GROUP_RELIABILITY_FACTOR = 0.0


@dataclass
class PolicyAnalysis:
    id: str
    label: str
    kind: str
    death_benefit: float
    premium_annual: float
    portable: bool
    expires: _dt.date | None
    years_remaining: float | None
    cost_per_1k: float | None
    cash_value: float | None
    premiums_paid: float | None
    nominal_return: float | None
    findings: list[str] = field(default_factory=list)


@dataclass
class LifeAssessment:
    need: float
    in_force_portable: float
    in_force_group: float
    gap: float
    annual_premium: float
    policies: list[PolicyAnalysis] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def covered(self) -> bool:
        return self.gap <= 0


def annualised_return(cash_value: float, premiums_paid: float, years: float) -> float | None:
    """Crude but honest internal return on a cash-value policy.

    Treats total premiums as a lump sum paid at the midpoint of the holding
    period, which understates the loss on a policy funded evenly over time.
    That direction is deliberate: it is the generous reading, and these
    policies still fail it.
    """
    if years <= 0 or premiums_paid <= 0:
        return None
    effective_years = years / 2
    if effective_years <= 0:
        return None
    return (cash_value / premiums_paid) ** (1 / effective_years) - 1


def analyse_policy(p: dict, *, today: _dt.date) -> PolicyAnalysis:
    kind = p.get("type") or "term"
    db = float(p.get("death_benefit") or 0)
    premium = float(p.get("premium_annual") or 0)
    group = bool(p.get("employer_provided"))

    expires = p.get("term_expires")
    if isinstance(expires, _dt.datetime):
        expires = expires.date()
    elif isinstance(expires, str):
        try:
            expires = _dt.date.fromisoformat(expires)
        except ValueError:
            expires = None
    years_remaining = (expires - today).days / 365.25 if expires else None

    a = PolicyAnalysis(
        id=p.get("id") or "?",
        label=p.get("label") or p.get("id") or "policy",
        kind=kind,
        death_benefit=db,
        premium_annual=premium,
        portable=not group,
        expires=expires,
        years_remaining=years_remaining,
        cost_per_1k=(premium / (db / 1000)) if db else None,
        cash_value=p.get("cash_value"),
        premiums_paid=p.get("premiums_paid_to_date"),
        nominal_return=None,
    )

    if group:
        a.findings.append(
            "**Employer-provided, so treat it as zero for planning.** It is "
            "real while employed, but the job ending and needing the cover "
            "are correlated events — a layoff removes the income and the "
            "policy together. Check whether it is portable or convertible, "
            "and at what rate."
        )
    if kind in PERMANENT_TYPES:
        issued = p.get("issued")
        if isinstance(issued, str):
            try:
                issued = _dt.date.fromisoformat(issued)
            except ValueError:
                issued = None
        elif isinstance(issued, _dt.datetime):
            issued = issued.date()
        held = (today - issued).days / 365.25 if issued else None

        cv, paid = a.cash_value, a.premiums_paid
        if cv is not None and paid:
            if cv < paid:
                a.findings.append(
                    f"**Cash value is below premiums paid** — {_money(cv)} "
                    f"against {_money(paid)}. A nominal loss of "
                    f"{_money(paid - cv)} before inflation, on a product sold "
                    "as an investment."
                )
            if held:
                r = annualised_return(cv, paid, held)
                a.nominal_return = r
                if r is not None:
                    a.findings.append(
                        f"Implied return ≈ **{r:.1%}/yr nominal** over about "
                        f"{held:.0f} years, computed generously (premiums "
                        f"treated as a lump sum at the midpoint). The bar for "
                        f"keeping it as an investment is "
                        f"{DEFENSIBLE_REAL_RETURN:.0%} *real*."
                    )
        elif cv is not None:
            a.findings.append(
                "`premiums_paid_to_date` is missing, so the return cannot be "
                "computed — only the balance. The balance alone cannot answer "
                "whether this has been a good investment, which is the only "
                "question worth asking about a cash-value policy."
            )
        a.findings.append(
            "Surrendering has two traps worth naming before anyone acts. "
            "**Do not 1035 exchange into another permanent policy** — it "
            "feels like a fix and restarts the surrender-charge clock on the "
            "same cost architecture. And **replace the death benefit before "
            "cancelling**, never after: the new policy must be in force first, "
            "because insurability is not guaranteed."
        )
    elif expires:
        a.findings.append(
            f"Term expires {expires.isoformat()}"
            + (f" — about {years_remaining:.0f} years away." if years_remaining else ".")
        )
    return a


def assess(
    policies: list[dict],
    *,
    need: float,
    insured_id: str | None = None,
    dependents: list[dict] | None = None,
    today: _dt.date | None = None,
) -> LifeAssessment:
    today = today or _dt.date.today()
    rows = [p for p in policies
            if insured_id is None or p.get("insured") == insured_id]
    analyses = [analyse_policy(p, today=today) for p in rows]

    portable = sum(a.death_benefit for a in analyses if a.portable)
    group = sum(a.death_benefit for a in analyses if not a.portable)

    out = LifeAssessment(
        need=need,
        in_force_portable=portable,
        in_force_group=group,
        gap=max(0.0, need - portable),
        annual_premium=sum(a.premium_annual for a in analyses),
        policies=analyses,
    )

    if group:
        out.notes.append(
            f"{_money(group)} of employer cover is excluded from the gap. "
            "Including it would assume the job survives the event that "
            "creates the claim."
        )

    # ── coverage that expires before the need does ──────────────────────
    if dependents:
        youngest = min((d.get("age") or 0) for d in dependents)
        years_of_dependency = max(0, 22 - youngest)
        for a in analyses:
            if a.years_remaining is not None and a.years_remaining < years_of_dependency:
                out.notes.append(
                    f"**`{a.label}` expires before the dependents do.** About "
                    f"{a.years_remaining:.0f} years of cover against "
                    f"{years_of_dependency} years of dependency. Renewing at "
                    "that point means renewing at that age, in that health."
                )

    cheapest = min((a for a in analyses if a.cost_per_1k and a.portable),
                   key=lambda a: a.cost_per_1k, default=None)
    dearest = max((a for a in analyses if a.cost_per_1k and a.portable),
                  key=lambda a: a.cost_per_1k, default=None)
    if cheapest and dearest and dearest is not cheapest and cheapest.cost_per_1k:
        ratio = dearest.cost_per_1k / cheapest.cost_per_1k
        if ratio >= 3:
            out.notes.append(
                f"**`{dearest.label}` costs {ratio:.0f}× per dollar of death "
                f"benefit** what `{cheapest.label}` does "
                f"(${dearest.cost_per_1k:,.2f} vs "
                f"${cheapest.cost_per_1k:,.2f} per $1,000/yr). That spread "
                "is the whole argument, and it does not require an opinion "
                "about investment returns."
            )
    return out


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
