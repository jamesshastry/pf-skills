---
name: ca-condo-hoa-disclosure-review
description: Generate the checklist for reviewing a California condo or townhome package, weighted toward the association — which Civil Code section 4525 packet items are missing, how the reserves and delinquency rate read against their thresholds, whether the SB 326 balcony inspection applies and was done, and what threatens warrantability. Use when reviewing a California condo or townhome purchase, reading HOA documents, assessing special assessment risk, or before removing contingencies. Reads figures from a local facts file.
requires:
  - meta.jurisdiction.state
  - property_review.property_type
  - property_review.hoa
---

# California condo / townhome disclosure review

## The idea

**On a condo the unit is rarely what hurts you. The building and the association
are.**

A flawless unit inside an association with 24%-funded reserves, construction
defect litigation and an unperformed balcony inspection is a worse purchase than
a tired unit in a well-run building — and only one of those two facts is visible
on a walkthrough. So this skill spends most of its output on the association and
treats the unit as the smaller half.

It generates the checklist and the threshold comparisons. It does not read the
documents.

## The §4525 packet is a statutory list, which changes what "missing" means

Civ. Code §4525 defines exactly what a seller must hand over: governing
documents, pro-forma budget, the assessment and reserve funding disclosure
summary, the reserve study, insurance summary, delinquency and litigation
statements, approved special assessment notices, and twelve months of open board
meeting minutes.

Because the list is statutory, **a missing item is a finding rather than a gap
in the analysis.** You are entitled to it, and the skill names which ones are
absent so they can be requested by name. Twelve months of minutes is the floor
and rarely spans a project cycle — ask for twenty-four to thirty-six.

## SB 326 gets its own section because it is the one that bites

Civ. Code §5551 requires inspection of exterior elevated elements — balconies,
decks and walkways more than six feet above ground, supported substantially by
wood — in buildings of three or more multifamily dwelling units, by a licensed
structural engineer or architect, on a nine-year cycle.

It is the single most common source of large, sudden California condo
assessments. The skill establishes whether it applies from the unit count and
element description, and then reports one of:

| Status | What it means |
|---|---|
| `clean` | Inspected, nothing needing immediate repair. Check the next due date |
| `findings` | **Elements need repair.** Establish whether the work is funded, assessed, or neither |
| `none` | **No inspection performed.** The obligation exists anyway, so the cost is ahead of the buyer |
| unrecorded | Ask. Absence from the packet is not evidence it was done |

Not to be confused with SB 721, which covers apartment buildings rather than
common interest developments.

## Thresholds, and why the number alone decides nothing

Reserves are banded — strong at 70%, weak below 30% — and the report says
plainly that **the percentage on its own decides nothing.** An association at 65%
facing a roof next year is worse placed than one at 40% that has just finished
replacing everything. The band is reported *alongside* the instruction to read
the component list, never instead of it.

Delinquency above 15% and reserve contributions below 10% of budget are reported
against **warrantability**, not just cash flow — which matters because it is a
resale problem even for a cash buyer. A non-warrantable project narrows the
future buyer pool to cash and portfolio lenders.

## Every unrecorded field is a note, never a pass

An association whose delinquency rate nobody has requested is not an association
with a low delinquency rate. Unrecorded inputs produce notes and set the report's
determinable flag; they never quietly read as clean.

## What it will not do

**It does not read documents or reach a verdict.** It has no access to the PDFs.

**It does not assess warrantability fully.** Single-entity concentration,
investor ratio and commercial floor-area share are real gates and are not in
this facts slice. The lender's condo questionnaire answers those, and saying so
is the correct output rather than guessing.

**It does not resolve rental restrictions.** Civ. Code §4741 limits caps below
25%, and restrictions recorded before it are frequently unenforceable as
written — which is a question for counsel in either direction, not a fact this
skill can settle.

**California only.** It refuses outright elsewhere; Davis-Stirling has no
analogue in most states. The state comes from `property_review.state` where
present, because disclosure law follows the property rather than the buyer.

## Closing

Run it before reading the package. Then request the missing §4525 items by name,
in writing, and read the minutes for what the reserve study does not fund — that
gap is where the assessment lives.

*Not financial, tax, or legal advice. Davis-Stirling and California disclosure
law change; a real estate attorney, a structural engineer and an insurance
broker are the people who actually answer these questions.*
