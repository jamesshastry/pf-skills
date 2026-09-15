# prompts/

Long-form prompts for document review. **These are not skills**, and the distinction
is deliberate.

| | Skills (`skills/`) | Prompts (here) |
|---|---|---|
| Input | `inputs/facts.yml` — a typed contract | A pile of PDFs |
| Logic | Tested Python in `lib/pf/` | The agent's reading |
| Output | Deterministic, golden-tested | Synthesis, different every time |
| Fails when | A field is missing | A document is missing or says something odd |

`CONTRIBUTING.md` sets four tests for a skill. These pass two and fail two: there is a
real decision with a defensible rule, but **the arithmetic does not fit in tested
code** and **there is no schema slice at all**. A `run.py` here would do nothing, and
a golden fixture cannot exist for output that is a reading rather than a computation.

Rather than weaken the skill contract to admit them, they live here and say what they
are.

## What is here

| Prompt | For |
|---|---|
| [`ca-sfh-disclosure-review.md`](ca-sfh-disclosure-review.md) | California detached single-family home |
| [`ca-condo-hoa-disclosure-review.md`](ca-condo-hoa-disclosure-review.md) | California condo or townhome, where the HOA is usually the larger risk |

Both are California-specific by design. The statutory citations — Civ. Code §1102 for
the TDS, §1103 for the NHD, Davis-Stirling for associations, §5551 for balcony
inspections — do not transfer to other states, and a prompt that pretended to be
general would quietly apply the wrong law. That is the same rule the skills follow for
jurisdiction tables: **encoded only where checked, never by analogy.**

## Using one

Paste everything below the horizontal rule into a fresh conversation and attach the
PDFs. Both prompts open by requiring a **document inventory** before any analysis,
because a conclusion drawn from an unstated sample is the most common failure in
document review — and the absence of a standard report is itself a finding.

## Where the output goes

Both prompts direct output to `documents/analysis/`, which is gitignored, under a
**non-identifying filename**.

The obvious instruction — save it as `<Property Address>analysis.md` — puts a real
address into a directory listing, shell history, and every screen share of that
terminal. The file contents may be protected by `.gitignore`; the filename is not. It
is also a small thing to get right once rather than remember every time.

## Relationship to the skills

These answer *"should I buy this specific property, given these documents"*. The
skills answer the questions either side of that:

- [`rent-vs-buy`](../skills/rent-vs-buy/) — whether to buy at all, at this
  price-to-rent ratio, for this holding period
- [`rental-deal-underwriting`](../skills/rental-deal-underwriting/) — whether an
  investment property pencils on NOI, DSCR and IRR
- [`passive-loss-eligibility`](../skills/passive-loss-eligibility/) — whether the tax
  benefits an investment case assumes are usable at all
- [`probate-exposure`](../skills/probate-exposure/) — how to take title once you own it

A prompt here plus `rent-vs-buy` is a reasonable pre-offer workflow: the skill sizes
the decision, the prompt reviews the specific property.

*Not legal, tax or engineering advice.*
