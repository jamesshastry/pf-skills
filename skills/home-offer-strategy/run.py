#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Comparable-sale evidence and a bounded home-offer strategy."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

from pf import cli  # noqa: E402
from pf import home_offer as O  # noqa: E402
from pf import housing_affordability as A  # noqa: E402
from pf import workflows as WF  # noqa: E402

REQUIRED = [
    "meta.as_of", "meta.currency", "meta.jurisdiction.state",
    "household.members",
    "household.balance_sheet", "retirement.annual_savings",
    "cash_flow.scenarios", "housing.monthly_rent", "housing.purchase",
    "housing.affordability", "housing.transition", "housing.offer",
    "property_review.property_type", "property_review.documents_provided",
]
m = cli.money


def signed_money(value: float) -> str:
    if value > 0:
        return f"+{m(value)}"
    if value < 0:
        return f"−{m(abs(value))}"
    return m(0)


def build(data: dict, w: cli.Writer) -> None:
    try:
        result = O.assess_from_facts(data)
    except (O.OfferError, A.ReconciliationError) as exc:
        w(f"## BLOCKED — {exc}")
        w()
        w("No valuation or offer recommendation is produced until the "
          "contradictory or missing fact is resolved. Unknown is not zero.")
        cli.disclaimer(w, "lib/pf/home_offer.py")
        return

    if result.blockers:
        w("## BLOCKED — the evidence or affordability chain is incomplete")
        w()
        for blocker in result.blockers:
            w(f"- {blocker}")
        w()
        w("Comparable evidence is still shown below, but no opening offer or "
          "walk-away price is recommended while a blocker remains.")
    else:
        w(f"**Open at {m(result.opening_offer)} and do not exceed "
          f"{m(result.walk_away_price)}.**")
        w()
        w(f"Posture: **{result.posture}**. The cap is set by "
          f"{', '.join(result.binding_constraints)}.")
    w()
    w("All values are **nominal dollars**. The report uses only supplied, "
      "verified closed sales; it fetches no market data and is not an appraisal.")
    w()

    w("## Subject and evidence")
    w()
    evidence_rows = [
        ["Property", result.subject_label],
        ["List price", m(result.list_price)],
        ["Verified comps passing selection",
         (f"{len(result.usable_comparables)} of {len(result.comparables)} "
          f"(minimum {result.minimum_comparables})")],
        ["Stress-tested affordability ceiling", m(result.affordability_ceiling)],
    ]
    if result.central_value is not None:
        evidence_rows.extend([
            ["Adjusted-value core range",
             f"{m(result.core_low)}–{m(result.core_high)}"],
            ["Median adjusted value", m(result.central_value)],
            ["Full adjusted-value range",
             f"{m(result.observed_low)}–{m(result.observed_high)}"],
        ])
    w.table(["Measure", "Result"], evidence_rows)
    w()

    w("## Comparable adjustments")
    w()
    w.table(
        ["Comp", "Source", "Sold", "Age", "Miles", "Concessions",
         "Adjustments", "Adjusted", "Adj. $/sf", "Gross adj.", "Use"],
        [[comp.label, comp.source, m(comp.sale_price), f"{comp.age_days}d",
          f"{comp.distance_miles:g}", m(comp.sale_price - comp.net_sale_price),
          signed_money(comp.adjustment_total), m(comp.adjusted_price),
          f"${comp.adjusted_price_per_sqft:,.0f}",
          f"{comp.gross_adjustment_rate:.1%}",
          ("included" if comp.included else "excluded: " + "; ".join(comp.reasons))]
         for comp in result.comparables],
    )
    w()
    w("Adjustments are signed from each comparable to the subject. Seller "
      "concessions are removed before adjustments; they are not counted twice.")
    w()

    if result.walk_away_price is not None:
        w("## Offer ladder")
        w()
        rows = [
            ["Competition recorded", result.competition],
            ["Opening posture", result.posture],
            ["Suggested opening", m(result.opening_offer)],
            ["Comparable-evidence ceiling", m(result.value_ceiling)],
            ["Affordability ceiling", m(result.affordability_ceiling)],
        ]
        if result.appraisal_ceiling is not None:
            rows.extend([
                ["Appraisal-gap cash ceiling", m(result.appraisal_ceiling)],
                ["Potential gap above median at cap",
                 m(result.appraisal_gap_at_cap)],
            ])
        rows.extend([
            ["**Walk-away price**", f"**{m(result.walk_away_price)}**"],
            ["Binding constraint", ", ".join(result.binding_constraints)],
        ])
        w.table(["Offer decision", "Amount or state"], rows)
        w()
        w("Treat the walk-away figure as a ceiling, not a target. In a "
          "multiple-offer process, require documentary support before using "
          "an escalation mechanism and never let its cap exceed this figure.")
        w()

    if result.findings:
        w("## Findings")
        w()
        for finding in result.findings:
            w(f"- {finding}")
        w()

    w("## Property evaluation workflow")
    w()
    workflow = WF.PROPERTY_EVALUATION
    w.table(
        ["Stage", "Skills", "Why"],
        [[step.stage,
          " + ".join(
              f"**{skill}**" if skill == "home-offer-strategy" else skill
              for skill in step.skills),
          step.purpose + (
              " " + step.condition if step.condition != "always" else "")]
         for step in workflow.steps],
    )
    w()

    w("## Terms and next checks")
    w()
    w("Comp arithmetic does not price title defects, insurability, deferred "
      "maintenance, HOA exposure, or legal terms. Run the applicable property "
      "disclosure review and keep inspection, financing, appraisal, title, "
      "insurance, and legal protections unless the responsible professionals "
      "have separately priced the risk. Use `conflict-check` and a housing "
      "scenario before committing material cash or changing the debt plan.")
    w()
    w("**Weakest input:** the adjustment ledger. Generic dollars per square "
      "foot or an agent-selected comp set can make exact arithmetic support a "
      "false conclusion.")
    cli.disclaimer(w, "lib/pf/home_offer.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(
        title="Home offer strategy", required=REQUIRED, build=build))
