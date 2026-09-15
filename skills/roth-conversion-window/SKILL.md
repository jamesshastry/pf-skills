---
name: roth-conversion-window
description: Identify the low-tax years between employment income ending and RMDs or Social Security starting, and how to use them for Roth conversions. Covers bracket filling, IRMAA and subsidy knock-ons, and the widow's tax trap. Use when asked about Roth conversions, RMD planning, or tax planning in early retirement. Reads figures from a local facts file.
requires:
  - household.members
  - retirement.planned_retirement_age
---

# Roth conversion window

## The window

Between the year employment income stops and the year RMDs or benefits begin,
taxable income is **whatever you choose it to be**. Most people occupy that
position exactly once, and for a fixed number of years.

The report computes it: opens at planned retirement, closes at the earlier of
the RMD age or the claiming age. Both are birth-year dependent and both moved
recently, which is why `birth_year` is required rather than inferred from age.

## What a conversion does — three things, not one

1. Moves money into an account **never taxed again**.
2. **Shrinks the future RMD** that would otherwise be forced out, possibly at a
   higher rate, whether or not the money is needed.
3. Leaves heirs a far better asset. An inherited Roth is tax-free; an inherited
   traditional IRA is ordinary income to the beneficiary, usually within ten
   years, and often during their own peak earning period.

## Convert to fill a bracket, not to a fixed amount

Compute the headroom to the top of the target bracket each year and convert
exactly that. A fixed annual figure either wastes headroom or spills into the
next bracket, and the headroom changes every year.

Unused bracket space is not carried forward. This is the same principle as
`withdrawal-sequencing`, applied to the years where it matters most.

## The knock-ons that catch people

Conversions raise modified AGI, which:

- can raise **Medicare premiums two years later** (IRMAA), and the tiers are
  cliffs, not slopes — a dollar over a threshold costs the whole step;
- can reduce **ACA premium subsidies** for anyone retiring before Medicare
  eligibility, which is exactly the population with a conversion window;
- affects **how Social Security is taxed** once claimed.

None of this makes conversions wrong. All of it belongs in the arithmetic, and
none of it is modelled here — the report names the effects and stops.

## Two hard rules

**Pay the conversion tax from taxable funds, never from the converted amount.**
Paying from the conversion shrinks the balance that was the entire point, and
before 59½ the withheld portion is itself a penalised distribution.

**Watch the widow's tax trap.** On the first death the survivor files as
single, with roughly half the bracket width, on much the same required income.
For a couple, conversions are partly insurance against that — and it is the
argument most often left out.

## Closing

1. **The window: opens, closes, how many years.**
2. **What to convert into it** — brackets, not a figure.
3. **The knock-ons**, named, with a note that they are not modelled.
4. **Pay the tax from outside.** Say it every time.

---

*Not tax advice. Bracket thresholds, IRMAA tiers and subsidy cliffs are
year-specific — get current figures before converting.*
