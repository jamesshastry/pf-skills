#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Target allocation, glide path, and the usually-unexamined half: asset location."""
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

    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), None)
    years = P.years_to_retirement(
        F._dig(data, "retirement.planned_retirement_age"),
        (primary or {}).get("age"))
    g = P.glide_path(years=years, actual_equity=a.inv.equity_share)
    loc = P.review_location(a.inv)

    if not a.total:
        w("⚠️ **No classified holdings.** Every balance-sheet row is either "
          "earmarked, pending, or missing an `asset_class`, so there is no "
          "allocation to review.")
        for f in a.findings:
            w()
            w(f"- {f}")
        cli.disclaimer(w, "lib/pf/portfolio.py")
        return

    if a.breached:
        w(f"**{len(a.breached)} of {len(a.sleeves)} classes are outside their "
          f"band**, against {m(a.total)} of classified holdings.")
    else:
        w(f"✅ **Every class is inside its band**, against {m(a.total)} of "
          "classified holdings.")
    w()

    w("## Target against actual")
    w()
    w.table(["Class", "Target", "Actual", "Value", "Drift", "Band", "Status"],
            [[s.asset_class, f"{s.target:.0%}", f"{s.share:.1%}", m(s.value),
              f"{s.drift:+.1%}", f"±{s.band:.1%}",
              "**outside**" if s.breached else "in band"]
             for s in a.sleeves])
    w()
    for f in a.findings:
        w(f"- {f}")
        w()

    w("## Glide path")
    w()
    if g.known:
        w(f"Horizon **{g.years:.0f} years** · reference equity band "
          f"**{g.low:.0%}–{g.high:.0%}** · held "
          + (f"**{g.actual:.0%}**." if g.actual is not None else "unknown."))
        w()
    for f in g.findings:
        w(f"- {f}")
        w()

    w("## Asset location")
    w()
    by_type: dict[str, dict[str, float]] = {}
    for h in a.inv.holdings:
        by_type.setdefault(h.account_type or "unrecorded", {})
        by_type[h.account_type or "unrecorded"][h.asset_class] = (
            by_type[h.account_type or "unrecorded"].get(h.asset_class, 0.0) + h.value)
    classes = sorted({c for d in by_type.values() for c in d})
    w.table(["Account type", *classes, "Total"],
            [[t, *[m(d.get(c, 0)) if d.get(c) else "—" for c in classes],
              m(sum(d.values()))]
             for t, d in sorted(by_type.items())])
    w()
    for f in loc.findings:
        w(f"- {f}")
        w()

    w("## The boundary")
    w()
    w("- **This sets the policy; it does not place the trades.** Which funds, "
      "which lots, and in what order is a portfolio-tool question — see "
      "`rebalancing-rules` for whether the drift above is even worth "
      "correcting yet.")
    w("- **Balances, not market prices.** Every figure is from the facts file "
      "as of `meta.as_of`. Bands exist because the exact number does not "
      "matter; if a class is sitting on its band edge, re-read the balances "
      "before acting on it.")
    cli.disclaimer(w, "lib/pf/portfolio.py",
                   "The weakest input is `account_type` on each holding: "
                   "without it the location analysis cannot run at all.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Asset allocation review", required=REQUIRED,
                             build=build))
