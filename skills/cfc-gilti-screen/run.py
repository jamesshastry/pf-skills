#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Does a CFC exist, which forms follow, and what does ignoring them cost."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, expat as X, facts as F  # noqa: E402

REQUIRED = ["expat.foreign_entities"]
m = cli.money
VERDICT = {True: "🚫 **CFC**", False: "✅ not a CFC",
           None: "· **cannot be determined**"}


def verdict(e) -> str:
    """A partnership is not an undetermined corporation; say which it is."""
    if e.kind in X.OTHER_FORMS:
        return "— outside the CFC rules"
    return VERDICT[e.is_cfc]


def build(data: dict, w: cli.Writer) -> None:
    s = X.cfc_screen(F._dig(data, "expat.foreign_entities"))

    w("**This is a screen, not a calculator.** It establishes whether a "
      "controlled foreign corporation exists, names the filings that follow, "
      "and prices the penalty for missing them. It does **not** compute a "
      "GILTI inclusion and it does **not** model a §962 election — the "
      "findings below say why that refusal is the point rather than a gap.")
    w()
    w.table(["Test", "Threshold"], [
        ["US shareholder", f"a US person owning **{X.US_SHAREHOLDER_PCT}% or "
         "more** of vote **or** value"],
        ["Controlled foreign corporation",
         f"US shareholders together owning **more than "
         f"{X.CFC_CONTROL_PCT}%** of vote or value, on any day of the year "
         f"(or for {X.CONTROL_PERIOD_DAYS} uninterrupted days)"],
    ])
    w()
    w("Both are required. *More than* 50%, not 50% — an even split is the "
      "case people assume is caught, and it is not.")
    w()

    if s.entities:
        w("## Entities")
        w()
        w.table(["Entity", "Country", "Kind", "Your %", "US shareholders %",
                 "Verdict"],
                [[e.name, e.country or "—", e.kind.replace("_", " "),
                  "—" if e.ownership_pct is None else f"{e.ownership_pct:g}%",
                  "—" if e.us_shareholder_pct is None
                  else f"{e.us_shareholder_pct:g}%",
                  verdict(e)] for e in s.entities])
        w()
        for e in s.entities:
            w(f"**{e.name}**")
            w()
            for f in e.findings:
                w(f"- {f}")
            if e.forms:
                w(f"- Filings that follow: "
                  + ", ".join(f"**{x}**" for x in e.forms) + ".")
            w()

    w("## Findings")
    w()
    for f in s.findings:
        w(f"- {f}")
        w()

    if s.any_cfc or s.any_undetermined:
        w("## The forms, and what they cost to miss")
        w()
        w.table(["Form", "Who files", "Penalty for not filing"], [
            ["**5471**", "US shareholders and officers/directors of a foreign "
             "corporation — categories 1 through 5",
             f"{m(X.FORM_5471_PENALTY)} per form per year, plus the same "
             f"again per 30 days after notice up to "
             f"{m(X.FORM_5471_CONTINUATION_CAP)}, plus a 10% cut in foreign "
             "tax credits"],
            ["**8992**", "US shareholders of a CFC, computing the GILTI "
             "inclusion", "flows through the return; the inclusion itself is "
             "the exposure"],
            ["**8865**", "US persons with a controlling or 10%-plus interest "
             "in a foreign partnership",
             f"{m(X.FORM_5471_PENALTY)}-scale, on the same pattern"],
            ["**8858**", "owners of a foreign disregarded entity or branch — "
             "including a single-member foreign LLC and an unincorporated "
             "business run abroad",
             f"{m(X.FORM_5471_PENALTY)}-scale, and the one people have never "
             "heard of"],
        ])
        w()
        w("If years are already missed, **do not simply start filing.** The "
          "remediation path differs sharply depending on whether the failure "
          "was non-wilful, and choosing it is the first conversation to have "
          "with a cross-border CPA or EA — before anything is filed, not "
          "after.")
        w()

    w("## Weakest input")
    w()
    w("**Weakest input:** the ownership percentages. They are direct holdings "
      "as recorded, and attribution rules treat shares held by a spouse, "
      "children, parents, partnerships and trusts as yours — so the real "
      "figure is at least as high as the one above and frequently higher. A "
      "family company where no individual holds a majority is the ordinary "
      "case, not an edge case.")
    cli.disclaimer(w, "lib/pf/expat.py",
                   "This is a screen. Every path out of it ends at a "
                   "cross-border CPA or EA.")


if __name__ == "__main__":
    raise SystemExit(cli.run(title="CFC and GILTI screen",
                             required=REQUIRED, build=build))
