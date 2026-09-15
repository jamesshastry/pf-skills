#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Band-versus-calendar rebalancing, and what the correction would cost in tax."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, portfolio as P  # noqa: E402

REQUIRED = ["household.balance_sheet", "portfolio.target_allocation"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    rows = F._dig(data, "household.balance_sheet") or []
    a = P.review_allocation(rows, F._dig(data, "portfolio.target_allocation"))
    plan = P.rebalance_plan(
        a,
        policy=F._dig(data, "portfolio.rebalancing.policy"),
        last_reviewed=F._dig(data, "portfolio.rebalancing.last_reviewed"),
        as_of=F.as_of(data),
        annual_contributions=F._dig(data, "portfolio.annual_contributions"),
    )

    if not a.total:
        w("⚠️ **No classified holdings**, so no drift can be computed. Add "
          "`asset_class` to the balance sheet before this rule can be applied.")
        cli.disclaimer(w, "lib/pf/portfolio.py")
        return

    if plan.triggered:
        w(f"**The rule fires.** {len(a.breached)} class(es) breached their "
          f"band; {m(plan.buys)} of buying restores the target, of which "
          f"**{m(plan.taxable_sale_needed)} would require a taxable sale**.")
    else:
        w("✅ **The rule says do nothing.** Every class is inside its band.")
    w()

    w("## Drift against the bands")
    w()
    w.table(["Class", "Target", "Actual", "Drift", "Band", "Binds", "Trade"],
            [[t.asset_class, f"{s.target:.0%}", f"{s.share:.1%}",
              f"{s.drift:+.1%}", f"±{s.band:.1%}", s.which_band,
              ("—" if not s.breached
               else (f"buy {m(t.amount)}" if t.amount > 0 else f"sell {m(-t.amount)}"))]
             for s, t in zip(a.sleeves, plan.trades)])
    w()
    w(f"The band is **{P.ABSOLUTE_BAND:.0%} absolute or {P.RELATIVE_BAND:.0%} "
      "relative, whichever binds first** — the tighter of the two, per class.")
    w()

    w("## The rule")
    w()
    for f in plan.findings:
        w(f"- {f}")
        w()
    if plan.next_review and plan.next_review.on:
        w(f"- Next scheduled check: **{plan.next_review.on.isoformat()}** "
          f"({plan.next_review.urgency}).")
        w()

    w("## Decide it once")
    w()
    w("| | Bands | Calendar |")
    w("|---|---|---|")
    w("| Trigger | The portfolio moves | The date arrives |")
    w("| Trades when nothing moved | No | Yes |")
    w("| Misses a move between checks | Only up to the check interval | Yes, for up to a year |")
    w("| Needs a check cadence anyway | Yes — "
      f"{P.BAND_CHECK_MONTHS} months | The cadence *is* the rule |")
    w("| Failure mode | Checking too often becomes market-watching | "
      "Rebalancing on a date that happens to be a bad one |")
    w()
    w("Either beats the third option, which is what happens by default: the "
      "decision gets made afresh whenever someone opens the account, which is "
      "the moment when it is hardest to make well.")
    w()
    for f in a.findings:
        w(f"- {f}")
        w()

    cli.disclaimer(w, "lib/pf/portfolio.py",
                   "Trade sizes are the size of the correction, not an order "
                   "list — which lots to sell, and the tax on each, is a "
                   "portfolio-tool question.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Rebalancing rules", required=REQUIRED,
                             build=build))
