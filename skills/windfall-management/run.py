#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Windfall management — the pause first, then the tax character."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, transitions as T  # noqa: E402

REQUIRED = ["transitions.windfall"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    events = F._dig(data, "transitions.windfall") or []
    bs = F._dig(data, "household.balance_sheet") or []

    # A row flagged `new_from_windfall` with no designation recorded. Absent
    # is absent — `beneficiaries: []` means somebody looked and found none,
    # which is a different finding and belongs to `beneficiary-audit`.
    naked = [r.get("name", "?") for r in bs
             if r.get("new_from_windfall")
             and r.get("beneficiary_applicable") is not False
             and r.get("beneficiaries") is None]

    plan = T.assess_windfall(
        events,
        as_of=F.as_of(data),
        marginal_rate=F._dig(data, "assumptions.marginal_tax_rate"),
        withheld=F._dig(data, "transitions.tax_withheld_ytd"),
        prior_year_tax=F._dig(data, "transitions.prior_year_tax"),
        prior_year_agi=F._dig(data, "transitions.prior_year_agi"),
        aca_marketplace_coverage=F._dig(data, "transitions.aca_marketplace_coverage"),
        medicare_within_lookback=F._dig(data, "transitions.medicare_within_lookback"),
        new_accounts_without_beneficiaries=naked,
    )

    pause = [f for f in plan.findings if f.area == "pause"]
    if pause and pause[0].severity == "blocker":
        w("## Do nothing for ninety days")
    elif pause and pause[0].severity == "ok":
        w("## The pause has elapsed")
    else:
        w("## The pause, first")
    w()
    for f in pause:
        w(f.detail)
        w()

    w(f"**{m(plan.total)}** across {len(plan.events)} event(s).")
    w()
    w.table(
        ["Event", "Amount", "Kind", "Income on receipt?", "Basis", "Pause"],
        [[e.label, m(e.amount), f"`{e.kind}`",
          ("**unknown**" if not e.character.known else
           {True: "yes", False: "no", None: "depends"}[
               e.character.income_on_receipt]),
          e.character.basis_rule.replace("_", " "),
          ("not recorded" if e.pause_days_remaining is None
           else "elapsed" if e.pause_elapsed
           else f"**{e.pause_days_remaining}d left**")]
         for e in plan.events])
    w()

    if plan.estimated_tax is not None:
        w.table(
            ["", "Amount"],
            [["Taxable on receipt", m(plan.taxable_amount)],
             ["Estimated federal tax", m(plan.estimated_tax)],
             ["Withheld", m(plan.withheld) if plan.withheld is not None
              else "not recorded"],
             ["Shortfall", m(plan.shortfall) if plan.shortfall is not None
              else "cannot be determined"],
             ["Prior-year safe harbour",
              m(plan.safe_harbor) if plan.safe_harbor is not None
              else "cannot be determined"]])
        w()

    for heading, areas in (("Tax character", ("character",)),
                           ("Tax and withholding",
                            ("estimated tax", "withholding")),
                           ("Where it sits meanwhile", ("parking",)),
                           ("Reporting", ("reporting",)),
                           ("Beneficiaries", ("beneficiaries",)),
                           ("The two-year echo", ("irmaa", "aca"))):
        rows = T._sorted([f for f in plan.findings if f.area in areas])
        if not rows:
            continue
        w(f"## {heading}")
        w()
        for f in rows:
            w(f"- {'⚠️ ' if f.severity == 'blocker' else ''}{f.detail}")
            w()

    w("## The weakest input")
    w()
    w("**`kind`.** Everything above is downstream of it, and it is the one "
      "field a user fills in from memory rather than from a document. An "
      "inheritance that is actually an inherited IRA, or a settlement "
      "recorded without its allocation, produces a confident answer that is "
      "wrong by the whole tax bill.")
    w()
    w("## What this will not do")
    w()
    w("- **Tell you what to buy.** That is the next conversation, after the "
      "ninety days, and it is `portfolio` work rather than transition work.")
    w("- **Compute state tax, NIIT, or the bracket this pushes you into.** "
      "Every figure here is federal, nominal, and a floor.")
    w("- **Characterise a settlement.** That needs the allocation in the "
      "agreement, and no amount of arithmetic substitutes for it.")
    cli.disclaimer(w, "lib/pf/transitions.py",
                   "The tax-character table is transcribed statute, marked "
                   "unverified — check it before relying on it.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Windfall management", required=REQUIRED,
                             build=build))
