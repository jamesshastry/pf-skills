---
name: rent-vs-buy
description: Compare the economic cost of renting versus owning at an already-feasible purchase price, including transaction costs, opportunity cost, terminal equity, and the break-even year. Use when choosing between feasible rent and buy options or testing a holding period; do not use to answer how much home is affordable. Reads figures from a local facts file.
requires:
  - housing.monthly_rent
  - housing.purchase
---

# Rent vs buy

**This compares the economics of renting and buying; it does not determine
affordability.** Run `housing-affordability` first to identify feasible prices,
then use this skill to compare those choices.

## The comparison everyone makes is the wrong one

**Monthly mortgage payment against monthly rent is meaningless.** The payment
is not the cost of owning. Most of the cost is in lines that never appear on a
mortgage statement: property tax, insurance, maintenance, and the cost of
getting in and out.

The report compares **total cost of occupancy over a holding period** instead,
and it makes two corrections in opposite directions that are both usually
missed:

- **Principal repayment is not a cost.** It converts cash into equity. Counting
  it as a cost is the standard error in the pro-renting direction.
- **Every dollar spent has an opportunity cost, not just the down payment.**
  Both sides are carried forward to the horizon at the investment return.
  Summing undiscounted cash flows over decades treats a dollar in year 30 as
  equal to a dollar today, and since owning front-loads cost and back-loads
  benefit, that error flatters buying. An earlier version of this skill made
  it and reached the opposite conclusion to a careful hand analysis.

## The answer is a break-even holding period

Buying is rarely right or wrong in general. It is right or wrong **for how long
you stay.**

Selling costs alone run around 6% of price, and that single line is why short
holds lose — it does not shrink if the market moves against you. Lead with the
break-even year and let the household compare it against how long they actually
expect to be there, which they know better than any model.

## Nominal throughout, and it must stay that way

Unlike the retirement skills, this one works in **nominal** terms, because the
mortgage rate is inherently nominal and converting it would obscure the one
number the household actually knows.

That means every other input must be nominal too. In particular:

> **Zero real appreciation is expressed as appreciation equal to rent growth,
> not as zero.**

Setting nominal appreciation to zero silently assumes houses fall in real terms
every single year, which decides the answer on its own.

This is not hypothetical. An early version of this module took its investment
return from `assumptions.expected_return_apr` — a nominal figure, since it
exists to be compared against nominal debt rates — and applied it as a real
return against zero nominal appreciation. Buying never broke even, in forty
years, at any price. Same defect class as mixing real and nominal in a
retirement projection; it just hides better here because a mortgage rate looks
like a hard fact. A regression test now guards it.

## Calibration

The crossover sits at a price-to-rent ratio of about **15** at a 7% alternative
return — essentially the conventional boundary. Worth knowing, because a model
that lands far from it is miscalibrated and will look biased whichever way it
leans. There is a test pinning this.

Two useful reference points: at P/R 18 the model says rent; at P/R 12 it says
buy. If a household's ratio is near 15, the answer turns on the assumptions
rather than on the arithmetic, and you should say so.

## No forecast is baked in

Appreciation is a **dial, not a prediction**. The default is zero real. If the
household wants to assume appreciation, set it explicitly and then show how
much of the conclusion depends on it — if the answer flips on a one-point
change, that is the finding.

When either growth input is overridden, the report shows the implied real
spread (appreciation minus rent growth) next to the inputs, and flags it when
the override moves off the default spread. Moving one side without the other
is usually accidental — lowering rent growth while holding appreciation fixed
raises the real view without saying so.

## What it doesn't model

Mortgage interest and property tax deductibility, which depend on whether the
household itemises. The risk of being unable to relocate for work. Security of
tenure. The forced-savings behavioural effect of a mortgage, which is real and
not financial.

Say these are excluded rather than pretending the number is complete.

## Closing

1. **The break-even year**, first.
2. **The cost table**, so the conclusion is checkable line by line.
3. **The assumptions that could flip it** — appreciation and holding period.
4. **The non-financial factors**, named but not priced.

---

*Not financial advice. Nominal throughout; the appreciation input is an
assumption, not a forecast.*
