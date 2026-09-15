#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Withdrawal sequencing — which account to spend first, and why not strictly."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, limits as L, retirement as R  # noqa: E402

REQUIRED = ["household.members", "household.balance_sheet"]


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    rows = F._dig(data, "household.balance_sheet") or []
    names = " ".join((r.get("name") or "").lower() for r in rows)

    d = R.drawdown_guidance(
        current_age=primary.get("age"),
        ages=L.retirement_ages(primary.get("birth_year")),
        has_taxable=F.tier_total(data, F.LIQUID) > 0,
        has_tax_deferred=any(k in names for k in ("401k", "ira", "403b", "457")),
        has_roth="roth" in names,
    )

    w("## The conventional order")
    w()
    w.table(["#", "Account", "Why"],
            [[i, label, why] for i, (_, label, why) in enumerate(d.sequence, 1)])
    w()
    for f in d.findings:
        w(f"- {f}")
        w()
    w("## The version that actually works")
    w()
    w("Strict sequencing is the wrong answer for most households, and it is "
      "wrong in a specific way: it leaves the low brackets empty during early "
      "retirement, then forces large ordinary-income withdrawals once RMDs "
      "begin. The total tax bill is higher even though every individual step "
      "looked tax-efficient.")
    w()
    w("The better rule is **fill brackets, don't drain accounts**:")
    w()
    w("1. Spend from taxable for cash flow.")
    w("2. Each year, compute the headroom to the top of the target bracket.")
    w("3. Fill it with tax-deferred withdrawals or Roth conversions.")
    w("4. Leave the Roth alone as long as possible.")
    w()
    w("Unused bracket space does not carry forward. A year spent entirely in "
      "the lowest bracket has wasted the headroom above it permanently.")
    cli.disclaimer(w, "lib/pf/retirement.py",
                   "Bracket management is jurisdiction- and year-specific; "
                   "this skill gives the structure, not the numbers.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Withdrawal sequencing", required=REQUIRED, build=build))
