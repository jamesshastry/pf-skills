#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Medicare does not travel — the keep-or-drop arithmetic on Part B."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, crossborder as X, facts as F  # noqa: E402

REQUIRED = ["crossborder.medicare.months_abroad_planned",
            "crossborder.medicare.standard_premium_monthly"]
m = cli.money

HEADLINE = {
    "keep": "**Keep Part B while abroad.**",
    "drop": "**Dropping Part B is cheaper on these numbers.**",
    "cannot_determine": "⚠️ **This cannot be decided on what is recorded.**",
}


def build(data: dict, w: cli.Writer) -> None:
    med = F._dig(data, "crossborder.medicare") or {}
    d = X.part_b_decision(
        months_abroad=float(med.get("months_abroad_planned")),
        standard_premium_monthly=float(med.get("standard_premium_monthly")),
        will_return=med.get("will_return_to_us"),
        years_after_return=med.get("years_after_return"),
    )

    w("🚫 **Medicare does not pay for care received outside the United "
      "States.** The exceptions are narrow and situational, not a travel "
      "benefit. Everything below follows from that one fact.")
    w()
    w(HEADLINE[d.recommendation])
    w()

    w("## The keep-or-drop arithmetic")
    w()
    w.table(["", "Cost"], [
        [f"Keep Part B for {d.months_abroad:.0f} months abroad "
         "(premiums for cover you cannot use)", m(d.keep_cost)],
        [f"Drop it — permanent penalty of {d.penalty_rate:.0%} "
         f"({d.penalty_years} full year(s) × {X.PART_B_PENALTY_PER_12M:.0%})",
         f"{m(d.penalty_monthly)}/month"],
        ["Penalty over the years back in the US",
         m(d.penalty_lifetime) if d.penalty_lifetime is not None
         else "**cannot be determined**"],
    ])
    w()
    w(f"At a standard premium of {m(d.standard_premium_monthly)}/month, which "
      "you supplied — it is not hard-coded here, because it changes annually "
      "and a stale figure would go wrong silently.")
    w()
    if d.years_after_return is None:
        w("**Years living in the US after returning is not recorded**, so the "
          "penalty cannot be totalled. It is the term that decides the "
          "comparison: the keep cost is linear in time abroad, the penalty "
          "cost is time abroad multiplied by years lived afterwards.")
    else:
        w(f"Over {d.years_after_return:.0f} years back in the US. The keep "
          "cost is linear in time abroad; the penalty cost is time abroad "
          "multiplied by years lived afterwards — which is why long absences "
          "followed by long lives favour keeping.")

    w()
    w("## Findings")
    w()
    for f in d.findings:
        w(f"- {f}")
        w()

    w("## The Medigap foreign travel benefit is a holiday benefit")
    w()
    for f in X.medigap_notes(has_medigap=med.get("has_medigap")):
        w(f"- {f}")
        w()
    w.table(["Limit", "Value"], [
        ["Share of emergency care paid", f"{X.MEDIGAP_FOREIGN_COINSURANCE:.0%}"],
        ["Deductible", m(X.MEDIGAP_FOREIGN_DEDUCTIBLE)],
        ["Covered window", f"first {X.MEDIGAP_FOREIGN_TRIP_DAYS} days of a trip"],
        ["Maximum", f"**{m(X.MEDIGAP_FOREIGN_LIFETIME_MAX)} — lifetime, not annual**"],
    ])

    w()
    w("## The alternative: private expatriate cover")
    w()
    for f in X.expat_cover_notes(
            premium_annual=med.get("expat_policy_premium_annual")):
        w(f"- {f}")
        w()

    w("## What this will not do")
    w()
    w("- **It does not say whether a destination's public system will admit "
      "you**, or on what terms. Residency status, contribution history and age "
      "limits all bear on it and none of them is in this repository's tables.")
    w("- **It does not project premiums.** Every figure here is a nominal "
      "current-year amount you supplied.")
    w("- **It does not cover Medicare Advantage**, whose network rules abroad "
      "differ from traditional Medicare's and have to be read on the plan.")
    w()
    w("**The weakest input is whether you will return to the US.** It is an "
      "intention rather than a fact, it decides the whole comparison, and it "
      "is the one people revise — for family, for care, and because a plan "
      "made at 65 is not the plan at 80.")
    cli.disclaimer(w, "lib/pf/crossborder.py",
                   "Enrolment rules and penalty mechanics should be confirmed "
                   "against medicare.gov before acting; the premium and "
                   "penalty figures here are yours, not fetched.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Cross-border healthcare",
                             required=REQUIRED, build=build))
