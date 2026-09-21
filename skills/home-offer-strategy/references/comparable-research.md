# Public comparable-sale research

Use this procedure when `housing.offer.comparables` is missing, stale, or does
not contain enough usable closed sales. The goal is a cited proposal for the
facts file and, when supportable, a preliminary offer analysis—not a claim of
private MLS access.

## Privacy boundary

Tell the user before searching an exact address. Send only the property address
or the minimum location and property characteristics needed for the search.
Never upload disclosure PDFs, tax returns, account balances, financing details,
names, contact information, or the facts file to a search or listing service.
The search provider and visited sites receive the query under their own privacy
terms.

## Source order

Prefer sources in this order, using more than one where practical:

1. County recorder, assessor, or other official public records for transfer
   date, recorded consideration, parcel facts, and ownership history.
2. The closed listing page or an authorized MLS interface for sale price,
   listing history, seller concessions when disclosed, and property features.
3. Established listing aggregators for corroboration and archived photos or
   descriptions.

Do not describe an aggregator as the MLS. Do not bypass access controls,
CAPTCHAs, robots restrictions, subscription gates, or site terms. Search another
lawfully accessible source instead.

## Search and selection

Start with the subject address or parcel identifier, then search recent sold
properties using the recorded property type, neighborhood, living area, lot,
bed/bath count, condition, parking, view, HOA, and other material features. Aim
for five to eight candidates and stop when at least the recorded
`minimum_comparables` pass every selection rule, or when reasonable public
sources have been exhausted.

For every candidate capture:

- exact source URL and access date;
- closed-sale date and price;
- whether seller concessions are explicitly known;
- distance from the subject and how it was measured;
- property type and living area;
- evidence bearing on whether the sale was arm's-length; and
- every material difference considered in the adjustment ledger.

A search-result snippet is a lead, not evidence. Open the underlying source.
Resolve conflicting sale prices, dates, or property attributes before marking
the row `verified: true`; otherwise keep it unverified and explain the conflict.

## Adjustments

Do not infer a generic dollar-per-square-foot or bedroom adjustment from an
asking-price page. Prefer nearly matched properties. Use a nonzero adjustment
only when supported by local paired sales, a documented appraisal adjustment,
or a qualified professional. Set `adjustments_supported: true` only after all
material differences were reviewed. An explicit zero means a factor was
considered and no adjustment was supported; omission means it was not checked.

Seller concessions are often absent from public sources. Never convert that
absence to zero. A comp with unknown concessions cannot be marked verified for
the deterministic valuation, although it can remain in the research table as a
candidate needing agent or recorder confirmation.

## Comparison and source tables

Before proposing YAML or an offer, present both:

1. A subject-to-candidate comparison table with one row for the subject and
   each candidate. Use columns for listing/closed status, property type, living
   area, beds/baths, lot, year built, parking, HOA, condition, sale date,
   distance, price, raw price per square foot, known concessions, verification,
   and proposed inclusion. Keep a cell as `unknown` when the source does not
   establish it; never show missing concessions or features as zero.
2. A source-audit table with candidate, publisher, exact URL, access date,
   source type, and conflicts or unresolved fields. Cite the comparison rows
   back to this table.

Columns that truly do not apply may be marked `n/a`; retain all material
comparison columns. Distinguish verified facts, inferences, and unresolved
fields. The comparison reveals differences but does not itself support a
dollar adjustment.

## Handoff to the calculator

Do not silently modify `inputs/facts.yml`.
After confirmation, record the supported rows under
`housing.offer.comparables`, refresh `meta.as_of`, and run:

```bash
uv run skills/home-offer-strategy/run.py --facts inputs/facts.yml
```

If the user requests an immediate preliminary analysis, make an ignored working
copy rather than changing the canonical facts. Preserve `verified: false` and
`adjustments_supported: false` wherever support is incomplete; the calculator
should block rather than turn weak web evidence into a confident bid.

## Stopping rule

Stop after enough valid comps are found or after official records plus at least
two reasonable public listing sources have been checked without producing the
required evidence. Report the sources attempted and each missing fact. Do not
substitute the list price, an automated valuation estimate, tax assessment, or
the household's affordability ceiling for closed-sale market evidence.
