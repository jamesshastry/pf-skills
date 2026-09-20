#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Tax planning grounded in filed-return history and current facts."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, skill_metrics as M, tax_planning as T  # noqa: E402

REQUIRED = [
    "meta.as_of",
    "meta.currency",
    "meta.jurisdiction.country",
    "household.members",
    "household.balance_sheet",
    "contributions.year",
    "assumptions.marginal_tax_rate",
    "assumptions.state_tax_rate",
    "tax_planning.returns[].tax_year",
    "tax_planning.returns[].adjusted_gross_income",
    "tax_planning.returns[].taxable_income",
    "tax_planning.returns[].federal_total_tax",
    "tax_planning.returns[].state_income_tax",
    "tax_planning.returns[].filing_status",
    "tax_planning.returns[].state",
    "tax_planning.current_year.tax_year",
    "tax_planning.current_year.projected_adjusted_gross_income",
    "tax_planning.current_year.projected_taxable_income",
    "tax_planning.current_year.projected_federal_total_tax",
    "tax_planning.current_year.projected_state_income_tax",
    "tax_planning.current_year.projected_payments",
    "tax_planning.current_year.filing_status",
    "tax_planning.current_year.state",
]

m = cli.money


def _payment(value: float | None) -> str:
    if value is None:
        return "not recorded"
    if value > 0:
        return f"{m(value)} due"
    if value < 0:
        return f"{m(-value)} refund"
    return "settled"


def _current_effect(value: float | None) -> str:
    if value is None:
        return "not sized"
    if value > 0:
        return f"**{m(value)} lower**"
    if value < 0:
        return f"{m(-value)} higher now"
    return "no current change"


def build(data: dict, w: cli.Writer) -> None:
    plan = T.plan_from_facts(data)
    w.add_metrics(M.emit("tax-planning", data))

    w("Filed returns are the baseline; the current row is a projection. "
      "Payments stay separate because a refund or balance due says when tax "
      "was paid, not how much tax the household incurred.")
    w()
    w("## Filed-return history")
    w()
    w.table(
        ["Year", "Filing / state", "AGI", "Taxable", "Federal", "State tax",
         "Combined", "Effective", "Payment result"],
        [[
            row.tax_year,
            f"{row.filing_status} / {row.state}",
            m(row.adjusted_gross_income),
            m(row.taxable_income),
            m(row.federal_total_tax),
            m(row.state_income_tax),
            m(row.combined_tax),
            f"{row.effective_rate:.1%}",
            _payment(row.payment_gap),
        ] for row in plan.history.years],
    )
    w()
    change = plan.history.effective_rate_change
    if change is None:
        w("One filed return cannot establish a trend.")
    else:
        direction = "up" if change > 0 else "down" if change < 0 else "flat"
        w(
            f"Across the recorded period, nominal AGI changed by "
            f"{m(plan.history.agi_change)} and the combined effective rate "
            f"moved {direction} by {abs(change):.1%}. The income-weighted "
            f"historical rate is {plan.history.weighted_effective_rate:.1%}."
        )
    w("That movement is diagnostic, not causal: it does not identify a "
      "deduction, law change, or income-mix effect by itself.")

    current = plan.current
    w()
    w("## Current projection")
    w()
    w.table(["Year", "Filing / state", "AGI", "Taxable", "Combined tax",
             "Effective",
             "Payments", "Projected result"], [[
        current.tax_year,
        f"{current.filing_status} / {current.state}",
        m(current.adjusted_gross_income),
        m(current.taxable_income),
        m(current.combined_tax),
        f"{current.effective_rate:.1%}",
        m(current.payments),
        _payment(current.payment_gap),
    ]])
    for finding in plan.findings:
        w()
        w(f"- {finding}")

    w()
    w("## Tax-reduction candidates")
    w()
    if not plan.opportunities:
        w("No candidate can be sized from the recorded facts. That does not "
          "mean no opportunity exists; it means this screen will not invent "
          "one from a generic checklist.")
    else:
        w.table(
            ["Move", "Amount", "Current-year tax", "Possible later benefit",
             "Confidence", "Detail"],
            [[
                opportunity.action,
                m(opportunity.amount) if opportunity.amount is not None
                else "not sized",
                _current_effect(opportunity.current_tax_savings),
                m(opportunity.future_tax_savings)
                if opportunity.future_tax_savings is not None
                else "not separately sized",
                opportunity.confidence,
                f"`{opportunity.related_skill}`",
            ] for opportunity in plan.opportunities],
        )

        for opportunity in plan.opportunities:
            w()
            w(f"### {opportunity.action}")
            w()
            w(opportunity.reason)
            w()
            w("Tradeoffs:")
            for tradeoff in opportunity.tradeoffs:
                w(f"- {tradeoff}")

    w()
    w("**Do not add the opportunity figures together.** Contribution choices "
      "compete for cash; charitable techniques can overlap; losses depend on "
      "return-level netting; and a conversion deliberately moves tax between "
      "years. Reproject the return after selecting a combination.")
    cli.disclaimer(
        w,
        "lib/pf/tax_planning.py",
        "This is a planning screen, not a prepared return. Verify current "
        "law, eligibility, and filing treatment before acting.",
    )


if __name__ == "__main__":
    raise SystemExit(cli.run(
        title="Tax planning",
        required=REQUIRED,
        build=build,
        skill_id="tax-planning",
    ))
