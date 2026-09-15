"""Disability insurance: the coverage people under-buy and never re-read.

Disability is more likely than death during working years and is insured worse.
The policy is also harder to read: two policies with the same headline monthly
benefit can differ by a factor of two in what they actually pay, depending on
the occupation definition, the benefit period, and who paid the premium.

The last one is not a detail. **Who paid decides whether the benefit is taxed**,
so a stated benefit is not comparable across policies until it is converted to
a common after-tax basis. This module does that conversion before comparing
anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Assumed marginal rate applied to a taxable benefit to reach a spendable
#: figure. Crude, and labelled as such wherever it is used.
ASSUMED_MARGINAL_RATE = 0.30

#: Carriers will not insure 100% of income — the industry ceiling, and the
#: reason a "gap" above this is usually not purchasable.
MAX_INSURABLE_SHARE_OF_GROSS = 0.70

#: Age most policies and most plans treat as the end of working life.
ASSUMED_RETIREMENT_AGE = 67

DEFINITION_RANK = {
    "own_occupation": 3,
    "modified_own_occupation": 2,
    "any_occupation": 1,
}
DEFINITION_NOTE = {
    "own_occupation": "Pays if you cannot perform **your own** occupation, "
                      "even if you work in another. The strongest form.",
    "modified_own_occupation": "Pays if you cannot perform your own "
                               "occupation **and are not working elsewhere**. "
                               "Middle tier — the benefit stops if you take "
                               "other work.",
    "any_occupation": "Pays only if you cannot perform **any** occupation you "
                      "are reasonably suited to. The weakest form, and much "
                      "harder to claim than people assume.",
}


@dataclass
class PolicyAnalysis:
    id: str
    label: str
    monthly_benefit: float
    monthly_benefit_after_tax: float
    taxable: bool
    employer_provided: bool
    elimination_days: int | None
    benefit_period_years: object
    definition: str | None
    riders: list[str]
    findings: list[str] = field(default_factory=list)


@dataclass
class DisabilityAssessment:
    monthly_need: float
    monthly_covered_after_tax: float
    monthly_gap: float
    max_insurable_monthly: float
    policies: list[PolicyAnalysis] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    deadlines: list[object] = field(default_factory=list)

    @property
    def covered(self) -> bool:
        return self.monthly_gap <= 0


def after_tax_benefit(monthly: float, *, taxable: bool,
                      rate: float = ASSUMED_MARGINAL_RATE) -> float:
    return monthly * (1 - rate) if taxable else monthly


def analyse_policy(p: dict) -> PolicyAnalysis:
    employer = bool(p.get("employer_provided"))
    paid_with = p.get("premium_paid_with")
    # An employer-paid premium produces a taxable benefit; an individual
    # policy funded with after-tax dollars produces a tax-free one.
    taxable = employer or paid_with == "pre_tax"
    monthly = float(p.get("monthly_benefit") or 0)

    a = PolicyAnalysis(
        id=p.get("id") or "?",
        label=p.get("label") or p.get("id") or "policy",
        monthly_benefit=monthly,
        monthly_benefit_after_tax=after_tax_benefit(monthly, taxable=taxable),
        taxable=taxable,
        employer_provided=employer,
        elimination_days=p.get("elimination_days"),
        benefit_period_years=p.get("benefit_period_years"),
        definition=p.get("definition"),
        riders=list(p.get("riders") or []),
    )

    if taxable:
        a.findings.append(
            f"**Benefit is taxable** (premium paid pre-tax or by an employer), "
            f"so {_money(monthly)}/mo is worth about "
            f"{_money(a.monthly_benefit_after_tax)}/mo spendable at an assumed "
            f"{ASSUMED_MARGINAL_RATE:.0%} marginal rate. *Estimate.*"
        )
    else:
        a.findings.append(
            "**Benefit is tax-free** — premium paid with after-tax dollars. "
            "Worth its full face value, and worth more than a taxable policy "
            "of the same headline amount."
        )

    if a.definition in DEFINITION_NOTE:
        a.findings.append(f"*{a.definition}* — {DEFINITION_NOTE[a.definition]}")
    elif a.definition:
        a.findings.append(
            f"Occupation definition `{a.definition}` not recognised. Read it "
            "off the policy; it changes what the cover is worth more than the "
            "benefit amount does."
        )
    else:
        a.findings.append(
            "**Occupation definition not stated.** This is the single most "
            "important term in a disability policy. Find it."
        )

    if employer:
        a.findings.append(
            "Group cover, so it ends with the job and generally cannot be "
            "taken with you. It also usually caps at a percentage of base "
            "salary, excluding bonus and equity — which for variable "
            "compensation can be most of the income."
        )
    return a


def assess(
    policies: list[dict],
    *,
    insured_id: str,
    insured_age: int | None,
    annual_spending: float,
    gross_income: float,
    liquid_assets: float,
    reference_date=None,
) -> DisabilityAssessment:
    from . import facts as F  # local import keeps the dependency one-way

    rows = [p for p in policies if p.get("insured") == insured_id]
    analyses = [analyse_policy(p) for p in rows]

    monthly_need = annual_spending / 12.0
    covered = sum(a.monthly_benefit_after_tax for a in analyses)
    max_insurable = gross_income * MAX_INSURABLE_SHARE_OF_GROSS / 12.0

    out = DisabilityAssessment(
        monthly_need=monthly_need,
        monthly_covered_after_tax=covered,
        monthly_gap=max(0.0, monthly_need - covered),
        max_insurable_monthly=max_insurable,
        policies=analyses,
    )

    if out.monthly_gap > 0 and covered >= max_insurable:
        out.notes.append(
            f"The gap of {_money(out.monthly_gap)}/mo is real but may not be "
            f"purchasable: cover already reaches the industry ceiling of about "
            f"{MAX_INSURABLE_SHARE_OF_GROSS:.0%} of gross "
            f"({_money(max_insurable)}/mo). Closing it means reducing required "
            "spending, not buying more."
        )

    # ── elimination period against the buffer that has to fund it ───────
    for a in analyses:
        if a.elimination_days:
            needed = monthly_need * (a.elimination_days / 30.0)
            if needed > liquid_assets:
                a.findings.append(
                    f"**The {a.elimination_days}-day elimination period needs "
                    f"about {_money(needed)} of liquid assets to bridge, and "
                    f"only {_money(liquid_assets)} is available.** A benefit "
                    "that starts after money runs out arrives too late."
                )
            else:
                months = a.elimination_days / 30.0
                a.findings.append(
                    f"{a.elimination_days}-day elimination period needs about "
                    f"{_money(needed)} to bridge ({months:.1f} months of "
                    f"spending); {_money(liquid_assets)} liquid covers it. A "
                    "longer elimination period is the cheapest way to cut this "
                    "premium if the buffer can carry it."
                )

    # ── benefit period against working life ─────────────────────────────
    if insured_age:
        for a in analyses:
            bp = a.benefit_period_years
            if isinstance(bp, (int, float)):
                ends_at = insured_age + int(bp)
                if ends_at < ASSUMED_RETIREMENT_AGE:
                    a.findings.append(
                        f"**Benefit period ends at about age {ends_at}, "
                        f"leaving {ASSUMED_RETIREMENT_AGE - ends_at} years to "
                        f"{ASSUMED_RETIREMENT_AGE} unfunded.** A disability "
                        "starting today pays out and then stops while the "
                        "career is still, on paper, unfinished — and those are "
                        "years with no earnings and no further retirement "
                        "contributions."
                    )
                else:
                    a.findings.append(
                        f"Benefit period runs to about age {ends_at}, covering "
                        "working life."
                    )

    # ── rider deadlines: the findings that expire ───────────────────────
    for p, a in zip(rows, analyses):
        if "future_increase" in a.riders:
            d = F.deadline(
                f"{a.label} — Future Increase option",
                p.get("future_increase_deadline"),
                reference_date,
            )
            out.deadlines.append(d)
            if d.on is None:
                a.findings.append(
                    "**A Future Increase rider is attached but no deadline is "
                    "recorded.** These windows close, usually somewhere in the "
                    "early fifties. Find the date — the rider lets you raise "
                    "cover later *without further medical underwriting*, which "
                    "is exactly what stops being available once health changes."
                )
            elif d.passed:
                a.findings.append(
                    f"**The Future Increase window closed on "
                    f"{d.on.isoformat()}.** Any increase now requires fresh "
                    "underwriting."
                )
            else:
                a.findings.append(
                    f"⏰ **Future Increase option expires {d.on.isoformat()} — "
                    f"{d.days_remaining} days.** It permits raising cover "
                    "*without medical underwriting*. If income has grown since "
                    "the policy was written, exercise it before the window "
                    "closes; insurability is the thing being bought, and it is "
                    "not purchasable later at any price."
                )
        if "cola" not in a.riders:
            a.findings.append(
                "No cost-of-living rider. A level benefit over a long claim "
                "loses real value steadily — a claim at 45 running to 67 is "
                "22 years of erosion."
            )
    return out


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
