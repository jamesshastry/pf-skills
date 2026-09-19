#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Opinionated correlated job-loss wrapper over the scenario engine."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, scenario as S  # noqa: E402

REQUIRED = [
    "meta.as_of", "meta.currency", "household.members",
    "household.balance_sheet", "household.annual_spending",
    "debts",
    "cash_flow.scenarios", "housing.status", "housing.monthly_rent",
    "retirement.annual_savings", "equity_comp",
    "equity_comp.held_value_in_balance_sheet",
    "scenario_planning.scenarios",
]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    results = [r for r in S.run_from_facts(data)
               if any(e.type == "employment_loss" for e in r.spec.events)]
    w.add_metrics(metric for result in results for metric in result.metrics)
    if not results:
        w("No `employment_loss` scenario is recorded. Nothing was inferred.")
        cli.disclaimer(w, "lib/pf/scenario.py")
        return

    for result in results:
        losses = [event for event in result.spec.events
                  if event.type == "employment_loss"]
        w(f"## {result.spec.label}")
        w()
        current, essential = S.current_and_essential_runway(result)
        w.table(["Runway view", "Months", "What it assumes"], [
            ["Current spending", f"{current:.1f}", "No immediate spending cut"],
            ["Essential spending",
             f"{essential:.1f}" if essential is not None else "**unknown**",
             "Comparison only unless a spending-change event records it"],
        ])
        w()
        w.table(["Liquidity test", "Result"], [
            ["Opening cash", m(result.baseline.cash)],
            ["Emergency-fund floor", m(result.baseline.emergency_floor)],
            ["Minimum cash", f"**{m(result.minimum_cash)} in month "
                             f"{result.minimum_cash_month}**"],
            ["Months below reserve", str(result.months_below_floor)],
            ["Liquidity verdict", "**passes**" if result.liquidity_passes
             else "**fails before terminal recovery**"],
        ])
        w()
        w("### Correlated event bundle")
        w()
        w.table(
            ["Event", "Person", "Duration", "Income loss / mo", "Severance",
             "Benefits / mo", "Health / mo", "Unvested lost", "Stock change"],
            [[f"`{event.id}`", event.person_id or "**unknown**",
              (str(event.duration_months) if event.duration_months is not None
               else "**unknown/permanent**"),
              m(event.after_tax_income_loss_monthly), m(event.severance_after_tax),
              m(event.unemployment_after_tax_monthly),
              m(event.replacement_health_cost_monthly),
              m(event.unvested_forfeiture),
              (f"{event.employer_stock_change:.0%}"
               if event.employer_stock_change is not None else "**unknown**")]
             for event in losses],
        )
        unknowns = [item for event in losses for item in event.unknown_fields]
        if unknowns:
            w()
            w("**Unknown rather than zero:** " + ", ".join(
                f"`{item}`" for item in sorted(set(unknowns))) + ".")
        w()
        if result.spec.liquidation_order:
            w("Explicit liquidation order (the engine still sells only through "
              "a recorded withdrawal event): " + " → ".join(
                  f"`{item}`" for item in result.spec.liquidation_order) + ".")
        else:
            w("**Liquidation order is unknown.** No asset is sold automatically.")
        temporary = [event for event in losses if event.end_month is not None]
        if temporary:
            recovery_month = max(event.end_month for event in temporary) + 1
            w(f"Recorded employment-loss recovery begins in month "
              f"**{recovery_month}**; any lower ongoing pay must be a separate "
              "`compensation_change` event.")
        w()
        w(f"Annual saving during the shock: "
          f"**{m(result.annual_savings_during_shock)}**; after recovery: "
          f"**{m(result.annual_savings_after_recovery)}**. Binding constraint: "
          f"**{result.binding_constraint}**.")
        w()
        w("Recovery conditions:")
        for condition in result.recovery_conditions:
            w(f"- {condition}")
    cli.disclaimer(w, "lib/pf/scenario.py",
                   "This is an adverse deterministic stress, not a forecast.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Job-loss stress test",
                             required=REQUIRED, build=build,
                             skill_id="job-loss-stress-test"))
