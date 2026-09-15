---
name: ca-sfh-disclosure-review
description: Generate the checklist for reviewing a California detached single-family disclosure package — which statutory disclosures this property attracts given its age, which standard reports are absent, and what to read the TDS and SPQ for. Use when reviewing a California home purchase, reading a TDS, SPQ or NHD, deciding whether a disclosure package is complete, or before removing inspection contingencies. Produces the checklist; the documents still have to be read against it. Reads figures from a local facts file.
requires:
  - meta.jurisdiction.state
  - property_review.property_type
---

# California single-family disclosure review

## The idea

An agent handed a folder of PDFs improvises its own checklist, and **the
checklist is the part that must not be improvised.** Whether a pre-1978 home
needs a lead-based paint disclosure is not a judgement call. Whether a package
is missing a sewer scope is a list. Whether the TDS is exempt changes how much
weight silence carries.

So this generates *what to look for*, from a cited table, and the reading
happens afterwards. Same division as `document-intake`: the repository decides
what is worth reading for; the reader reads.

## What it produces

| Section | What it answers |
|---|---|
| Disclosures this property attracts | Statutory list, filtered by property type and build year, with the authority for each |
| Reports normally present | What is absent from the package — a finding, not a gap in the analysis |
| What to read for | TDS/SPQ "Yes" boxes, unknowns, exemption status, the contradiction table |
| Grading | Severity tests and cost buckets, so findings are comparable |
| Before contingencies | What to commission, including a **bound** insurance quote |

## Three rules it imposes on the reading

**Label the basis of every claim** — *stated* with a citation, *inferred* with
its evidence, or *absent*. An unlabelled assertion cannot be told from a guess,
and a guess in a due-diligence note becomes a decision three steps later.

**Build the contradiction table even when it is empty.** An absent section reads
as "not checked". "No contradictions found" is a finding.

**Use "cannot be estimated" freely.** A cost figure you cannot defend carries
more weight than an honest gap, because it looks like work.

## Two things it gets right that a generic checklist does not

**An unrecorded build year does not drop the year-gated disclosures.** Lead-based
paint stays on the list, flagged as kept *because* the year is unknown. "We do
not know whether this is pre-1978" is a question to ask, not a reason to stop
asking it.

**It knows the TDS can be exempt.** Trustee sales, probate and some REO
transfers are excused under Civ. Code §1102.2. A thin package from an exempt
seller is not a clean package, and conflating the two is the most common way a
review reaches the wrong conclusion cheerfully.

## Jurisdiction

**California only, and it refuses outright for anything else** rather than
reaching for the nearest regime it knows. Disclosure law does not transfer
between states.

The state is read from `property_review.state` where present, falling back to
the household's. Disclosure law follows the **property** — a household in one
state reviewing a listing in another is ordinary, and using the buyer's
jurisdiction would apply the wrong regime to the documents.

## What it will not do

**It does not read documents, score the property, or reach a verdict.** It has
no access to the PDFs and makes no claim about them. Every conclusion still
comes from the reading.

**It is not a complete statement of California law.** The table is what has been
checked and cited, marked `verified_on: unverified` like everything else in this
repository. Where a pinpoint section is not certain, the authority is named
without one — an approximate citation reads as settled and is harder to check
than an honest description.

**It does not look at an association.** If the property is a condo or townhome
it says so and points at `ca-condo-hoa-disclosure-review`, because on those the
building and the association are usually the larger risk.

## Closing

Run it before reading the package, not after. The order matters: a conclusion
drawn from an unstated sample is the most common failure in document review, and
knowing what is missing changes how you read what is present.

*Not financial, tax, or legal advice. California disclosure law changes; a real
estate attorney, a licensed inspector and an insurance broker are the people who
actually answer these questions.*
