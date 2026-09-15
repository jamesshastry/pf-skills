#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Divorce asset split — the after-tax value of what is being divided."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, facts as F, transitions as T  # noqa: E402

REQUIRED = ["transitions.divorce"]
m = cli.money


def build(data: dict, w: cli.Writer) -> None:
    div = F._dig(data, "transitions.divorce") or {}
    labels = tuple(div.get("parties") or ("a", "b"))

    w("## Scope, before anything else")
    w()
    w("**This needs a family-law attorney.** A divorce is substantially a "
      "legal process, and this skill covers exactly one part of it: **the tax "
      "character of what is being divided.** It does not value a business, "
      "compute support, touch anything involving children, or take a side. "
      "Nothing below is a negotiating position — it is arithmetic that both "
      "sides' lawyers can check.")
    w()

    s = T.split_assets(
        div.get("assets") or [],
        ordinary_rate=F._dig(data, "assumptions.marginal_tax_rate"),
        capital_gains_rate=F._dig(data, "assumptions.capital_gains_rate"),
        party_labels=labels,
    )

    if not s.lines:
        for f in s.findings:
            w(f"⚠️ {f.detail}")
            w()
        cli.disclaimer(w, "lib/pf/transitions.py")
        return

    w("## A dollar is not a dollar")
    w()
    w.table(
        ["Asset", "To", "Kind", "Statement value", "Embedded gain",
         "After tax", "Moves by"],
        [[l.name, l.to or "**unassigned**", f"`{l.kind}`", m(l.nominal),
          m(l.embedded_gain) if l.embedded_gain is not None else "—",
          m(l.after_tax) if l.after_tax is not None
          else "**cannot be determined**",
          l.mechanism.instrument if l.mechanism.known else "**unknown**"]
         for l in s.lines])
    w()
    w.table(
        [""] + [f"`{p}`" for p in labels] + ["Gap"],
        [["Statement value"] + [m(s.nominal_by_party.get(p, 0)) for p in labels]
         + [m(s.nominal_gap)],
         ["**After tax**"]
         + [f"**{m(s.after_tax_by_party.get(p, 0))}**" for p in labels]
         + [f"**{m(s.after_tax_gap)}**"]])
    w()
    if not s.complete:
        w(f"⚠️ **{m(s.undetermined)} could not be valued after tax**, so the "
          "after-tax row is incomplete and the gap is understated by an "
          "unknown amount.")
        w()

    for heading, areas in (("What the split is really worth", ("split",)),
                           ("How each account may be divided", ("mechanism",)),
                           ("Beneficiaries", ("beneficiaries",)),
                           ("Scope", ("scope",))):
        rows = T._sorted([f for f in s.findings if f.area in areas])
        if not rows:
            continue
        w(f"## {heading}")
        w()
        for f in rows:
            w(f"- {'⚠️ ' if f.severity == 'blocker' else ''}{f.detail}")
            w()

    w("## The weakest input")
    w()
    w("**The rates.** The after-tax column uses the rates in your facts file, "
      "and the ones that matter are the **post-divorce** rates — single or "
      "head of household, on one income — not the joint rates on last year's "
      "return. They also differ between the two parties, and this report "
      "applies one pair to both. Treat the gap as an order of magnitude that "
      "shows the direction, not as a settlement figure.")
    w()
    w("## What this will not do")
    w()
    w("- **Value a business, a pension's present value, a professional "
      "practice, or a house net of selling costs.** Those are appraisals, and "
      "a wrong one here would be worse than none.")
    w("- **Compute support, or anything linked to custody.** Out of scope, "
      "permanently.")
    w("- **Advise on strategy, or on what a fair division would be.** "
      "'Equitable' is a legal standard applied by a court to facts this skill "
      "does not have, and it is not the same as equal.")
    w("- **Replace a QDRO drafted for the plan.** The mechanism notes above "
      "say what instrument is required; they are not the instrument.")
    cli.disclaimer(w, "lib/pf/transitions.py",
                   "The mechanism table is transcribed statute, marked "
                   "unverified. Confirm every item with counsel before "
                   "acting — several of these steps cannot be undone.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="Divorce asset split", required=REQUIRED,
                             build=build))
