"""Tax-advantaged contribution space, and the employer-match true-up trap.

The match arithmetic here is the reason this module exists. **Two common match
formulas give opposite answers to the same question** — "does front-loading my
deferrals cost me match?" — and the difference is invisible unless you model
the formula shape rather than the headline rate.

    percent_of_pay_per_period   match accrues only in periods you contribute.
                                Hit the §402(g) limit in month three and every
                                later period earns nothing. Unless the plan
                                trues up, that match is gone.

    dollar_for_dollar_annual_cap  match accrues against a yearly cap. Front
                                loading reaches the cap *sooner*. Nothing is
                                forfeited.

Advice that ignores the distinction is wrong roughly half the time, with the
same confident tone either way.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import limits as _limits

PERCENT_OF_PAY = "percent_of_pay_per_period"
DOLLAR_FOR_DOLLAR = "dollar_for_dollar_annual_cap"
FORMULA_TYPES = (PERCENT_OF_PAY, DOLLAR_FOR_DOLLAR)


@dataclass
class MatchAnalysis:
    formula_type: str | None
    pay_periods: int | None
    periods_contributing: float | None
    match_earned: float | None
    match_available: float | None
    forfeited: float | None
    true_up: bool | None
    findings: list[str] = field(default_factory=list)

    @property
    def at_risk(self) -> bool:
        return bool(self.forfeited and self.forfeited > 0)


@dataclass
class SpaceLine:
    name: str
    used: float
    available: float | None
    note: str = ""

    @property
    def unused(self) -> float | None:
        if self.available is None:
            return None
        return max(0.0, self.available - self.used)


@dataclass
class SpaceAudit:
    year: int
    limits_known: bool
    lines: list[SpaceLine] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    @property
    def total_unused(self) -> float:
        return sum(l.unused or 0 for l in self.lines)


# ── the match ───────────────────────────────────────────────────────────────


def analyse_match(plan: dict, *, age: int | None, lim: _limits.Limits) -> MatchAnalysis:
    formula = plan.get("match_formula") or {}
    ftype = formula.get("type")
    periods = plan.get("pay_periods")
    rate_pct = plan.get("deferral_rate_pct")
    comp = plan.get("compensation")
    true_up = plan.get("true_up")

    a = MatchAnalysis(
        formula_type=ftype, pay_periods=periods, periods_contributing=None,
        match_earned=None, match_available=None, forfeited=None, true_up=true_up,
    )

    if ftype not in FORMULA_TYPES:
        a.findings.append(
            "**The match formula shape is not recorded, so this cannot be "
            "answered.** It is the whole question: a percent-of-pay match "
            "accrues only in periods you contribute, while a dollar-for-dollar "
            "match with an annual cap does not care about timing. The same "
            "front-loaded deferral schedule is either costly or free depending "
            "on which one your plan uses. Read the summary plan description, "
            "or ask HR: *'is the match calculated per pay period or on annual "
            "compensation, and does the plan true up?'*"
        )
        return a

    # Explicit None checks, not truthiness: a deferral rate of 0 is a real,
    # recorded answer ("contributing nothing") and must not be mistaken for a
    # missing field. Same for a zero compensation figure.
    missing = [name for name, v in (("pay_periods", periods),
                                    ("deferral_rate_pct", rate_pct),
                                    ("compensation", comp)) if v is None]
    if missing or not lim.known:
        a.findings.append(
            "Cannot model the timing. Missing: "
            + (", ".join(f"`{x}`" for x in missing) or "nothing")
            + ("" if lim.known else "; statutory limits for this year are "
                                    "not in the table.")
        )
        return a

    deferral_ceiling = (lim.elective_deferral or 0) + _limits.catch_up_for_age(age, lim)
    per_period_comp = comp / periods
    per_period_deferral = per_period_comp * (rate_pct / 100.0)

    if per_period_deferral <= 0:
        a.findings.append("Deferral rate is zero — no match is being earned at all.")
        return a

    periods_to_ceiling = math.ceil(deferral_ceiling / per_period_deferral)
    contributing = min(periods, periods_to_ceiling)
    a.periods_contributing = contributing

    if ftype == DOLLAR_FOR_DOLLAR:
        cap = formula.get("cap_annual") or 0
        rate = formula.get("rate", 1.0)
        total_deferred = min(deferral_ceiling, per_period_deferral * periods)
        a.match_available = float(cap)
        a.match_earned = min(cap, total_deferred * rate)
        a.forfeited = max(0.0, a.match_available - a.match_earned)
        if a.forfeited <= 0:
            a.findings.append(
                f"**Front-loading costs nothing here.** The match is "
                f"dollar-for-dollar against a {_money(cap)} annual cap, so "
                f"reaching the §402(g) limit in about {contributing} of "
                f"{periods} pay periods hits the cap *sooner* rather than "
                f"cutting it off. The full match is earned."
            )
            a.findings.append(
                "Worth confirming with HR that the cap really is annual rather "
                "than applied per pay period — that single detail flips the "
                "answer, and plan documents are often ambiguous about it."
            )
        else:
            a.findings.append(
                f"Total deferrals earn {_money(a.match_earned)} against a "
                f"{_money(cap)} cap — the cap is not reached."
            )
        return a

    # percent_of_pay_per_period
    cap_pct = formula.get("cap_pct")
    rate = formula.get("rate", 1.0)
    if cap_pct is None:
        a.findings.append(
            "Percent-of-pay formula recorded without `cap_pct` (the share of "
            "each period's pay that is matched). Cannot size the exposure."
        )
        return a

    matchable = min(per_period_deferral, per_period_comp * cap_pct)
    match_per_period = matchable * rate
    a.match_available = match_per_period * periods
    a.match_earned = match_per_period * contributing
    a.forfeited = max(0.0, a.match_available - a.match_earned)

    if a.forfeited <= 0:
        a.findings.append(
            "Deferrals continue through every pay period, so the full match is "
            "earned. Nothing at risk from timing."
        )
    elif true_up is True:
        a.findings.append(
            f"Deferrals stop after about {contributing} of {periods} pay "
            f"periods, which would forfeit {_money(a.forfeited)} — **but the "
            f"plan trues up**, so it is recovered after year end. No action, "
            f"beyond checking the true-up actually lands."
        )
        a.forfeited = 0.0
    else:
        state = ("**the plan does not true up**" if true_up is False
                 else "**and whether the plan trues up is unknown**")
        a.findings.append(
            f"⚠️ **Up to {_money(a.forfeited)} of match at risk this year.** A "
            f"{rate_pct:.0f}% deferral rate on {_money(comp)} reaches the "
            f"§402(g) ceiling of {_money(deferral_ceiling)} in about "
            f"{contributing} of {periods} pay periods. The match is calculated "
            f"per period, so the remaining {periods - contributing} periods "
            f"earn nothing — {state}."
        )
        a.findings.append(
            "Two fixes, and the first is usually better: **lower the deferral "
            "rate so contributions spread across the whole year**, or get "
            "confirmation in writing that the plan trues up. This is invisible "
            "on every statement — the balance looks fine because the "
            "deferrals arrived; only the match is missing."
        )
    return a


# ── total space ─────────────────────────────────────────────────────────────


def audit_space(
    contributions: dict,
    *,
    members: list[dict],
    year: int,
) -> SpaceAudit:
    lim = _limits.for_year(year)
    a = SpaceAudit(year=year, limits_known=lim.known)

    if not lim.known:
        a.findings.append(
            f"**Statutory limits for {year} are not in the table** "
            f"(`lib/pf/limits.py` has {_limits.years_available()}). Nothing "
            "below can be checked against a ceiling. Adding last year's "
            "figures would produce confident, wrong answers — so it does not."
        )
        return a

    a.findings.append(
        f"Limits used are the {year} figures from `lib/pf/limits.py` "
        f"({lim.source}). They change annually; **verify against irs.gov "
        "before acting on any number here.**"
    )

    plan = contributions.get("employer_plan") or {}
    by_id = {m.get("id"): m for m in members}
    primary = next((m for m in members if m.get("role") == "primary"), {})
    age = primary.get("age")

    # ── employer plan ───────────────────────────────────────────────────
    if plan:
        used = sum(float(plan.get(k) or 0) for k in
                   ("employee_pre_tax", "employee_roth", "employee_after_tax",
                    "employer_match", "employer_other"))
        ceiling = _limits.employer_plan_space(age, lim)
        cu = _limits.catch_up_for_age(age, lim)
        note = (f"§415(c) is {_money(lim.total_additions)}; the {_money(cu)} "
                "catch-up sits outside it, which is why the ceiling exceeds "
                "the headline number." if cu else
                f"§415(c) is {_money(lim.total_additions)}. No catch-up at "
                f"this age — it becomes available at {_limits.CATCH_UP_AGE}.")
        a.lines.append(SpaceLine(
            "Employer plan (§415(c) + catch-up)" if cu else "Employer plan (§415(c))",
            used, ceiling, note))

        elective = sum(float(plan.get(k) or 0)
                       for k in ("employee_pre_tax", "employee_roth"))
        elective_ceiling = (lim.elective_deferral or 0) + _limits.catch_up_for_age(age, lim)
        a.lines.append(SpaceLine(
            "…of which elective deferral (§402(g))", elective, elective_ceiling,
            "Pre-tax and Roth combined. After-tax contributions do not count "
            "against this, which is what makes the after-tax route possible."
        ))

        after_tax = float(plan.get("employee_after_tax") or 0)
        if ceiling and used < ceiling and after_tax == 0:
            headroom = ceiling - used
            a.findings.append(
                f"**{_money(headroom)} of employer-plan space is unused, and "
                "no after-tax contributions are being made.** If the plan "
                "permits after-tax contributions *and* in-plan Roth conversion "
                "or in-service withdrawal, that headroom can be filled. Both "
                "features are required — after-tax contributions without a "
                "conversion route leave earnings growing in a taxable-on-"
                "withdrawal bucket, which is worse than a plain brokerage "
                "account for most people. Check the summary plan description "
                "for both before acting."
            )
        elif ceiling and used >= ceiling:
            a.findings.append(
                "**Employer-plan space is fully used.** Nothing further is "
                "available here; additional saving goes to IRA space, HSA, or "
                "taxable."
            )

        if plan.get("in_plan_roth_conversion") is None and after_tax > 0:
            a.findings.append(
                "After-tax contributions are being made but "
                "`in_plan_roth_conversion` is not recorded. Without a "
                "conversion route those contributions accumulate taxable "
                "earnings. Confirm the plan offers it and that the election is "
                "actually switched on — it is frequently available and "
                "frequently left off by default."
            )

        comp = plan.get("compensation")
        if comp and lim.compensation_limit and comp > lim.compensation_limit:
            a.findings.append(
                f"Compensation of {_money(comp)} exceeds the §401(a)(17) cap "
                f"of {_money(lim.compensation_limit)}. Plan contributions and "
                "match are calculated on the capped figure, not the full "
                "amount — which can reduce a percentage-based match below what "
                "the headline rate implies."
            )

    # ── IRAs ────────────────────────────────────────────────────────────
    for row in contributions.get("ira") or []:
        mid = row.get("member")
        m = by_id.get(mid, {})
        space = _limits.ira_space(m.get("age"), lim)
        a.lines.append(SpaceLine(
            f"IRA — {mid}", float(row.get("amount") or 0), space,
            row.get("type") or "",
        ))
        if row.get("type") in ("roth_backdoor", "backdoor"):
            a.findings.append(
                f"IRA for `{mid}` is a backdoor Roth. **Check the pro-rata "
                "rule**: if that person holds *any* pre-tax IRA balance — "
                "traditional, SEP, or SIMPLE — the conversion is taxed "
                "proportionally across all of them, and the step is not the "
                "tax-free move it appears to be. A 401(k) balance does not "
                "count; an IRA balance does."
            )

    # ── HSA ─────────────────────────────────────────────────────────────
    hsa = contributions.get("hsa") or {}
    if hsa:
        coverage = hsa.get("coverage")
        space = _limits.hsa_space(coverage, age, lim)
        if hsa.get("eligible") is False:
            a.findings.append(
                "HSA recorded as not eligible — that requires enrolment in a "
                "qualifying high-deductible health plan. If a HDHP is offered "
                "at open enrolment, the HSA is worth evaluating on its own "
                "terms; see `hsa-review`."
            )
        else:
            a.lines.append(SpaceLine(
                f"HSA ({coverage})", float(hsa.get("contribution") or 0), space,
                "The only triple-tax-advantaged account available.",
            ))
    return a


def _money(x) -> str:
    if x is None:
        return "none"
    return f"${x:,.0f}"
