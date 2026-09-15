---
name: probate-exposure
description: Work out which accounts will pass through probate court, what that costs in the household's state, and the cheapest instrument that avoids it for each one. Covers the pour-over will misconception, small-estate thresholds, simplified spousal transfers, and why the right designation differs between a taxable and a retirement account. Use when asked about avoiding probate, whether a trust is worth it, what probate costs, transfer-on-death registration, joint titling, or whether a funded trust means the estate is covered. Reads figures from a local facts file.
requires:
  - meta.jurisdiction.state
  - household.members
  - household.balance_sheet
---

# Probate exposure

## The idea

`beneficiary-audit` asks whether a designation is *coherent*. This asks a
different question and reaches a different decision: **which assets will pass
through court, what will that cost, and what is the cheapest instrument that
avoids it for each one.**

Titling decides that, and nothing else in this repository reads titling.

## A pour-over will does not avoid probate

The single most common misconception here, and it is held by exactly the
households who believe they are covered.

A pour-over will directs whatever is left into the trust on death. It fixes the
**destination**, not the **route**. Anything still titled in an individual name
goes through court first and lands in the trust afterwards, having paid for the
trip. A trust avoids probate only for the assets actually retitled into it —
drafting is the part people pay for, retitling is the part they skip.

## The rule

An asset avoids probate if **any one** of these is true:

| Route | What carries it |
|---|---|
| A valid beneficiary, TOD or POD designation | Passes by contract, outside the will |
| Joint tenancy with right of survivorship | Passes by operation of law |
| Titled to the trust | Never in the estate at all |

Otherwise it passes under the will, and the will is the probate route.

Titling is checked first because it is dispositive. A designation is checked
second because it carries the asset out regardless of how the account is
titled.

## Cost is jurisdiction-specific and never inferred

Some states set fees as a **statutory percentage of the gross value** — before
mortgages, so a heavily mortgaged house is priced on the whole house — and in
at least one, the attorney and the personal representative may **each** claim
the full scheduled fee, so the real cost is double what reading the statute
once suggests. Others bill whatever is reasonable, usually hourly.

A state is in the table only if it was checked, with a source and a
`verified_on`. Every other state returns UNKNOWN and the report says the cost
cannot be estimated. **It never reasons by analogy from a state it does know**
— the pricing models are different enough that borrowing one produces a
confident wrong number.

## Two things that make the exposure smaller than it looks

**Small-estate procedures.** Most states replace probate with an affidavit
below a threshold. Below it the exposure may be near zero even with no
designations at all, and the skill will say so rather than recommending
paperwork that buys nothing. The threshold is often indexed, so it moves.

**Simplified spousal transfers.** Several states offer an abbreviated procedure
for property passing to a surviving spouse. There is an interaction worth
knowing: a will that pours to a **trust** rather than to the spouse directly
may take that shortcut off the table, because property passing to a trust is
not property passing to a spouse. The skill flags that as a question for
counsel and does not decide it.

## The right designation depends on the tax wrapper

The subtle part, and the reason there is no single answer for "the accounts":

| Wrapper | Primary should be | Why |
|---|---|---|
| Taxable | The trust | One dispositive scheme; the contingent protections already drafted apply automatically |
| **Retirement** | **The spouse, directly** | A trust as primary generally forfeits the spousal rollover and forces a roughly ten-year payout |

A skill that optimised only for probate avoidance would recommend
trust-as-primary everywhere and quietly cost a surviving spouse decades of tax
deferral. That is a larger number than the probate it saved.

## Avoiding probate is not the same as a good outcome

A transfer-on-death registration naming a minor avoids probate **and** triggers
a court-appointed guardianship of the estate, which hands the whole balance
over outright at the age of majority. Frequently worse than the probate it
avoided.

So this runs a second test after the probate test, and it constrains **what the
skill is allowed to recommend** rather than what it diagnoses. Where the only
available beneficiaries are minors, the obvious instrument is withheld and the
reason is stated.

Diagnosing a designation that *already* names a minor belongs to
`beneficiary-audit`, which does it. This does not restate it.

## Unknown is neither exposed nor covered

`titled_to` absent means nobody looked. It is the most common real state and
the one most likely to be hiding a problem.

Reporting it as exposed produces a false alarm and a recommendation to buy
paperwork. Reporting it as covered produces a silent failure. It reports as
**cannot be determined**, and the estimated cost becomes a range — the width of
that range is what not having looked is worth.

## What it will not do

**It does not decide whether joint titling is a good idea.** Adding a joint
owner is a completed gift in many cases, exposes the asset to that person's
creditors and divorce, and can forfeit a step-up in basis. It avoids probate;
that is a different question from whether to do it.

**It does not price the delay.** Ordinary fees only — extraordinary fees,
filing costs, appraisal, bond and months of assets being unavailable are all
real and none are in the figure.

**It does not read the deed.** Every verdict rests on `titled_to`, which is not
on any statement and is the weakest input by construction. Tenants in common
looks identical to joint tenancy on a monthly statement and does not avoid
probate.

**It is not legal advice**, and the spousal-transfer interaction in particular
is flagged for counsel rather than resolved.

## Closing

1. **Lead with the undetermined count**, not the exposed total. The range is
   the honest answer and the phone calls that close it are free.
2. **Fixes are per account**, because the wrapper changes the instrument.
3. **Hand off to `beneficiary-audit`** for whether the forms are coherent, and
   to `estate-document-review` for whether the trust is funded at all.

*Not financial, tax, or legal advice. Estate law is state-specific and changes.*
