#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""The checklist to read a California single-family disclosure package against."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, disclosure as D, facts as F  # noqa: E402

REQUIRED = [
    "meta.jurisdiction.state",
    "property_review.property_type",
]


def build(data: dict, w: cli.Writer) -> None:
    # Disclosure law follows the property, not the buyer. A household in one
    # state reviewing a property in another is ordinary, and reading the
    # household's jurisdiction would apply the wrong regime to the documents.
    state = (F._dig(data, "property_review.state")
             or F._dig(data, "meta.jurisdiction.state"))
    ptype = F._dig(data, "property_review.property_type")
    year = F._dig(data, "property_review.year_built")
    provided = F._dig(data, "property_review.documents_provided")

    if state != "CA":
        w(f"**This skill encodes California law only, and the recorded "
          f"jurisdiction is {state}.**")
        w()
        w("Nothing below applies. Disclosure regimes do not transfer between "
          "states — there is no Davis-Stirling analogue in most of them, and "
          "applying a California checklist elsewhere would produce a "
          "confident list of the wrong obligations. Stop here.")
        cli.disclaimer(w, "lib/pf/disclosure.py")
        return

    if D.is_cid(ptype):
        w(f"⚠️ **The recorded property type is `{ptype}`, which sits inside a "
          "common interest development.** Use `ca-condo-hoa-disclosure-review` "
          "instead — on a property with an association the building and the "
          "association are usually the larger risk, and this skill does not "
          "look at either.")
        w()
        w("The California-wide checklist below still applies to the unit, so "
          "it is printed rather than withheld. It is not sufficient on its "
          "own for this property.")
        w()

    w("## How to use this")
    w()
    w("This is the checklist, not the analysis. It says what a California "
      "single-family package must contain and what to look for; reading the "
      "documents against it is the next step, and no part of it is a finding "
      "until a document has been read.")
    w()
    w("Label every claim you make from the documents as **stated** (cite the "
      "document and page), **inferred** (say from what) or **absent**. An "
      "unlabelled assertion cannot be told from a guess, and a guess in a "
      "due-diligence note becomes a decision three steps later.")

    # ── statutory disclosures ───────────────────────────────────────────
    req = D.required_disclosures(property_type=ptype, year_built=year)
    have = {str(x).strip().lower() for x in (provided or [])}
    w()
    w("## Disclosures this property attracts")
    w()
    w.table(["Disclosure", "Authority", "In the package?"],
            [[d.name, f"`{d.authority}`",
              "yes" if d.key in have else "**not seen**"] for d in req])
    w()
    for d in req:
        if d.key not in have:
            w(f"- **{d.name}** — {d.why}")

    unknown_year = D.year_gated_but_unknown(year_built=year)
    if unknown_year:
        w()
        w(f"> **`year_built` is not recorded**, so "
          + ", ".join(f"**{d.name}**" for d in unknown_year)
          + " stays on the list rather than being dropped. Not knowing "
            "whether a house is pre-1978 is a question to ask, not a reason "
            "to stop asking it.")

    # ── standard reports ────────────────────────────────────────────────
    missing = D.missing_reports(provided, property_type=D.SINGLE_FAMILY)
    w()
    w("## Reports a complete package normally contains")
    w()
    if missing:
        w(f"**{len(missing)} not seen.** An absent report is a finding, not "
          "merely a gap in the analysis — a package is not clean because "
          "nobody looked.")
        w()
        for _k, label in missing:
            w(f"- {label}")
    else:
        w("All of the standard reports appear to be present. Check their "
          "**dates** as well: a general inspection over six months old or a "
          "WDO report over ninety days old is weaker evidence than its "
          "presence suggests.")

    # ── what to read for ────────────────────────────────────────────────
    w()
    w("## What to read for")
    w()
    w("**Every `Yes` on the TDS and SPQ**, with the seller's explanation and "
      "whether it is adequate. Look for *patterns* — three separate plumbing "
      "repairs is a different finding from one.")
    w()
    w("**Every blank, vague or `Unknown` answer.** A seller answering "
      "\"unknown\" about their own occupancy is a follow-up, not an answer.")
    w()
    w("**Whether the TDS is exempt.** Trustee sales, probate and some REO "
      "transfers are excused under Civ. Code §1102.2. Silence from an exempt "
      "seller carries far less information than silence from an ordinary one, "
      "and mistaking the two is how a thin package reads as a clean one.")
    w()
    w("**Contradictions between documents.** Build the table even if it comes "
      "back empty — an absent section reads as *not checked*.")
    w()
    w.table(["Topic", "Document A says", "Document B says", "Why it matters"],
            [["", "", "", ""]])
    w()
    w("The ones that recur: TDS \"no water damage\" against inspection "
      "evidence of past leaks; SPQ \"no claims\" against a CLUE report; "
      "claimed upgrades against permit history; a general inspector deferring "
      "to a specialist whose report is not in the package.")

    # ── severity and cost ───────────────────────────────────────────────
    w()
    w("## Grading what you find")
    w()
    w.table(["Severity", "Test"],
            [["**High**", "Safety, habitability, insurability or financing — "
              f"or plausibly above {D.HIGH_SEVERITY_PRICE_SHARE:.0%} of price"],
             ["**Medium**", "Real money, but scheduled rather than a surprise"],
             ["**Low**", "Maintenance, deferred upkeep, cosmetic"]])
    w()
    w("Cost buckets: under $5k · $5–20k · $20–50k · $50k+ · **cannot be "
      "estimated**. Use the last one freely. A figure you cannot defend "
      "carries more weight than an honest gap, because it looks like work.")
    w()
    w("**Insurance is the item most likely to change the deal** and the one "
      "most often left to the end. In a high fire hazard severity zone, get a "
      "**bound quote** rather than an estimate: admitted carriers decline, "
      "and a FAIR Plan policy plus a difference-in-conditions wrapper costs "
      "materially more than the figure in a spreadsheet.")
    w()
    w("**Unpermitted work** is a chain rather than a flag: retroactive "
      "permitting, possible forced removal, appraisal and financing problems "
      "where square footage is not legal, and an insurer declining a claim on "
      "work that was never inspected.")

    w()
    w("## Before removing contingencies")
    w()
    for item in ("A structural engineer where any foundation or framing "
                 "question is open",
                 "A sewer lateral camera scope — cheap, and the failure is "
                 "expensive and invisible",
                 "A licensed roofer's opinion on remaining life, not the "
                 "general inspector's",
                 "A **bound** insurance quote",
                 "Permit history pulled from the jurisdiction rather than "
                 "taken from the listing"):
        w(f"- {item}")

    w()
    w("**Weakest input:** this checklist knows what the package *should* "
      "contain and nothing about what it *says*. Every conclusion still comes "
      "from reading the documents.")
    cli.disclaimer(w, "lib/pf/disclosure.py")


if __name__ == "__main__":
    raise SystemExit(cli.run(
        title="California single-family disclosure review",
        required=REQUIRED, build=build))
