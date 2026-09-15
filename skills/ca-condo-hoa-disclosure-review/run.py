#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""The checklist for a California condo package — the association, mostly."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from pf import cli, disclosure as D, facts as F  # noqa: E402

REQUIRED = [
    "meta.jurisdiction.state",
    "property_review.property_type",
    "property_review.hoa",
]
SEV = {"high": "🚫 **high**", "medium": "⚠️ medium", "note": "· note"}


def build(data: dict, w: cli.Writer) -> None:
    # Disclosure law follows the property, not the buyer. A household in one
    # state reviewing a property in another is ordinary, and reading the
    # household's jurisdiction would apply the wrong regime to the documents.
    state = (F._dig(data, "property_review.state")
             or F._dig(data, "meta.jurisdiction.state"))
    ptype = F._dig(data, "property_review.property_type")
    year = F._dig(data, "property_review.year_built")
    units = F._dig(data, "property_review.unit_count")
    elevated = F._dig(data, "property_review.elevated_elements")
    provided = F._dig(data, "property_review.documents_provided")
    hoa = F._dig(data, "property_review.hoa") or {}

    if state != "CA":
        w(f"**This skill encodes California law only, and the recorded "
          f"jurisdiction is {state}.** Davis-Stirling has no analogue in most "
          "states; applying it elsewhere would produce a confident list of "
          "the wrong obligations. Stop here.")
        cli.disclaimer(w, "lib/pf/disclosure.py")
        return

    if not D.is_cid(ptype):
        w(f"**The recorded property type is `{ptype}`, which has no "
          "association.** Use `ca-sfh-disclosure-review`. Everything below "
          "assumes a common interest development and would invent obligations "
          "that do not exist here.")
        cli.disclaimer(w, "lib/pf/disclosure.py")
        return

    w("**On a condo the unit is rarely what hurts you — the building and the "
      "association are.** A flawless unit in an association with weak reserves "
      "and an unbudgeted structural inspection is a worse purchase than a "
      "tired unit in a well-run building, and only one of those two facts is "
      "visible on a walkthrough.")
    w()
    w("This is the checklist, not the analysis. Label every claim you make "
      "from the documents as **stated** (cite the document, page or meeting "
      "date), **inferred** (say from what), or **absent**.")

    # ── the §4525 packet ────────────────────────────────────────────────
    packet_missing = D.missing_packet_items(hoa.get("packet_provided"))
    w()
    w("## The §4525 transfer packet")
    w()
    w("Civ. Code §4525 defines exactly what the seller must hand over. "
      "Because the list is statutory, **a missing item is a finding rather "
      "than a gap in the analysis** — you are entitled to it.")
    w()
    if packet_missing:
        w(f"**{len(packet_missing)} of {len(D.HOA_PACKET_ITEMS)} items not "
          "recorded as provided:**")
        w()
        for _k, label in packet_missing:
            w(f"- {label}")
        w()
        w("Request them in writing, by name. Twelve months of minutes is the "
          "statutory floor and rarely enough to see a project cycle — ask for "
          "24 to 36.")
    else:
        w("All statutory items recorded as provided. Check their **dates**: a "
          f"reserve study older than {D.RESERVE_STUDY_MAX_AGE_YEARS} years "
          "fails Civ. Code §5550 and is a finding on its own.")

    # ── association health ──────────────────────────────────────────────
    r = D.review_hoa(hoa)
    w()
    w("## Association health")
    w()
    if r.reserve_band:
        w(f"Reserves read as **{r.reserve_band}** on the conventional bands "
          f"(strong ≥ {D.RESERVE_STRONG:.0%}, weak < {D.RESERVE_WEAK:.0%}). "
          "**The percentage alone decides nothing** — an association at 65% "
          "facing a roof next year is worse placed than one at 40% that has "
          "just finished replacing everything. Read it against the component "
          "list and the remaining useful lives.")
        w()
    w.table(["", "Topic", "Detail"],
            [[SEV[f.severity], f.topic, f.detail] for f in r.flags])
    if not r.determinable:
        w()
        w("> **Some association inputs are unrecorded, and each is reported "
          "as a note rather than a pass.** An association whose delinquency "
          "rate nobody has requested is not an association with a low "
          "delinquency rate.")

    # ── SB 326 ──────────────────────────────────────────────────────────
    sb = D.sb326(property_type=ptype, unit_count=units,
                 elevated_elements=elevated, report=hoa.get("sb326_report"))
    w()
    w("## SB 326 — exterior elevated elements (Civ. Code §5551)")
    w()
    w("The single most common source of large, sudden California condo "
      "assessments. Inspection by a licensed structural engineer or architect "
      f"on a {D.SB326_CYCLE_YEARS}-year cycle, for buildings of "
      f"{D.SB326_MIN_UNITS}+ multifamily dwelling units with walking surfaces "
      f"more than {D.SB326_MIN_HEIGHT_FEET} feet above ground supported "
      "substantially by wood.")
    w()
    applies = {True: "**Applies.**", False: "Does not apply.",
               None: "**Cannot be determined.**"}[sb.applies]
    w(f"{applies} {sb.reason}")
    w()
    w(sb.detail)
    w()
    w("Do not confuse this with SB 721, which covers apartment buildings "
      "rather than common interest developments.")

    # ── warrantability ──────────────────────────────────────────────────
    w()
    w("## Warrantability and financing")
    w()
    w("Separate from association health and frequently decisive, because it "
      "affects **resale** as much as this purchase. A non-warrantable project "
      "narrows the buyer pool to cash and portfolio lenders.")
    w()
    w.table(["Gate", "Threshold", "Recorded"], [
        ["Owner delinquency",
         f"above {D.DELINQUENCY_FINANCING_RISK:.0%} is a problem",
         _pct(hoa.get("delinquency_rate"))],
        ["Reserve contribution",
         f"below {D.RESERVE_CONTRIBUTION_MIN:.0%} of budget is a problem",
         _pct(hoa.get("reserve_contribution_share"))],
        ["Litigation", "construction defect is generally disqualifying",
         f"`{hoa.get('litigation')}`" if hoa.get("litigation") else "*not recorded*"],
        ["Deferred maintenance / structural findings",
         "post-Surfside standards treat these as disqualifying",
         f"SB 326: `{sb.status}`"],
    ])
    w()
    w("Single-entity ownership concentration, investor concentration and "
      "commercial floor-area share also apply and are **not** in this facts "
      "slice. The lender's condo questionnaire is what actually answers this; "
      "saying so is the correct output here rather than guessing.")

    # ── rules ───────────────────────────────────────────────────────────
    note = D.rental_restriction_note(hoa.get("rental_cap"))
    w()
    w("## Rules and restrictions")
    w()
    if note:
        w(note)
        w()
    w("Also read for: pets; parking (assigned, deeded or permissive) and "
      "guest parking; storage; architectural approval, flooring and noise "
      "rules; age or occupancy restrictions. **EV charging (Civ. Code §4745) "
      "and solar (§4746)** carry statutory rights — check the association's "
      "rules are consistent with them rather than assuming the rules are "
      "lawful.")

    # ── insurance ───────────────────────────────────────────────────────
    w()
    w("## Insurance")
    w()
    w("- **Master policy form** — bare walls, single entity or all-in. This "
      "decides what the buyer's HO-6 must cover, and buyers routinely "
      "under-insure because they misread it.")
    w("- **The master deductible, and how the CC&Rs allocate it.** A large "
      "deductible passed through to the owner of the unit where a loss "
      "originates is a real exposure that loss assessment coverage may only "
      "partly meet.")
    w("- **Earthquake is usually excluded.** Confirm rather than assume.")
    w("- Ask for the **declarations page, not a summary**.")

    # ── the remaining disclosures ───────────────────────────────────────
    req = D.required_disclosures(property_type=ptype, year_built=year)
    have = {str(x).strip().lower() for x in (provided or [])}
    absent = [d for d in req if d.key not in have]
    if absent:
        w()
        w("## Other disclosures not seen in the package")
        w()
        for d in absent:
            w(f"- **{d.name}** (`{d.authority}`) — {d.why}")
    if D.year_gated_but_unknown(year_built=year):
        w()
        w("> `year_built` is unrecorded, so the year-gated disclosures above "
          "stay on the list rather than being dropped.")

    missing = D.missing_reports(provided, property_type=ptype)
    if missing:
        w()
        w("## Reports a complete condo package normally contains")
        w()
        for _k, label in missing:
            w(f"- {label}")

    # ── contradictions ──────────────────────────────────────────────────
    w()
    w("## Contradictions")
    w()
    w("Build this table even if it comes back empty — an absent section reads "
      "as *not checked*.")
    w()
    w.table(["Topic", "Document A says", "Document B says", "Why it matters"],
            [["", "", "", ""]])
    w()
    w("The ones that recur: minutes discussing a project the reserve study "
      "does not fund; a budget assuming dues the notice does not match; TDS "
      "or SPQ silence on an assessment the minutes debate; an insurance "
      "summary that contradicts the CC&Rs on deductible allocation.")

    # ── next ────────────────────────────────────────────────────────────
    w()
    w("## Before removing contingencies")
    w()
    for item in ("The reserve study itself, current within "
                 f"{D.RESERVE_STUDY_MAX_AGE_YEARS} years, with the component "
                 "list",
                 "The SB 326 report and its date",
                 "The master policy declarations page and the CC&R deductible "
                 "allocation",
                 "A bound HO-6 quote with adequate loss assessment coverage",
                 "The lender's condo questionnaire",
                 "24–36 months of minutes, not the statutory 12"):
        w(f"- {item}")
    w()
    w("**Negotiation.** Pending assessments are directly negotiable — who "
      "pays an approved-but-unbilled assessment is a contract term, not a "
      "custom. Where reserves are weak the honest framing is that the buyer "
      "is purchasing a share of a future liability, which is a price "
      "conversation rather than a repair-credit one.")
    w()
    w(f"**Weakest input:** the association fields. "
      f"{'Some are unrecorded' if not r.determinable else 'All are recorded'}, "
      "and every one of them comes from a document the seller is obliged to "
      "provide. This checklist knows what to ask; it knows nothing about what "
      "the answers say.")
    cli.disclaimer(w, "lib/pf/disclosure.py")


def _pct(v) -> str:
    return f"{v:.0%}" if isinstance(v, (int, float)) else "*not recorded*"


if __name__ == "__main__":
    raise SystemExit(cli.run(
        title="California condo / townhome disclosure review",
        required=REQUIRED, build=build))
