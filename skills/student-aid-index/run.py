#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Student Aid Index — whether need-based aid is plausible, and whether assets can move it."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import aid as A, cli, facts as F  # noqa: E402

REQUIRED = [
    "household.members",
    "household.balance_sheet",
    "education.financial_aid.award_year",
    "education.financial_aid.income_year",
    "education.financial_aid.parent_total_income",
    "education.financial_aid.parent_federal_income_tax",
    "education.financial_aid.parent_earned_income",
    "education.financial_aid.family_size",
    "education.financial_aid.older_parent_age",
    "education.financial_aid.two_parents",
    "education.financial_aid.cost_of_attendance",
]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    fa = F._dig(data, "education.financial_aid")
    try:
        h = A.household(fa, balance_sheet=F._dig(data, "household.balance_sheet") or [],
                        members=F._dig(data, "household.members") or [],
                        accounts=F._dig(data, "education.accounts") or [])
    except A.AidError as e:
        w("## Stopped — the inputs cannot support an SAI")
        w()
        w(f"- {e}")
        w()
        w("See SCHEMA.md `financial_aid`. Fill this in rather than letting the skill guess.")
        return
    p = h.parent

    w(f"**Award year {h.award_year}**, based on {h.income_year} income "
      "(prior-prior year) and assets on the filing date.")
    w()
    w("## The decision")
    w()
    for line in h.findings:
        w(f"- {line}")
        w()

    w("## Parents' contribution")
    w()
    rows = [["Total income (AGI + untaxed income)", m(float(fa["parent_total_income"]))]]
    rows += [[f"Less {k}", f"−{m(v)}"] for k, v in p.allowances.items()]
    rows += [["**Available income**", f"**{m(p.available_income)}**"],
             ["Reportable parent assets", m(p.reportable_assets)],
             [f"× {A.ASSET_CONVERSION_RATE:.0%} conversion", m(p.asset_contribution_income)],
             ["Adjusted available income", m(p.adjusted_available_income)],
             ["**Parents' contribution**", f"**{m(p.parent_contribution)}**"],
             ["— from income alone", m(p.parent_contribution_income_only)]]
    w.table(["", "Amount"], rows)
    w()
    w("There is **no state tax allowance** and no reduction for two children in "
      "college at once — both were removed by the FAFSA Simplification Act.")
    w()

    w("## Assets: what counts")
    w()
    w.table(["Item", "Value", "FAFSA treatment"],
            [[x.name, m(x.value), x.reason] for x in h.assets])
    w()
    if not h.include_foreign:
        w("> Foreign assets are excluded **by household choice**. The FAFSA asks "
          "for investments wherever held; an actual filing must follow the "
          "form's instructions.")
        w()

    w("## Per student")
    w()
    rows = []
    for s in h.students:
        if s.eligible is False:
            rows.append([s.name, "not FAFSA-eligible", "—", m(s.student_assets)])
            continue
        flag = "" if s.eligible else " *(eligibility not recorded — computed as if eligible)*"
        if not s.income_recorded:
            flag += " *(student income not recorded)*"
        rows.append([s.name + flag, m(s.sai),
                     ", ".join(f"{k}: {m(v)}" for k, v in s.need.items()),
                     m(s.student_assets)])
    w.table(["Student", "SAI", "Need by school", "Student-held assets"], rows)
    w()
    w("**Weakest input:** the income year. The FAFSA uses income from two years "
      "before the award year, so a one-off gain or a job loss in that year moves "
      "the result more than any asset decision.")
    cli.disclaimer(w, "lib/pf/aid.py",
                   "The CSS Profile and other institutional methodologies are not modelled.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Student Aid Index", required=REQUIRED, build=build))
