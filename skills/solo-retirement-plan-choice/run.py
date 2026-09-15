#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Solo 401(k), SEP IRA or defined benefit, for an owner-only business."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, entity as E, facts as F  # noqa: E402

REQUIRED = ["business.gross_revenue", "business.expenses", "household.members"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    biz = F._dig(data, "business") or {}
    members = F._dig(data, "household.members") or []
    owners = set(biz.get("owners") or [])
    owner = next((x for x in members if x.get("id") in owners), None)
    if owner is None:
        owner = next((x for x in members if x.get("role") == "primary"), {})
    age = owner.get("age")

    as_of = F.as_of(data)
    year = as_of.year if as_of else None

    net_profit = float(biz.get("gross_revenue") or 0) - float(biz.get("expenses") or 0)
    # An S-Corp's plan compensation is W-2 salary only. A Schedule C's is net
    # earnings from self-employment. Which applies is the entity question, so
    # it is read from the facts file rather than assumed.
    structure = biz.get("structure")
    salary = biz.get("owner_w2_salary")
    on_payroll = structure in (E.S_CORP, E.C_CORP)

    p = E.TaxParams(
        marginal_rate=F._dig(data, "assumptions.marginal_tax_rate"),
        ss_wage_base=F._dig(data, "assumptions.ss_wage_base"),
    )
    choice = E.solo_plan_options(
        net_profit=None if on_payroll else net_profit,
        w2_salary=salary if on_payroll else None,
        age=age, year=year, p=p)

    w(f"Owner-only business · {m(net_profit)} net profit · "
      f"{structure or 'structure not recorded'}"
      + (f" · owner salary {m(salary)}" if on_payroll and salary else "")
      + (f" · age {age}" if age else ""))
    w()

    if not choice.limits_known:
        w("## Stopped — no statutory limits for this year")
        w()
        for f in choice.findings:
            w(f"⚠️ {f}")
        cli.disclaimer(w, "lib/pf/entity.py")
        return

    if on_payroll and salary is None:
        w("⚠️ **The business is on payroll but `business.owner_w2_salary` is "
          "not recorded.** Plan space is a percentage of W-2 compensation, and "
          "distributions are not compensation — without the salary there is "
          "nothing to take a percentage of. Unknown is not the net profit.")
        w()

    best = choice.best
    if best:
        w(f"**{best.name} shelters the most: {m(best.total)}** this year.")
        w()

    w.table(["Plan", "Elective deferral", "Catch-up", "Employer", "Total",
             "Capped by"],
            [[o.name,
              m(o.employee_deferral) if o.employee_deferral else "none",
              m(o.catch_up) if o.catch_up else "—",
              m(o.employer) if o.total is not None else "—",
              f"**{m(o.total)}**" if o.total is not None else "**no figure**",
              o.capped_by or "—"]
             for o in choice.options])
    w()
    w(f"*§415(c) and the catch-up rules are read from `lib/pf/limits.py` for "
      f"{choice.year}; nothing here recomputes them. For what is already used "
      "across every account, see `contribution-space-audit`.*")
    w()

    for f in choice.findings:
        w(f"- {f}")
        w()

    for o in choice.options:
        if not o.findings:
            continue
        w(f"## {o.name}")
        w()
        for f in o.findings:
            w(f"- {f}")
            w()

    w("## The year the business hires")
    w()
    w("- A **Solo 401(k) stops being solo** the moment a non-spouse employee "
      "becomes eligible. It does not break; it becomes an ordinary 401(k), "
      "with nondiscrimination testing, a real Form 5500 and administration "
      "costs to match.")
    w("- A spouse working in the business is **not** a disqualifying employee, "
      "and can have their own deferral and employer contribution. That "
      "frequently doubles what an owner-operator couple can shelter.")
    w()

    w("## The weakest input")
    w()
    if on_payroll:
        w("**The W-2 salary.** It caps the employer contribution at 25% of "
          "itself, so a salary minimised for payroll-tax reasons in "
          "`entity-structure-comparison` also caps this plan. The two "
          "decisions are the same decision, and optimising them separately "
          "gets both wrong.")
    else:
        w("**Net profit**, which is an estimate until the year closes. The "
          "employer contribution is a percentage of it, and the deadline for "
          "funding an employer contribution runs to the return due date — so "
          "this figure can be finalised after the year ends, unlike the "
          "elective deferral election.")
    w()
    w("Deadlines differ by plan and are the thing most often missed: a Solo "
      "401(k) generally must **exist** before the year ends even though it can "
      "be funded later, while a SEP can be both established and funded up to "
      "the return due date. Check the current rule before relying on either.")
    cli.disclaimer(w, "lib/pf/entity.py",
                   "Statutory limits are in `lib/pf/limits.py` and are marked "
                   "unverified — check them against irs.gov before relying on "
                   "a figure.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Solo retirement plan choice",
                             required=REQUIRED, build=build))
