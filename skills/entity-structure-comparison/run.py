#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Entity structure — and the salary optimum the payroll-tax story misses."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, entity as E, facts as F  # noqa: E402

REQUIRED = ["business.gross_revenue", "business.expenses"]
m = cli.money
LABEL = {E.SCHEDULE_C: "Schedule C / single-member LLC",
         E.S_CORP: "S-Corp election", E.C_CORP: "C-Corp"}


def _params(data: dict) -> E.TaxParams:
    members = F._dig(data, "household.members") or []
    adults = [x for x in members if x.get("role") in ("primary", "spouse")]
    status = F._dig(data, "household.filing_status") or (
        "married_joint" if len(adults) > 1 else "single")
    # The Social Security wage base is **per person**, so only the owner's own
    # outside wages consume it — a spouse's salary does not. Asked for
    # explicitly rather than inferred from `income_annual`, which for a
    # self-employed member may already be the business income.
    owners = set(F._dig(data, "business.owners") or [])
    other_wages = float(F._dig(data, "business.owner_outside_wages") or 0.0)
    # Household income from outside the business, which decides which §199A
    # regime applies. That test is on the return's taxable income, so it is
    # household-wide even though the wage base is not.
    other_income = float(sum(x.get("income_annual") or 0 for x in adults
                             if x.get("id") not in owners))
    return E.TaxParams(
        marginal_rate=F._dig(data, "assumptions.marginal_tax_rate"),
        state_rate=F._dig(data, "assumptions.state_tax_rate"),
        ss_wage_base=F._dig(data, "assumptions.ss_wage_base"),
        qbi_threshold=F._dig(data, "assumptions.qbi_threshold"),
        qbi_phase_in=F._dig(data, "assumptions.qbi_phase_in_range"),
        qualified_dividend_rate=F._dig(data, "assumptions.qualified_dividend_rate"),
        niit_rate=F._dig(data, "assumptions.niit_rate"),
        filing_status=status,
        other_wages=other_wages,
        other_taxable_income=other_income,
        deductions_total=F._dig(data, "assumptions.deductions_total"),
    )


def build(data: dict, w: cli.Writer) -> None:
    biz = F._dig(data, "business") or {}
    b = E.Business(
        gross_revenue=float(biz.get("gross_revenue") or 0),
        expenses=float(biz.get("expenses") or 0),
        sstb=bool(biz.get("sstb")),
        field=biz.get("field"),
        ubia=biz.get("ubia"),
        reasonable_salary_floor=biz.get("reasonable_salary_floor"),
        s_corp_annual_cost=biz.get("s_corp_annual_cost"),
    )
    p = _params(data)
    c = E.compare(b, p)

    w(f"Business: {m(b.gross_revenue)} revenue − {m(b.expenses)} expenses = "
      f"**{m(b.net_profit)} net profit**"
      + (f" · {biz.get('field')}" if biz.get("field") else "")
      + (" · **specified service trade or business**" if b.sstb else ""))
    w()

    if not c.params_known:
        w("## Stopped — the indexed figures are missing")
        w()
        for f in c.findings:
            w(f"⚠️ {f}")
        w()
        for path in c.missing:
            w(f"- `{path}`")
        w()
        w("These are asked for rather than held in this repository because "
          "they change every year, and a stale figure here would corrupt every "
          "number in the report while looking exactly as confident.")
        cli.disclaimer(w, "lib/pf/entity.py")
        return

    best = c.best
    if best:
        w(f"**{LABEL[best.structure]} produces the most take-home** on these "
          f"figures: {m(best.take_home)}.")
        w()

    w.table(["Structure", "Owner salary", "Payroll tax", "§199A deduction",
             "Income tax", "Take-home"],
            [[LABEL[o.structure],
              m(o.salary) if o.salary else "—",
              m(o.payroll_tax),
              m(o.qbi.deduction) if o.qbi.regime != "n/a" else "none",
              m(o.federal_income_tax + o.state_tax + o.entity_tax),
              f"**{m(o.take_home)}**" if o.unavailable is None else "—"]
             for o in c.outcomes])
    w()
    w("*Take-home is cash in the owners' hands after federal and state tax, "
      "before any retirement contribution. The federal figure applies your "
      "marginal rate to taxable income rather than a bracket schedule, so the "
      "**gaps between rows** are reliable and the levels are approximations.*")
    w()

    for o in c.outcomes:
        if o.unavailable:
            w(f"⚠️ **{LABEL[o.structure]} — no figure.** {o.unavailable}")
            w()

    # ── the salary optimum ──────────────────────────────────────────────
    w("## The salary optimum")
    w()
    w("W-2 salary reduces payroll tax exposure **and** reduces qualified "
      "business income. Those pull in opposite directions, so reasonable "
      "salary has an optimum rather than a floor.")
    w()
    curve = c.curve
    if curve.best:
        pts = _sample(curve.points, 7)
        w.table(["Salary", "§199A deduction", "Payroll tax", "Take-home"],
                [[m(pt.salary), m(pt.qbi_deduction), m(pt.payroll_tax),
                  (f"**{m(pt.take_home)}**"
                   if pt is curve.best else m(pt.take_home))]
                 for pt in pts])
        w()
    for f in curve.findings:
        w(f"- {f}")
        w()

    # ── the verdict at another profit level ─────────────────────────────
    # The S-Corp verdict flips with profit, and a report built on one profit
    # level shows one side of it. Any scenario recorded in the facts file is
    # re-run here at verdict level only — the full comparison above is the
    # one that applies to this year.
    scenarios = biz.get("alternate_scenarios") or []
    if scenarios:
        w("## The same election at a different profit level")
        w()
        w("The verdict is not a property of the business, it is a property of "
          "the profit. A reasonable salary that is defensible in a good year "
          "consumes most of a slow year's profit, leaving little to shelter "
          "as a distribution while the running cost stays the same.")
        w()
        for sc in scenarios:
            alt = E.Business(
                gross_revenue=float(sc.get("gross_revenue", b.gross_revenue)),
                expenses=float(sc.get("expenses", b.expenses)),
                sstb=b.sstb, field=b.field, ubia=b.ubia,
                reasonable_salary_floor=b.reasonable_salary_floor,
                s_corp_annual_cost=b.s_corp_annual_cost,
            )
            ac = E.compare(alt, p)
            w(f"**{sc.get('label') or 'Alternate scenario'}** — "
              f"{m(alt.gross_revenue)} revenue, {m(alt.net_profit)} net profit")
            w()
            for f in ac.findings[:1]:
                w(f"- {f}")
            w()

    w("## What the arithmetic says, and what it does not")
    w()
    for o in c.outcomes:
        if not o.findings:
            continue
        w(f"**{LABEL[o.structure]}**")
        w()
        for f in o.findings:
            w(f"- {f}")
        w()
    for f in c.findings:
        w(f"- {f}")
        w()

    flags = E.cross_border_flags(
        tax_home_abroad=bool(F._dig(data, "household.tax_home_abroad")))
    if flags:
        w("## Living abroad")
        w()
        for f in flags:
            w(f"- {f}")
            w()

    w("## The weakest input")
    w()
    if b.reasonable_salary_floor is None:
        w("**The reasonable salary, which is not recorded.** Every S-Corp "
          "figure above moves with it, and this skill will not invent it — it "
          "depends on what the work is, what comparable people are paid to do "
          "it, and how much of the profit is your labour rather than your "
          "capital. Get comparable compensation data and record "
          "`business.reasonable_salary_floor`.")
    else:
        w(f"**The reasonable salary floor of {m(b.reasonable_salary_floor)}.** "
          "It is an assertion, not a computation, and it carries the whole "
          "S-Corp result. If it cannot be supported with comparable "
          "compensation data, the election is not supportable either — the IRS "
          "can recharacterise distributions as wages, with payroll tax, "
          "penalties and interest.")
    w()
    w("**Beneficial ownership information (BOI) reporting is not modelled "
      "here.** It has been reported that an August 2026 FinCEN final rule "
      "exempts US domestic companies, leaving only foreign-formed entities in "
      "scope. **That is unverified** — it is repeated as reported, not "
      "asserted, and the Corporate Transparency Act's scope has moved more "
      "than once. Check fincen.gov/boi before concluding you have nothing to "
      "file. The penalty falls on the filer.")
    cli.disclaimer(w, "lib/pf/entity.py",
                   "An entity election has legal and liability consequences "
                   "beyond tax, and the S-Corp election has deadlines. Take "
                   "this to a CPA before filing Form 2553.")


def _sample(points: list, n: int) -> list:
    """Evenly spaced samples, with the optimum always included."""
    if len(points) <= n:
        return points
    best = max(points, key=lambda pt: pt.take_home)
    step = (len(points) - 1) / (n - 1)
    picked = [points[round(i * step)] for i in range(n)]
    if best not in picked:
        picked[len(picked) // 2] = best
    return sorted(picked, key=lambda pt: pt.salary)


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Entity structure comparison",
                             required=REQUIRED, build=build))
