#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Debt payoff priority — avalanche vs snowball, with the difference priced."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, debt as D, facts as F  # noqa: E402

REQUIRED = ["debts"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    extra = F._dig(data, "assumptions.monthly_debt_extra") or 0
    rate = F._dig(data, "assumptions.marginal_tax_rate") or 0.0
    p = D.plan(F._dig(data, "debts") or [], monthly_extra=float(extra),
               marginal_rate=float(rate),
               expected_return_apr=F._dig(data, "assumptions.expected_return_apr"))

    if not p.debts:
        w("No debts with a balance recorded.")
        return

    w(f"**{m(p.total_balance)}** across {len(p.debts)} debt(s) · minimums "
      f"{m(p.total_minimum)}/mo · extra {m(extra)}/mo.")
    w()
    w.table(["Debt", "Balance", "APR", "After tax", "Minimum"],
            [[d.name, m(d.balance), f"{d.apr:.2%}",
              f"{d.after_tax_apr(rate):.2%}" + (" *ded.*" if d.deductible else ""),
              m(d.minimum_payment)] for d in p.debts])

    if p.avalanche and p.snowball and p.avalanche.terminated:
        w()
        w("## The two orderings")
        w()
        w.table(["Method", "Order", "Months", "Total interest"],
                [["**Avalanche** (rate)", " → ".join(p.avalanche.order),
                  p.avalanche.months, m(p.avalanche.total_interest)],
                 ["**Snowball** (balance)", " → ".join(p.snowball.order),
                  p.snowball.months, m(p.snowball.total_interest)]])
        w()
        w("Both simulations roll a cleared debt's minimum payment into the "
          "next target, so the only difference is the order.")
    w()
    for f in p.findings:
        w(f"- {f}")
        w()

    w("## How to choose")
    w()
    w("**Avalanche is mathematically correct. Snowball is the one people "
      "finish.** The cost of the difference is stated above in dollars, which "
      "is the only honest way to present it — a few hundred dollars for a plan "
      "that actually gets completed is a good trade, and the optimal schedule "
      "abandoned in month four is not optimal.")
    w()
    w("Pick avalanche if the gap is large or the rates are far apart. Pick "
      "snowball if past attempts have stalled. Do not let the choice itself "
      "become the reason nothing starts.")
    cli.disclaimer(w, "lib/pf/debt.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Debt payoff priority", required=REQUIRED, build=build))
