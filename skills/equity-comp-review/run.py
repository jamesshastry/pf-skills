#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Equity compensation — the vesting cliff an annual income figure hides."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, concentration as C, facts as F  # noqa: E402

REQUIRED = ["equity_comp"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    eq = F._dig(data, "equity_comp") or {}
    today = F.as_of(data)
    o = C.vesting_outlook(eq.get("grants"), today=today)

    if o.delta > 0:
        w(f"⚠️ **Equity income steps down {m(o.delta)}/yr "
          f"({o.drop_share:.0%}) over the next {C.CLIFF_HORIZON_MONTHS} "
          f"months. First step: {o.next_cliff.isoformat()}.**")
    else:
        w("✅ **No near-term vesting cliff.**")
    w()
    w.table(["", ""], [
        ["Current run rate", f"{m(o.run_rate)}/yr"],
        ["Steady state without refresh", f"**{m(o.steady_state)}/yr**"],
        ["Delta", f"**−{m(o.delta)}**"],
    ])
    w()
    if o.grants:
        w.table(["Grant", "Annual value", "Completes", "Months left"],
                [[g.id, m(g.annual_value),
                  g.completes.isoformat() if g.completes else "—",
                  f"{g.months_remaining(today):.0f}" if g.months_remaining(today) is not None else "—"]
                 for g in o.grants])
    w()
    for f in o.findings:
        w(f"- {f}")
        w()

    w("## Where this figure gets used")
    w()
    w("Anything tested against income — housing affordability, savings rate, "
      "insurance need — should be tested against the **steady state**, not "
      "the run rate. Variable compensation is the first thing to fall and the "
      "last thing people model.")
    w()
    w("Two habits worth adopting, both of which remove a decision rather than "
      "requiring a better one:")
    w()
    w("- **Sell at vest as a standing policy.** See "
      "`employer-concentration-risk`. Vested shares held are identical to "
      "cash received and immediately used to buy employer stock.")
    w("- **Treat equity as a bonus, not as salary.** Budgeting fixed costs "
      "against it converts a variable input into a fixed obligation, which is "
      "the wrong direction.")
    cli.disclaimer(w, "lib/pf/concentration.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Equity compensation review",
                             required=REQUIRED, build=build))
