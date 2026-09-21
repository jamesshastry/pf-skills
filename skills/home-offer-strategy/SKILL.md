---
name: home-offer-strategy
description: Research public internet sources for closed-sale comparables, reconcile verified comp-to-subject adjustments, and recommend an opening offer and walk-away ceiling bounded by market evidence, appraisal-gap cash, and stress-tested affordability. Use when preparing or revising an offer on a specific home, including when comparable facts are not yet recorded. Reads private figures from a local facts file and may send the minimum necessary property search terms to public web services.
requires:
  - meta.as_of
  - meta.currency
  - meta.jurisdiction.state
  - household.members
  - household.balance_sheet
  - retirement.annual_savings
  - cash_flow.scenarios
  - housing.monthly_rent
  - housing.purchase
  - housing.affordability
  - housing.transition
  - housing.offer
  - property_review.property_type
  - property_review.documents_provided
---

# Home offer strategy

## The decision

Recommend a defensible opening price and a walk-away ceiling for one identified
property. Keep three questions separate:

1. What do verified closed sales support after concessions and explicit
   comp-to-subject adjustments?
2. What can the household afford under the existing conservative cash-flow and
   closing-liquidity tests?
3. What opening posture fits the recorded competition and time-on-market facts?

The lowest binding ceiling wins. Desire to win is not evidence that the home is
worth more or that the household can carry it.

This is the price-and-bid stage of the declarative `property-evaluation`
workflow in `lib/pf/workflows.py`. It follows affordability, rent-versus-buy,
and the applicable disclosure review; conflict and whole-balance-sheet scenario
checks follow it before material cash or debt is committed. The separate
`mortgage-review` evaluates an existing loan, not a proposed purchase mortgage.

## Research missing comparables

If the recorded comparable set is absent, stale, or too weak to pass its own
selection rules, **continue with public-web research instead of stopping at the
missing facts**. Read [references/comparable-research.md](references/comparable-research.md)
and follow its source, citation, privacy, and stopping rules. Search for the
subject's public listing and nearby closed sales, verify the fields the model
needs, and present the proposed comparable rows with citations. Every research
or analysis response must include a table that places the subject and each
candidate or accepted comp in rows with the material property and transaction
data points in columns. Keep unknown values visible as `unknown`; do not omit a
material column or convert missing data to zero.

The Python runner remains deliberately offline. Web research is performed by
the agent invoking this skill, not hidden inside `run.py`. Do not write
researched values into the canonical facts file without confirmation. For a
preliminary answer, use an ignored working copy and label the result as based on
web-researched facts. If web access is unavailable or the public record cannot
support enough comps, report the searches attempted and the unresolved fields;
do not replace market value with an affordability-only negotiating range.

## Comparable evidence

Use closed, verified, arm's-length sales. Net seller concessions before applying
adjustments. Every adjustment is signed from the comparable to the subject:
positive when the subject is worth more, negative when the comparable is worth
more. Do not derive generic dollars per square foot, bedroom, condition grade,
school district, view, or renovation. Record adjustments supported by local
paired-sale evidence or a qualified professional, and set
`adjustments_supported` only after the material differences were reviewed;
otherwise exclude the comp.

Selection limits for age, distance, gross adjustment rate, and minimum comp
count are facts for the market being analyzed, not universal constants. A comp
outside those limits stays visible in the report with the reason it was
excluded. Active and pending listings may inform competition, but their asking
prices are not closed-sale evidence and do not belong in `comparables`.

Before the adjustment ledger, show a subject-to-comparable data-point table.
At minimum compare status/basis, property type, living area, sale date, distance,
price, raw price per square foot, concessions, and inclusion status. During web
research also compare beds/baths, lot, year built, parking, HOA, and condition
when material and publicly supportable. The table is an evidence audit, not a
license to infer generic adjustment rates from raw differences.

The central estimate is the median adjusted sale. The core range is the middle
half of adjusted values, and the full observed range remains visible. Neither
range is an appraisal or a confidence interval.

## Offer bounds

Reuse `housing-affordability`; never copy its ceiling into a second facts field.
The walk-away price is the lowest of:

- the stress-tested affordability ceiling;
- the upper core comparable value plus the buyer's explicitly recorded maximum
  premium; and
- for mortgage financing, the central comparable estimate plus the cash the
  buyer is willing and able to use for an appraisal gap after the down payment,
  closing costs, and required emergency reserve.

Round down to the recorded offer increment. Multiple offers can move the
opening anchor toward the central evidence, but never move the walk-away
ceiling. A stale or reduced listing with no competing offer anchors at the low
end. Unknown competition produces a balanced posture, not a prediction.

## Boundaries

This skill may research publicly accessible sale and listing records. It does
not claim access to a private MLS, bypass authentication, CAPTCHAs, robots or
paywalls, upload local documents, estimate an appraisal, inspect disclosures,
determine affordability, predict a seller response, draft a contract, or
recommend waiving inspection, financing, appraisal, title, insurance, or legal
protections. Run the applicable disclosure review before treating a condition
adjustment as complete, and run `conflict-check` plus a housing scenario before
an offer materially changes cash, debt, or reserves.

The weakest input is the adjustment ledger. A precise calculation over weak or
broker-selected adjustments is still a weak valuation.

---

*Not financial, tax, legal, appraisal, or real-estate advice.*
