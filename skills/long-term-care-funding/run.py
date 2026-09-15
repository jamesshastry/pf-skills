#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Long-term care: insure what you cannot absorb, measured on the survivor."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, healthcare as H, retirement as R  # noqa: E402

REQUIRED = ["household.members", "household.balance_sheet"]
m = cli.money

VERDICT_LABEL = {
    H.SELF_INSURE: "Self-insure",
    H.PARTIAL: "Partial transfer",
    H.TRANSFER: "Transfer the tail",
    "unknown": "Cannot be determined",
}


def build(data: dict, w: cli.Writer) -> None:
    # Investable = liquid + age_restricted. `illiquid` is excluded: a 529 and a
    # home are on the balance sheet but are not what pays a care bill, and
    # counting them would flatter the absorb test in the direction of inaction.
    investable = F.tier_total(data, F.LIQUID) + F.tier_total(data, F.AGE_RESTRICTED)
    policies = F._dig(data, "healthcare.ltc.policies") or []

    a = H.assess_ltc(
        annual_cost=F._dig(data, "healthcare.ltc.annual_cost_today"),
        cost_as_of=F._dig(data, "healthcare.ltc.cost_as_of"),
        investable_assets=investable,
        survivor_annual_spending=F._dig(
            data, "healthcare.ltc.survivor_annual_spending"),
        has_policy=bool(policies),
        policy_type=(policies[0].get("type") if policies else None),
    )

    w(f"**{VERDICT_LABEL[a.verdict]}.**")
    w()

    if a.annual_cost:
        w.table(["", ""], [
            ["Annual care cost (today's money)", m(a.annual_cost)],
            [f"{H.LTC_PLANNING_YEARS}-year episode", m(a.planning_cost)],
            [f"**{H.LTC_TAIL_YEARS}-year episode**", f"**{m(a.tail_cost)}**"],
            ["Investable assets (liquid + age-restricted)", m(investable)],
            ["Tail as a share of investable",
             f"{a.share_tail:.0%}" if a.share_tail is not None else "—"],
            ["Portfolio after the tail case",
             "**exhausted**" if a.exhausted else m(a.residual_assets)],
            [f"Supports at {R.DEFAULT_WITHDRAWAL_RATE:.1%}",
             m(a.residual_supportable_spending)],
            ["**Survivor shortfall**",
             f"**{m(a.survivor_shortfall)}/yr**"
             if a.survivor_shortfall else
             ("none" if a.survivor_shortfall == 0 else "not computed")],
        ])
        w()

    for f in a.findings:
        w(f"- {f}")
        w()

    w("## The three options, compared on the right axis")
    w()
    w.table(
        ["", "Self-insure", "Traditional LTC", "Hybrid life-LTC"],
        [["Premium certainty", "n/a",
          "**not guaranteed — the known defect**", "usually guaranteed"],
         ["Care benefit per dollar", "1:1 with assets",
          "highest of the three", "lowest of the three"],
         ["If care is never needed", "assets retained",
          "premiums gone", "death benefit paid"],
         ["Capital committed", "none upfront",
          "annual premium", "large single or limited premium"],
         ["Fails when", "the tail runs long",
          "a rate increase arrives at 80", "the opportunity cost compounds"]])
    w()
    w("**Do not compare a hybrid to a traditional policy on premium.** Compare "
      "maximum care benefit per dollar committed, and price what the "
      "committed capital would otherwise have earned — the same arithmetic "
      "`life-insurance-review` applies to cash-value policies.")
    w()

    w("## Before acting")
    w()
    w("- **Ask for the carrier's rate-increase history on in-force business**, "
      "not the illustration. A carrier that has never raised rates on an old "
      "block is telling you something; one that has raised them repeatedly is "
      "telling you more.")
    w("- **Price the increase scenario.** If the premium rose substantially at "
      "the age where dropping the policy wastes everything paid in, would you "
      "still pay it? If not, the policy is not affordable now.")
    w("- **Check inflation protection.** A fixed daily benefit written today "
      "buys a fraction of a care day in thirty years, which is when it is "
      "needed.")
    w("- **Match the benefit period to the tail.** A three-year benefit period "
      "leaves uncovered exactly the scenario that justified buying.")
    w("- **Underwriting is the real gate.** This decision has a health "
      "deadline as well as a cost, the same way "
      "`disability-insurance-review` does — it is cheap and available until "
      "abruptly it is neither.")

    w()
    w("## Weakest input")
    w()
    w(a.weakest_input)
    cli.disclaimer(w, "lib/pf/healthcare.py",
                   "Medicaid spend-down, transfer lookback, community-spouse "
                   "protection and estate recovery are state law and are not "
                   "modelled — this report will not tell you whether a "
                   "transfer is safe.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Long-term care funding",
                             required=REQUIRED, build=build))
