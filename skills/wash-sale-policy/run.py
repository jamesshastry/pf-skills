#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""The standing rule: what may not be bought, in which accounts, and until when."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, portfolio as P  # noqa: E402

REQUIRED = ["household.balance_sheet", "portfolio.wash_sale"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    ws = F._dig(data, "portfolio.wash_sale") or {}
    as_of = F.as_of(data)
    p = P.wash_sale_policy(
        ws.get("excluded_securities"),
        F._dig(data, "household.balance_sheet") or [],
        as_of=as_of,
        provider=ws.get("direct_index_provider"),
        continuous=ws.get("harvesting_continuous"),
        spouse_accounts_covered=ws.get("spouse_accounts_covered"),
    )

    if p.retirement_gaps:
        w(f"⚠️ **{len(p.retirement_gaps)} retirement account(s) are outside the "
          "exclusion list.** A replacement purchase there disallows the loss "
          "**permanently, with no basis adjustment**.")
    elif p.gaps:
        w(f"**{len(p.gaps)} account(s) are not covered** by the exclusion list. "
          "No retirement account is among them, which removes the worst case "
          "but not the rule.")
    else:
        w("✅ **Every recorded account is covered by the exclusion list.**")
    w()

    w("## The window")
    w()
    w.table(["", "Days"],
            [["Before the sale", str(P.WASH_SALE_WINDOW_DAYS)],
             ["After the sale", str(P.WASH_SALE_WINDOW_DAYS)],
             ["Total, including the day of sale", str(P.WASH_SALE_TOTAL_DAYS)]])
    w()
    w(f"Source: {P.WASH_SALE_SOURCE}. Verification status: "
      f"*{P.WASH_SALE_VERIFIED_ON}*.")
    w()

    w("## Account coverage")
    w()
    if p.accounts:
        w.table(["Account", "Type", "Policy applied", "Loss if breached"],
                [[a.name, a.account_type or "**unrecorded**",
                  {True: "yes", False: "**no**", None: "**unknown**"}[a.covered],
                  "**permanently disallowed, no basis adjustment**"
                  if a.is_retirement else
                  ("deferred into the replacement's basis"
                   if a.account_type == P.TAXABLE else "—")]
                 for a in p.accounts])
    else:
        w("No account carries an `account_type` or a "
          "`wash_sale_policy_applied` flag, so coverage cannot be assessed.")
    w()

    w("## Excluded securities")
    w()
    if p.exclusions:
        w.table(["Ticker", "Reason", "Sold on", "Source", "Purchase safe from"],
                [[e.ticker, e.reason or "—",
                  e.sold_on.isoformat() if e.sold_on else "**unrecorded**",
                  e.source or "—",
                  ("**never, while harvesting continues**" if p.continuous
                   else (e.clear_on(continuous=False).isoformat()
                         if e.sold_on else "**cannot be determined**"))]
                 for e in p.exclusions])
    else:
        w("None recorded.")
    w()

    w("## The rule")
    w()
    for f in p.findings:
        w(f"- {f}")
        w()

    w("## Writing the policy down")
    w()
    w("1. **Scope**: every account either spouse controls, at every broker, "
      "including IRAs, Roth IRAs, 401(k)s and HSAs.")
    w("2. **Prohibition**: no purchase of any listed security, or anything "
      "substantially identical to it, by any means — including automatic "
      "contributions, dividend reinvestment, and rebalancing buys.")
    w("3. **Duration**: until the provider removes the name. Where harvesting "
      "is continuous, treat the list as standing rather than dated.")
    w("4. **Refresh**: re-pull the list on a schedule. A list pulled at the "
      "moment of a trade is pulled too late to cover the 30 days before it.")
    w("5. **Turn off automatic reinvestment** in every account holding a "
      "listed name. It is the most common way this rule gets broken by "
      "someone who agreed to it.")
    cli.disclaimer(w, "lib/pf/portfolio.py",
                   "This is a policy, not a harvest: it never identifies a "
                   "loss, values one, or picks a replacement security. The "
                   "weakest input is `wash_sale_policy_applied` — unrecorded "
                   "coverage is treated as no coverage.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Wash sale policy", required=REQUIRED,
                             build=build))
