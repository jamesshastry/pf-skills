#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Education funding — the gap, and the rule that outranks it."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, education as E, facts as F, retirement as R  # noqa: E402

REQUIRED = ["household.members", "education.children"]
m = cli.money


def _retirement_status(data: dict):
    """Cheap read-only check so the ordering rule can be applied rather than
    merely stated. Returns (on_track, age_at_target) or (None, None)."""
    savings = F._dig(data, "retirement.annual_savings")
    spending = F._dig(data, "household.annual_spending")
    if savings is None or spending is None:
        return None, None
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    assets = (F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
              + F.tier_total(data, F.ILLIQUID))
    r = R.assess_readiness(annual_spending=float(spending), assets=assets,
                           annual_savings=float(savings),
                           current_age=primary.get("age"))
    return r.years_to_target is not None, r.age_at_target


def build(data: dict, w: cli.Writer) -> None:
    edu = F._dig(data, "education") or {}
    state = F._dig(data, "meta.jurisdiction.state")
    p = E.plan_for(
        edu.get("children"),
        members=F._dig(data, "household.members") or [],
        accounts=edu.get("accounts") or [],
        cost_inflation=float(edu.get("cost_inflation") or E.DEFAULT_COST_INFLATION),
        real_return=float(edu.get("real_return") or E.DEFAULT_REAL_RETURN),
        state=state,
    )

    w("## First, the rule that outranks everything else")
    w()
    on_track, age_at = _retirement_status(data)
    for line in E.ordering_rule(retirement_on_track=on_track,
                                retirement_age_at_target=age_at):
        w(f"- {line}")
        w()

    w("## The gap")
    w()
    if p.total_gap > 0:
        w(f"**{m(p.total_gap)} short** against a projected "
          f"{m(p.total_projected_cost)} total cost.")
        if p.unallocated_savings:
            w()
            w(f"> That gap is **overstated by up to "
              f"{m(p.unallocated_savings)}** — education savings exist but no "
              "account names a beneficiary, so nothing counts toward either "
              "child. Allocate them and re-run before treating the figure as "
              "the real shortfall.")
    else:
        w(f"✅ **Fully funded** against a projected "
          f"{m(p.total_projected_cost)} total cost.")
    w()
    w.table(["Child", "Age", "Years to start", "Cost (nominal)",
             "Earmarked", "Projected", "Gap"],
            [[c.member_id, c.age if c.age is not None else "**?**",
              f"{c.years_until_start:.0f}" if c.years_until_start is not None else "**?**",
              m(c.projected_cost), m(c.allocated_savings), m(c.projected_savings),
              f"**{m(c.gap)}**" if c.gap > 0 else "—"]
             for c in p.children])
    w()
    w(f"Costs inflate at {float(edu.get('cost_inflation') or E.DEFAULT_COST_INFLATION):.1%}/yr, "
      f"applied to each year of study separately — year four carries three "
      f"more years of inflation than year one. Savings grow at "
      f"{float(edu.get('real_return') or E.DEFAULT_REAL_RETURN):.1%} real, "
      "deliberately below the retirement assumption: money needed on a fixed "
      "near date cannot be invested the same way as money needed in decades.")

    for c in p.children:
        if not c.findings:
            continue
        w()
        w(f"### {c.member_id}")
        w()
        for f in c.findings:
            w(f"- {f}")

    if p.findings:
        w()
        for f in p.findings:
            w(f"- {f}")

    w()
    w("## Mechanics")
    w()
    leftover = any(c.gap < 0 for c in p.children) or p.unallocated_savings > 0
    for line in E.mechanics_notes(state=state, has_leftover_risk=leftover):
        w(f"- {line}")
        w()

    w("## Closing the gap, in order of preference")
    w()
    for i, s in enumerate([
        "**A cheaper institution.** The single largest lever, and the one "
        "families consider last. The spread between in-state public and "
        "private is usually larger than everything else on this list "
        "combined.",
        "**Current cash flow during the study years.** Paying from income "
        "rather than from savings is not a failure of planning; for a high "
        "earner it is often the plan.",
        "**The student's own contribution** — work, scholarships, a "
        "reasonable loan in their name.",
        "**Federal loans in the student's name** before anything in the "
        "parents'. Parent loans carry no forgiveness or income-driven "
        "repayment worth the name.",
        "**Not** reducing retirement contributions. See the top of this "
        "report.",
    ], 1):
        w(f"{i}. {s}")
    cli.disclaimer(w, "lib/pf/education.py",
                   "Aid formulas, 529 rules and state treatment change; the "
                   "state table records itself as unverified.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Education funding", required=REQUIRED, build=build))
