#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Blended burn across a split-living arrangement, and the target that follows."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, crossborder as X, facts as F, retirement as R  # noqa: E402

REQUIRED = ["crossborder.locations", "household.balance_sheet",
            "retirement.annual_savings"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    assets = (F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
              + F.tier_total(data, F.ILLIQUID))
    savings = float(F._dig(data, "retirement.annual_savings"))

    p = X.model(
        F._dig(data, "crossborder.locations") or [],
        assets=assets,
        annual_savings=savings,
        fixed_annual=float(F._dig(data, "crossborder.fixed_annual_costs") or 0),
        duplicate_housing=F._dig(data, "crossborder.duplicate_housing"),
    )

    if not p.legs:
        w("⚠️ No locations recorded, so there is nothing to blend.")
        return

    w(f"Blended burn **{m(p.blended_annual)}/yr** against **"
      f"{m(p.baseline_annual)}** for a full year at the dearest location — a "
      f"saving of {m(p.annual_saving)}/yr, which cuts the portfolio target by "
      f"**{m(p.target_reduction)}** at a {p.withdrawal_rate:.1%} withdrawal "
      f"rate.")
    w()

    w("## The split")
    w()
    w.table(["Location", "Country", "Months", "Monthly", "Annual",
             "Est. days", "Currency"],
            [[l.name, l.country or "—", f"{l.months:g}", m(l.monthly_spending),
              m(l.annual_cost), f"{l.estimated_days:.0f}",
              "home" if l.home_currency else "**foreign**"]
             for l in p.legs])
    w()
    w(f"Plus {m(p.fixed_annual)}/yr of costs that do not move with location. "
      f"Estimated days are months × {X.DAYS_PER_MONTH} — an estimate for "
      "flagging day tests, never a substitute for counting real days.")

    w()
    w("## The target, three ways")
    w()
    w.table(["Scenario", "Annual burn", "Target", "Years to it"], [
        ["Full year at the dearest location", m(p.baseline_annual),
         m(p.baseline_target),
         f"{p.years_to_baseline:.0f}" if p.years_to_baseline is not None
         else "not reached"],
        ["**Blended, as planned**", f"**{m(p.blended_annual)}**",
         f"**{m(p.target)}**",
         f"**{p.years_to_target:.0f}**" if p.years_to_target is not None
         else "**not reached**"],
        [f"Blended, {X.FX_STRESS:.0%} adverse FX", m(p.stressed_annual),
         m(p.stressed_target), "—"],
    ])
    w()
    w(f"Assets {m(assets)}, savings {m(savings)}/yr, "
      f"{R.DEFAULT_REAL_RETURN:.0%} real return. Targets use "
      f"`retirement.target_for` and years use `retirement.years_to` — the same "
      "machinery as `retirement-readiness`, imported rather than "
      "reimplemented, so a location-adjusted target and an ordinary one cannot "
      "drift apart.")
    w()
    w("**Plan on the stressed row.** The saving is denominated in a currency "
      "the household neither earns nor holds, and that is the weakest input in "
      "the model — everything else here is arithmetic on figures you supplied.")

    w()
    w("## Findings")
    w()
    for f in p.findings:
        w(f"- {f}")
        w()

    w("## What this will not do")
    w()
    w("- **It does not model local inflation.** A constant real cost "
      "differential over decades is an assumption, not a finding, and it is "
      "the thing most likely to erode this quietly.")
    w("- **It does not decide whether you are tax resident anywhere.** It "
      "flags where an estimated day count crosses or approaches a recorded "
      "threshold, from a table holding only "
      f"{', '.join(X.countries_available())}.")
    w("- **It does not price healthcare**, which is usually the largest single "
      "line in an arrangement like this. See `cross-border-healthcare`.")
    w("- **It does not ask whether you want to live this way.** Two households "
      "a year, two sets of friendships, and a travel schedule are the actual "
      "cost, and no model here captures them.")
    cli.disclaimer(w, "lib/pf/crossborder.py",
                   "Figures are real — today's money — throughout. Tax "
                   "residency consequences of a split-living arrangement need "
                   "a cross-border professional, not a day estimate.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Geo arbitrage model",
                             required=REQUIRED, build=build))
