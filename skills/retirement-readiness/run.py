#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Retirement readiness — a range, deliberately, not a date."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, retirement as R, skill_metrics as SM  # noqa: E402

REQUIRED = ["household.members", "household.annual_spending",
            "household.balance_sheet", "retirement.annual_savings"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    members = F._dig(data, "household.members") or []
    primary = next((x for x in members if x.get("role") == "primary"), {})
    spending = float(F._dig(data, "household.annual_spending"))
    savings = float(F._dig(data, "retirement.annual_savings"))
    classified = F.retirement_assets(data)
    assets = classified.included
    age = primary.get("age")
    current_cash_flow = next(
        (s for s in (F._dig(data, "cash_flow.scenarios") or [])
         if s.get("kind") == "current"), {})
    try:
        savings_path = R.savings_path_from_obligations(
            savings, current_cash_flow.get("obligations") or [])
    except ValueError as exc:
        w(f"## BLOCKED — {exc}")
        w()
        w("A nominal future obligation cannot enter this real, today's-money "
          "projection. Correct the basis instead of mixing units.")
        cli.disclaimer(w, "lib/pf/retirement.py")
        return

    r = R.assess_readiness(annual_spending=spending, assets=assets,
                           annual_savings=savings, current_age=age,
                           savings_by_year=savings_path)
    grid = R.sensitivity(annual_spending=spending, assets=assets,
                         annual_savings=savings, current_age=age,
                         savings_by_year=savings_path)
    w.add_metrics(SM.emit("retirement-readiness", data))

    if r.already_there:
        w(f"✅ **Assets already exceed the {r.withdrawal_rate:.1%} target of "
          f"{m(r.target)}.**")
    elif r.years_to_target is not None:
        w(f"At the central assumptions — {r.withdrawal_rate:.1%} withdrawal, "
          f"{r.real_return:.0%} real return — the target of **{m(r.target)}** "
          f"is reached in **{r.years_to_target:.0f} years**"
          + (f", at age **{r.age_at_target:.0f}**." if r.age_at_target else "."))
    w()
    w.table(["", ""], [
        ["Annual spending", m(spending)],
        ["Retirement-eligible assets", m(assets)],
        ["Annual savings (current baseline)", m(savings)],
    ])
    if classified.unknown:
        w()
        w("⚠️ **Unclassified assets are excluded:** "
          + ", ".join(classified.unknown)
          + ". Add `retirement_eligible: true|false`; total net worth is not "
            "a retirement portfolio.")
    if classified.excluded:
        w()
        w(f"Explicitly excluded or unclassified assets: {m(classified.excluded)}.")

    w()
    w("## The answer is the spread, not the middle")
    w()
    header = ["Withdrawal rate", "Target"] + [f"{rr:.0%} real" for rr in R.REAL_RETURN_SCENARIOS]
    rows = []
    for row in grid:
        cells = [f"**{row['withdrawal_rate']:.1%}**", m(row["target"])]
        for rr in R.REAL_RETURN_SCENARIOS:
            cell = row[rr]
            cells.append(f"age {cell['age']:.0f}" if cell["age"] is not None
                         else (f"{cell['years']:.0f} yrs" if cell["years"] is not None
                               else "not reached"))
        rows.append(cells)
    w.table(header, rows)
    w()
    ages = [row[rr]["age"] for row in grid for rr in R.REAL_RETURN_SCENARIOS
            if row[rr]["age"] is not None]
    if ages:
        w(f"**The plausible range is age {min(ages):.0f} to {max(ages):.0f}.** "
          "Quoting the middle cell as *the* answer would imply a precision "
          "this cannot support — a half-point change in either assumption "
          "moves the date by years.")

    w()
    w("## Caveats that matter more than the arithmetic")
    w()
    for f in r.findings:
        w(f"- {f}")
    w()
    w("- **Spending is the strongest lever, and it works twice.** A dollar "
      "less of annual spending cuts the target by 20–29× *and* raises "
      "savings. Nothing on the return side comes close.")
    w("- **The withdrawal rate is a rule of thumb, not a law.** It came from "
      "historical sequences over a fixed horizon. Longer retirements, "
      "different asset mixes and different fee levels all move it.")
    cli.disclaimer(w, "lib/pf/retirement.py",
                   "Deterministic projection — for distributions, use a "
                   "dedicated Monte Carlo tool.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Retirement readiness", required=REQUIRED,
                             build=build, skill_id="retirement-readiness"))
