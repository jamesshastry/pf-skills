# California single-family disclosure review

⚠️ **The recorded property type is `townhome`, which sits inside a common interest development.** Use `ca-condo-hoa-disclosure-review` instead — on a property with an association the building and the association are usually the larger risk, and this skill does not look at either.

The California-wide checklist below still applies to the unit, so it is printed rather than withheld. It is not sufficient on its own for this property.

## How to use this

This is the checklist, not the analysis. It says what a California single-family package must contain and what to look for; reading the documents against it is the next step, and no part of it is a finding until a document has been read.

Label every claim you make from the documents as **stated** (cite the document and page), **inferred** (say from what) or **absent**. An unlabelled assertion cannot be told from a guess, and a guess in a due-diligence note becomes a decision three steps later.

## Disclosures this property attracts

| Disclosure | Authority | In the package? |
|---|---|---|
| Real Estate Transfer Disclosure Statement | `Civ. Code §1102 et seq.` | yes |
| Natural Hazard Disclosure statement | `Civ. Code §1103` | yes |
| Seller Property Questionnaire | `C.A.R. standard form, not statute` | yes |
| Lead-based paint disclosure and pamphlet | `42 U.S.C. §4852d (federal)` | **not seen** |
| Mello-Roos / 1915 Act special assessment notice | `Civ. Code §1102.6b` | **not seen** |
| Megan's Law database notice | `Civ. Code §2079.10a` | **not seen** |
| Water-conserving plumbing fixture compliance | `Civ. Code §1101.4` | **not seen** |
| Smoke and carbon monoxide alarm compliance | `Health & Safety Code §§13113.7, 17926` | **not seen** |
| HOA transfer disclosure packet | `Civ. Code §4525` | **not seen** |
| Current reserve study | `Civ. Code §5550` | **not seen** |
| SB 326 exterior elevated element inspection | `Civ. Code §5551` | **not seen** |

- **Lead-based paint disclosure and pamphlet** — Required for housing built before 1978. The most commonly missing item in a package, and the penalty is federal rather than contractual.
- **Mello-Roos / 1915 Act special assessment notice** — A special district lien is an ongoing cost that does not appear in the asking price and is easy to miss in the tax bill.
- **Megan's Law database notice** — Statutory notice language; its absence signals a package assembled without the standard addenda rather than a substantive problem.
- **Water-conserving plumbing fixture compliance** — Non-compliance is cheap to fix and a reliable indicator of how much else was deferred.
- **Smoke and carbon monoxide alarm compliance** — Cheap, mandatory, and a common point-of-sale condition.
- **HOA transfer disclosure packet** — Defines exactly what the seller must hand over: governing documents, pro-forma budget, assessment and reserve funding disclosure summary, reserve study, insurance summary, delinquency and litigation statements, and 12 months of open board meeting minutes. Because the list is statutory, a missing item is a finding rather than a gap in the analysis.
- **Current reserve study** — Required at least every three years with an annual review. A study older than that is a finding in its own right.
- **SB 326 exterior elevated element inspection** — Balconies, decks and walkways more than six feet up and supported substantially by wood, in buildings of three or more multifamily dwelling units, inspected by a licensed structural engineer or architect on a nine-year cycle. The single most common source of large, sudden California condo assessments — and where no report exists at all, the obligation exists anyway and the cost still lands on owners.

## Reports a complete package normally contains

**3 not seen.** An absent report is a finding, not merely a gap in the analysis — a package is not clean because nobody looked.

- Roof inspection
- Sewer lateral camera scope
- Permit history or city records report

## What to read for

**Every `Yes` on the TDS and SPQ**, with the seller's explanation and whether it is adequate. Look for *patterns* — three separate plumbing repairs is a different finding from one.

**Every blank, vague or `Unknown` answer.** A seller answering "unknown" about their own occupancy is a follow-up, not an answer.

**Whether the TDS is exempt.** Trustee sales, probate and some REO transfers are excused under Civ. Code §1102.2. Silence from an exempt seller carries far less information than silence from an ordinary one, and mistaking the two is how a thin package reads as a clean one.

**Contradictions between documents.** Build the table even if it comes back empty — an absent section reads as *not checked*.

| Topic | Document A says | Document B says | Why it matters |
|---|---|---|---|
|  |  |  |  |

The ones that recur: TDS "no water damage" against inspection evidence of past leaks; SPQ "no claims" against a CLUE report; claimed upgrades against permit history; a general inspector deferring to a specialist whose report is not in the package.

## Grading what you find

| Severity | Test |
|---|---|
| **High** | Safety, habitability, insurability or financing — or plausibly above 2% of price |
| **Medium** | Real money, but scheduled rather than a surprise |
| **Low** | Maintenance, deferred upkeep, cosmetic |

Cost buckets: under $5k · $5–20k · $20–50k · $50k+ · **cannot be estimated**. Use the last one freely. A figure you cannot defend carries more weight than an honest gap, because it looks like work.

**Insurance is the item most likely to change the deal** and the one most often left to the end. In a high fire hazard severity zone, get a **bound quote** rather than an estimate: admitted carriers decline, and a FAIR Plan policy plus a difference-in-conditions wrapper costs materially more than the figure in a spreadsheet.

**Unpermitted work** is a chain rather than a flag: retroactive permitting, possible forced removal, appraisal and financing problems where square footage is not legal, and an insurer declining a claim on work that was never inspected.

## Before removing contingencies

- A structural engineer where any foundation or framing question is open
- A sewer lateral camera scope — cheap, and the failure is expensive and invisible
- A licensed roofer's opinion on remaining life, not the general inspector's
- A **bound** insurance quote
- Permit history pulled from the jurisdiction rather than taken from the listing

**Weakest input:** this checklist knows what the package *should* contain and nothing about what it *says*. Every conclusion still comes from reading the documents.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/disclosure.py` with their reasons; every figure above is derived, not restated.*
