---
name: aca-subsidy-optimization
description: Size the years between retiring and Medicare that must be funded on the individual market, compute the premium tax credit against modified AGI as a percentage of the federal poverty level, and quantify what an extra dollar of MAGI costs. Detects and reports the direct conflict with roth-conversion-window, which tells the same household to raise MAGI in exactly those years. Use when asked about early retirement health insurance, ACA subsidies, premium tax credits, the 400% cliff, or how much income to show before 65. Reads figures from a local facts file.
requires:
  - household.members
  - retirement.planned_retirement_age
---

# ACA subsidy optimization

## The idea

Retire before 65 and health cover stops being a line item and becomes **a
constraint on income**. The premium tax credit is computed from modified AGI as
a percentage of the federal poverty level, so in the gap years the household is
choosing its own subsidy every time it decides where a dollar of spending comes
from.

That is a different kind of planning problem from the one a retirement
projection solves. A projection asks whether the money lasts. This asks what
the money is allowed to *look like* while it does.

## The conflict this skill exists to surface

`roth-conversion-window` is already shipped. It tells a household to
**deliberately raise** taxable income after retiring, to fill brackets that
would otherwise go empty before RMDs begin.

This skill tells the same household to **suppress** modified AGI, because the
credit tapers and — when the 400% cliff is in force — falls off entirely.

For anyone retiring before 65 these are **the same calendar years**. Two skills
in this repository, each individually correct, give opposite instructions about
one number. The report computes the overlap from
`retirement.conversion_window` and names it as a conflict rather than leaving
the reader to notice.

Review finding A6, and the reason this skill was built with the detection
rather than after it.

## The resolution is a sequence, not a choice

The useful output is not "there is a tension". It is the **partition**: the
conversion window splits into segments by which constraint binds, and they cost
very different amounts to convert in.

| Segment | What binds | Cost of a conversion dollar |
|---|---|---|
| Retirement → 63 | ACA subsidy only | Income tax **plus the taper rate** |
| 63 → 65 | Subsidy *and* IRMAA lookback | Both, on the same dollar |
| 65 → window close | IRMAA only | Income tax plus a bounded annual step |

The unconstrained years, where they exist, go first. The IRMAA-only years go
second, because an IRMAA step is a known surcharge for one year and a subsidy
cliff is the whole credit. The doubly-constrained years go last and least.

**This ordering is not a recommendation to convert.** It says that if
conversions happen, this sequence is strictly cheaper than converting evenly —
which is what a bracket-filling rule read on its own produces.

## The taper is a marginal tax rate nobody lists

Between the floor and the cliff, each additional dollar of MAGI raises the
expected contribution and reduces the credit one-for-one. That is an effective
marginal rate, it stacks on top of the income-tax bracket, and it appears in no
bracket table. The report computes it and adds it to the 12% and 22% brackets so
the real rate on a conversion is visible.

Where the cliff is in force, the **headroom to the cliff is the hard ceiling on
a conversion** — not the top of a bracket. One dollar over costs the entire
remaining credit. That number is the most actionable figure in the report.

## MAGI can also be too low

Advice to keep income down has a floor, and it is rarely mentioned. Below 100%
of FPL there is no credit at all: in a state that expanded Medicaid the
household routes to Medicaid instead, and in one that did not it lands in the
coverage gap — too poor to subsidise, too rich for Medicaid.

Suppressing MAGI below the expansion level does not buy a bigger credit. It
changes programme.

## Every year-specific figure is refused

Poverty levels, the applicable-percentage schedule, the benchmark silver
premium, and **whether the 400% cliff applies at all** come from
`assumptions.*` in the facts file. None of them lives in this repository.

Review finding A3 records `limits.py` as an unverified mirror of the tax code
that must not grow before it is verified, and the subsidy parameters are the
worst possible candidate for an unverified table: the taper means an error in
the poverty level compounds rather than cancels, and the cliff means an error
near 400% inverts the advice.

If they are missing, the report states the structure, names what is missing, and
computes nothing. The conflict detection still runs — its existence does not
depend on the figures.

## The MAGI definition is not the one you think

For the premium tax credit it is AGI plus tax-exempt interest, plus untaxed
Social Security, plus excluded foreign earned income. The tax code contains
several MAGIs and they are routinely conflated. The tax-exempt interest add-back
in particular catches households holding municipal bonds *for the purpose* of
keeping income down.

## What it will not do

- Price plans, compare networks, or say which metal tier to buy. The credit is
  computed against the benchmark silver plan whether or not you buy it.
- Model cost-sharing reductions, which are a separate silver-only subsidy with
  their own FPL bands.
- Decide whether to convert. It prices the conflict; the decision needs bracket
  figures this repository does not hold.
- Tell you your state's Medicaid expansion status. Supply it.

## Closing

1. **The gap** — how many years, at what ages.
2. **The credit**, or an explicit refusal with the missing inputs named.
3. **The conflict**, quantified as a marginal rate and a cliff headroom.
4. **The sequence** — which years are cheap to convert in and which are not.
5. **The reconciliation warning.** Estimate MAGI high; the excess is repayable.

---

*Not financial, tax, or legal advice. Subsidy parameters change annually and
the 400% cliff has been suspended and restored — confirm both for the plan year
before acting.*
