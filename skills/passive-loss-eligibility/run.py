#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""The §469 gate — can these losses reach W-2 income at all? Runs first."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, realestate as R  # noqa: E402

REQUIRED = ["real_estate.activities", "real_estate.participation.magi"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    p = F._dig(data, "real_estate.participation") or {}
    g = R.assess_gate(
        F._dig(data, "real_estate.activities") or [],
        magi=float(p.get("magi")),
        active_participation=p.get("active_participation"),
        hours_real_property=p.get("hours_real_property"),
        hours_all_work=p.get("hours_all_work"),
        grouping_election=bool(p.get("grouping_election")),
        allowance=F._dig(data, "assumptions.passive_loss_allowance"),
        phaseout_start=F._dig(data, "assumptions.passive_loss_phaseout_start"),
        phaseout_end=F._dig(data, "assumptions.passive_loss_phaseout_end"),
    )

    opened = [a for a in g.activities if a.open]
    if opened:
        w(f"**A door is open on {len(opened)} of {len(g.activities)} "
          f"activities.** "
          + ", ".join(f"{a.label} (via {a.door.replace('_', '-')})"
                      for a in opened)
          + ".")
    else:
        w("**No door is open.** Every rental loss below is passive and cannot "
          "offset wage income this year.")
    w()
    w("Run this before `rental-deal-underwriting` and "
      "`cost-segregation-screen`. An after-tax return quoted behind a shut "
      "gate is wrong, not conservative.")
    w()

    w.table(
        ["Activity", "Avg stay", "Rental activity?", "Material participation",
         "Door", "Deductible now", "Suspends"],
        [[a.label,
          "—" if a.avg_stay_days is None else f"{a.avg_stay_days:.1f}d",
          "unknown" if a.is_rental_activity is None
          else ("yes" if a.is_rental_activity else "**no** — short-stay"),
          "unknown" if a.materially_participates is None
          else ("yes" if a.materially_participates else "no"),
          f"**{a.door.replace('_', '-')}**" if a.door else "**shut**",
          m(a.deductible_against_wages),
          m((a.suspended_this_year or 0.0) + a.suspended_carryforward)]
         for a in g.activities])
    w()

    w("## The three doors")
    w()
    for f in g.findings:
        w(f"- {f}")
        w()

    w("## Per activity")
    w()
    for a in g.activities:
        w(f"### {a.label}")
        w()
        for f in a.findings:
            w(f"- {f}")
        w()

    w("## Before relying on this")
    w()
    w("- **Start the participation log today.** Dates, hours, description, "
      "kept as you go. An undocumented 750 hours is not 750 hours, and a log "
      "written after the notice arrives has been rejected repeatedly in Tax "
      "Court.")
    w("- **Recompute the average stay from the booking data** — total rental "
      "days divided by number of bookings. One long winter booking can push a "
      "four-day average over seven and close the only open door.")
    w("- **Count the cleaner's hours.** On a short-stay property they "
      "routinely exceed the owner's, and the 100-hour test requires more than "
      "*any* other individual.")
    w("- **§465 at-risk limits apply first**, and are not modelled here.")
    cli.disclaimer(
        w, "lib/pf/realestate.py",
        "The allowance and its phase-out band come from your facts file, not "
        "from a table in this library — see REVIEW.md A3. REPS is among the "
        "most heavily audited positions in the individual code; take it with "
        "a professional who signs the return.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Passive loss eligibility (§469 gate)",
                             required=REQUIRED, build=build))
