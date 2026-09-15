---
name: charitable-giving-strategy
description: Decide what to give and how — donating appreciated securities in kind instead of cash, bunching several years of giving into a donor-advised fund to clear the standard deduction, and qualified charitable distributions from an IRA once age-eligible, with the AGI percentage limits that constrain each. Use when asked about charitable donations, donor-advised funds, donating stock, QCDs, itemizing versus the standard deduction, or how to give tax-efficiently. Reads figures from a local facts file.
requires:
  - household.members
  - assumptions.marginal_tax_rate
---

# Charitable giving strategy

## Donating appreciated securities fixes two problems in one transaction

The idea this skill exists to encode, and it leads every report.

Giving an appreciated long-term holding **in kind** to a public charity does two
things at once. The donor deducts the **full fair market value**, and the
embedded capital gain is **never realised by anyone** — the charity is exempt,
so the gain evaporates rather than transferring. Selling first and donating the
proceeds gives up the second half: the gain is realised, the tax is paid, less
money reaches the charity for the same cost to the donor.

The deduction is identical either way. **The avoided gain is pure gain.**

And because the best gift is the most appreciated position, which in a
concentrated household is usually the employer stock, the same transaction
**reduces the concentration**. Two problems improved by one action is rare
enough in personal finance to be worth leading on.

One caution attached to it: **charitable intent sets the size of the gift, not
the concentration.** A gift large enough to fix a concentration problem is a
gift far larger than most households mean to make. Size it here, then take the
remaining exposure to `employer-concentration-risk`.

## Donating a loss position is strictly worse, always

The mirror image, and the error the excitement above produces.

Giving a holding worth less than its basis deducts the *value* and **forfeits
the loss** — nobody ever claims it. Sell it, book the capital loss against other
gains, donate the cash: the charity receives the same amount, the deduction is
the same, and the loss survives. There is no household for whom the in-kind
version of this is better.

The same logic caps a **short-term** lot: held under a year, the deduction is
limited to **basis**, not value. Give a long-term lot of the same security
instead, or wait.

## Bunching is arithmetic

**The standard deduction is a floor, not a subtraction.** A household whose
itemizable total sits below it gets *nothing* from ordinary annual giving —
every dollar given is already covered by the standard deduction.

Bunching several years of giving into one clears the floor once and takes the
standard deduction in the other years. The report computes the benefit over the
best window and compares on **total deductions taken across the window**, not on
the itemized total in the bunch year — a household that already itemizes
comfortably has a large bunch-year figure and no benefit, and reporting the
former would imply the latter.

**A donor-advised fund separates the deduction from the grant.** Fund it in the
bunch year, deduct that year, and grant to the charities on the same schedule as
before. That answers the objection that stops most households bunching: the
charity's cash flow does not have to absorb it.

## The AGI limits differ by what is given

The constraint people meet mid-plan. Cash to a public charity is deductible up
to **60% of AGI**; appreciated capital-gain property at fair market value only
up to **30%**. A bunched in-kind gift sized against the cash limit **overshoots
by half.**

The excess carries forward five years and then expires. A carryforward is worth
less than a deduction now and worth nothing if income falls in the years that
have to absorb it, so splitting a large gift across two tax years usually beats
relying on it. Electing to deduct basis instead of value raises the limit to
50% — almost never worth it, because giving up the appreciation in the deduction
costs more than the extra room is worth.

## QCDs, once age-eligible

A qualified charitable distribution goes straight from an IRA to the charity and
**never enters AGI** — which beats a deduction, because AGI drives Medicare
IRMAA surcharges, the taxability of Social Security, and every phase-out in the
code. A household taking the standard deduction gets no benefit from ordinary
giving and full benefit from this.

Two details that matter: the QCD age is **70½ and has not moved with the RMD
age**, so there are several years in which giving from the IRA is available
before it is required. And where RMDs apply, **make the QCD before taking any
other distribution** — the first dollars out of the IRA are the ones that count
toward the RMD, and a distribution already taken cannot be undone.

## What comes from the facts file

The **standard deduction**, the **QCD annual limit** and the **capital gains
rate** are read, never encoded. The first two are indexed and move most years;
the third is 0%, 15% or 20% depending on the household, so assuming one would be
wrong for most readers with nothing in the output to say which. Missing any of
them suppresses that part of the report rather than defaulting it.

## What it will not do

- **No charity selection**, and no view on how much to give. It arranges giving
  that has already been decided on.
- **No state treatment.** Federal only, nominal dollars.
- **No appraisal.** Non-publicly-traded property above the reporting threshold
  needs a qualified appraisal, which is out of scope here.
- **No DAF provider comparison.** Fees and grant minimums vary and are not
  modelled.

## The weakest input

The **cost basis** on each candidate holding. Without it, an appreciated gift
and a forfeited loss look identical — and those are opposite recommendations,
not adjacent ones. The broker has it.

## Closing

1. **The in-kind gift first**, with the avoided gain shown separately from the
   deduction. They are different benefits and only one of them is unusual.
2. **Any loss position**, as a "sell first" correction.
3. **The bunching benefit**, if the household sits below the standard deduction.
4. **The AGI limit**, if the plan overshoots it.
5. **Transfer the security, do not sell and wire the cash.** A sale the day
   before, however briefly, realises the gain and there is no way back.

---

*Not financial, tax, or legal advice. Confirm the receiving charity accepts
in-kind transfers before initiating one.*
