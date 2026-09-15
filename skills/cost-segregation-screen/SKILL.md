---
name: cost-segregation-screen
description: Screen whether commissioning a cost segregation study is plausibly worth it — reclassified basis range, bonus depreciation, present-valued timing benefit against the study fee, and whether the resulting losses can be deducted at all. Use when asked about cost segregation, accelerating depreciation on a rental, bonus depreciation on a property purchase, whether a depreciation study pays for itself, or §1245 recapture on sale. Run passive-loss-eligibility first. Reads figures from a local facts file.
requires:
  - real_estate.cost_segregation
  - assumptions.marginal_tax_rate
---

# Cost segregation screen

## A screen, not a study

A real cost segregation study is an engineering exercise: a site visit, a
component take-off, and an allocation written to be defensible under audit. It
costs several thousand dollars and it produces a number this skill cannot.

What this skill decides is narrower and comes first: **are the economics
plausibly in the region where paying for one makes sense?** Basis, holding
period, marginal rate, and — the one that decides it more often than any of the
others — whether the resulting deduction can be used at all.

So the reclassified share is reported as a **range**, not an estimate.
Producing the point figure *is* the study. Anything here that looks precise is
precise about the wrong thing.

## The gate decides this, not the arithmetic

`passive-loss-eligibility` runs first, and if it finds no open §469 door this
screen returns **zero** rather than a smaller positive number.

That is not conservatism. Accelerated depreciation behind a shut gate does not
produce a deduction — it enlarges a suspended passive loss, which is released
only against future passive income or on disposition. **Accelerating a loss you
cannot deduct is worth nothing this year, and it still costs the study fee.**

This is the single most common way cost segregation is oversold to a W-2
household: the pitch quotes the first-year deduction multiplied by a marginal
rate, for a taxpayer who cannot take the deduction. The multiplication is right
and the answer is zero.

If a door *is* open — usually the short-stay exception — the arithmetic below
means something.

## It is a timing benefit, and the report says so twice

Cost segregation does not create deductions. It moves them forward. Over the
life of the property the total is identical; what changes is when.

So the value is the time value of the deferral over your actual holding period,
not the first-year tax saving. The report present-values it and shows both,
because quoting the year-one figure as "the benefit of the study" overstates it
by the entire reversal — and that overstatement is exactly the number in most
sales material.

A short hold makes it worse, not better: less time for the deferral to be worth
anything, and the reversal arrives sooner.

## Recapture reverses part of it, at a worse rate

The reclassified 5- and 7-year components are **§1245 property**, recaptured on
sale at **ordinary income rates** — not at the §1250 rate that applies to the
building.

So if your marginal rate at sale exceeds the unrecaptured §1250 rate, a study
has converted some future capital-rate gain into future ordinary income. That
is a **rate cost on top of the timing reversal**, and it is routinely left out.
It can be avoided by exchanging rather than selling, which makes this skill and
`1031-exchange-modeling` a pair.

## The legislated figures come from the facts file

`assumptions.bonus_depreciation_rate` is the important one: the bonus
percentage is set by statute and has changed in most recent years, so a figure
baked into this library would go stale silently and produce a confident wrong
answer. Absent it, the report describes the structure and **refuses the
benefit figure**.

Same for `assumptions.marginal_tax_rate` and `assumptions.state_tax_rate`. The
recovery periods — 27.5 years residential, 39 commercial — are in the module,
because they are structural and do not drift annually.

## Land is not depreciable

`depreciable_basis` must already exclude land. Entering the purchase price
overstates every figure in the report, typically by 15–30%, and nothing
downstream can detect it. Use the allocation on the closing statement or the
assessor's land/improvement split, and say which you used.

## What it will not do

It does not allocate components, it does not produce anything an examiner will
accept, and it is not a substitute for the free feasibility estimate most
providers offer. It does not model the §163(j) interest limitation or the
real-property-trade election that interacts with it, does not handle partial
asset dispositions, and does not model qualified improvement property
separately. It takes no view on providers.

## Closing

1. **The gate.** If shut, the answer is no and the rest is arithmetic about
   nothing.
2. **The present-valued benefit range**, against the study fee — not the
   year-one saving.
3. **The §1245 recapture**, and whether the exit is a sale or an exchange.
4. **Confirm land is excluded** from the basis before believing any of it.

---

*Not financial, tax, or legal advice. This is a screen. The study is the study.*
