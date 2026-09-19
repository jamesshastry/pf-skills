#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""General baseline-versus-scenario comparison on a monthly cash path."""
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
    "retirement.annual_savings", "scenario_planning.scenarios",
]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    results = S.run_from_facts(data)
    w.add_metrics(metric for result in results for metric in result.metrics)
    objectives = {result.spec.objective for result in results}
    objective = next(iter(objectives)) if len(objectives) == 1 else None
    ranked = S.rank_results(results, objective)

    w("Every row is a **deterministic projection**, not a fact or probability. "
      "The unchanged baseline runs through the identical monthly engine.")
    w()
    if objective in (None, "compare_only"):
        w("**No ranking.** No single objective was recorded; the table presents "
          "tradeoffs without inventing what the household values.")
    else:
        w(f"Ranked for `{objective}`. Best on that one objective: "
          f"**{ranked[0].spec.label}**.")
    w()
    w.table(
        ["Scenario", "Min cash", "When", "Months below reserve",
         "Terminal cash Δ", "Terminal net-worth Δ", "Post-recovery saving",
         "Retirement target age", "Binding"],
        [[r.spec.label, m(r.minimum_cash), f"month {r.minimum_cash_month}",
          r.months_below_floor, m(r.terminal_liquidity_change),
          m(r.terminal_net_worth_change),
          f"{m(r.annual_savings_after_recovery)}/yr",
          (f"{r.retirement_age_at_target:.0f}"
           if r.retirement_age_at_target is not None else "**not reached**"),
          r.binding_constraint]
         for r in ranked],
    )

    for result in results:
        w()
        w(f"## {result.spec.label}")
        w()
        w.table(["Baseline", "Scenario", "Difference"], [[
            f"Terminal cash {m(result.baseline_path[-1].closing_cash)}",
            f"Terminal cash {m(result.monthly_path[-1].closing_cash)}",
            m(result.terminal_liquidity_change),
        ], [
            f"Terminal net worth {m(result.baseline_path[-1].net_worth)}",
            f"Terminal net worth {m(result.monthly_path[-1].net_worth)}",
            m(result.terminal_net_worth_change),
        ], [
            f"Reserve floor {m(result.baseline.emergency_floor)}",
            f"Minimum {m(result.minimum_cash)} in month {result.minimum_cash_month}",
            f"{result.months_below_floor} month(s) below",
        ]])
        w()
        w("### Event bridge")
        w()
        w.table(
            ["Event", "Isolated cash effect", "Isolated net-worth effect", "Basis"],
            [[f"`{item.event_id}`", m(item.cash_change),
              m(item.net_worth_change), item.note] for item in result.bridge],
        )
        bridge_cash = sum(item.cash_change for item in result.bridge)
        bridge_worth = sum(item.net_worth_change for item in result.bridge)
        w(f"Composition residual: cash **{m(result.terminal_liquidity_change - bridge_cash)}**; "
          f"net worth **{m(result.terminal_net_worth_change - bridge_worth)}**. "
          "It is retained rather than forced into an event when effects overlap.")
        w()
        w("### Months that decide the result")
        w()
        key_months = {1, result.minimum_cash_month, result.spec.horizon_months}
        key_months.update(event.start_month for event in result.spec.events)
        w.table(
            ["Month", "Cash", "Marketable", "Employer stock", "Retirement",
             "Debt", "Net worth", "Events"],
            [[row.month, m(row.closing_cash), m(row.marketable),
              m(row.employer_stock), m(row.retirement), m(row.debt), m(row.net_worth),
              ", ".join(row.event_ids) or "—"]
             for row in result.monthly_path if row.month in key_months],
        )
        if result.unknowns:
            w()
            w("Unknown inputs retained: " + ", ".join(
                f"`{item}`" for item in result.unknowns) + ".")
        w()
        w("Recovery conditions:")
        for condition in result.recovery_conditions:
            w(f"- {condition}")

    cli.disclaimer(w, "lib/pf/scenario.py",
                   "No scenario is written back into the household facts.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Financial scenario planner",
                             required=REQUIRED, build=build,
                             skill_id="financial-scenario-planner"))
