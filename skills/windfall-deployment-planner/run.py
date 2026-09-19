#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Compare deployment choices after windfall character and tax reserves."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, scenario as S, transitions as T  # noqa: E402

REQUIRED = [
    "meta.as_of", "meta.currency", "household.members",
    "household.balance_sheet", "household.annual_spending",
    "debts",
    "cash_flow.scenarios", "housing.status", "housing.monthly_rent",
    "retirement.annual_savings", "transitions.windfall",
    "scenario_planning.scenarios",
]
m = cli.money


def _windfall_plan(data: dict) -> T.WindfallPlan:
    rows = F._dig(data, "household.balance_sheet") or []
    naked = [row.get("name", "?") for row in rows
             if row.get("new_from_windfall")
             and row.get("beneficiary_applicable") is not False
             and row.get("beneficiaries") is None]
    return T.assess_windfall(
        F._dig(data, "transitions.windfall") or [], as_of=F.as_of(data),
        marginal_rate=F._dig(data, "assumptions.marginal_tax_rate"),
        withheld=F._dig(data, "transitions.tax_withheld_ytd"),
        prior_year_tax=F._dig(data, "transitions.prior_year_tax"),
        prior_year_agi=F._dig(data, "transitions.prior_year_agi"),
        aca_marketplace_coverage=F._dig(
            data, "transitions.aca_marketplace_coverage"),
        medicare_within_lookback=F._dig(
            data, "transitions.medicare_within_lookback"),
        new_accounts_without_beneficiaries=naked,
    )


def build(data: dict, w: cli.Writer) -> None:
    plan = _windfall_plan(data)
    results = [result for result in S.run_from_facts(data)
               if any(event.type in ("cash_receipt", "asset_receipt")
                      for event in result.spec.events)]
    w.add_metrics(metric for result in results for metric in result.metrics)
    if not results:
        w("No cash- or asset-receipt scenario is recorded. Nothing was inferred.")
        cli.disclaimer(w, "lib/pf/scenario.py and lib/pf/transitions.py")
        return

    live_pause = plan.any_pause_live
    link_errors = {result.spec.id: S.windfall_link_errors(result.spec, plan.events)
                   for result in results}
    blocked = [result for result in results
               if (live_pause and not result.spec.preliminary)
               or link_errors[result.spec.id]]
    runnable = [result for result in results if result not in blocked]
    if live_pause:
        w("## Decision pause")
        w()
        w(f"`windfall-management` reports a live {T.DECISION_PAUSE_DAYS}-day "
          "pause. Non-preliminary deployment cases are blocked.")
        if blocked:
            w("Blocked: " + ", ".join(f"**{r.spec.label}**" for r in blocked) + ".")
        if runnable:
            w("The remaining cases are explicitly **preliminary**; they are "
              "planning comparisons, not permission to act.")
    for result in blocked:
        for error in link_errors[result.spec.id]:
            w(f"- **{result.spec.label}:** {error}")

    if runnable:
        w()
        w("## Deployment comparison")
        w()
        w.table(
            ["Case", "Receipt form", "Spendable receipt", "Min cash",
             "Terminal cash Δ", "Terminal net-worth Δ", "Binding"],
            [[result.spec.label,
              ", ".join(event.type.replace("_", " ")
                        for event in result.spec.events
                        if event.type in ("cash_receipt", "asset_receipt")),
              "; ".join(
                  (m(net) if net is not None else f"**not cash:** {reason}")
                  for net, reason in (S.windfall_net_amount(event)
                                      for event in result.spec.events
                                      if event.type in ("cash_receipt", "asset_receipt"))),
              m(result.minimum_cash), m(result.terminal_liquidity_change),
              m(result.terminal_net_worth_change), result.binding_constraint]
             for result in runnable],
        )
        unknowns = sorted({item for result in runnable for item in result.unknowns})
        if unknowns:
            w()
            w("**Unknown rather than zero:** " + ", ".join(
                f"`{item}`" for item in unknowns) + ".")

    w()
    w("## Tax and basis boundary")
    w()
    w.table(["Recorded windfall", "Gross amount", "Tax character", "Basis rule", "Pause"],
            [[event.label, m(event.amount),
              ("unknown" if not event.character.known else
               "income" if event.character.income_on_receipt else "not income"),
              event.character.basis_rule.replace("_", " "),
              ("unknown" if event.pause_elapsed is None else
               "elapsed" if event.pause_elapsed else "**live**")]
             for event in plan.events])
    w()
    w("The scenario engine reserves only taxes explicitly supplied in the "
      "scenario. State tax, NIIT, AMT, holding period and transaction costs "
      "remain missing unless recorded; no effective rate is inferred.")
    cli.disclaimer(w, "lib/pf/scenario.py and lib/pf/transitions.py",
                   "This comparison cannot execute any deployment.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Windfall deployment planner",
                             required=REQUIRED, build=build,
                             skill_id="windfall-deployment-planner"))
