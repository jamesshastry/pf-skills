---
name: geo-arbitrage-model
description: Blend the annual burn rate across a split-living arrangement — months in each location, costs that do not move — and compute the location-adjusted portfolio target and the years it saves, stressed for currency risk and checked against residency day tests. Use when part of the year would be spent in a cheaper country, when retiring abroad is being costed, or when a lower cost of living is being counted on to make a retirement plan close. Reads figures from a local facts file.
requires:
  - crossborder.locations
  - household.balance_sheet
  - retirement.annual_savings
---

# Geo arbitrage model

## The idea

Spending is the strongest lever in retirement planning, and location is the
strongest lever on spending. At a 4% withdrawal rate **every dollar off the
annual burn takes twenty-five dollars off the portfolio target** — so a split
year that moves the burn by five figures moves the target by six, and usually
moves the retirement date by years.

That multiplier is the whole reason this is worth modelling rather than
estimating. It also means an error in the burn rate is amplified twenty-five
times, which is why most of this skill is about what would make the blended
figure wrong.

## The arithmetic is rigorous; the tax content around it is not

This is the deliberate split in this cluster. Blended burn rates, targets and
years-to-target are exact arithmetic on figures you supply, reusing
`retirement.target_for` and `retirement.years_to` — **the same machinery as
`retirement-readiness`, imported rather than reimplemented**, so a
location-adjusted target and an ordinary one cannot drift apart.

Everything about what a foreign revenue authority will do is refused or flagged.

## Three numbers, and the third is the planning figure

| Scenario | What it is |
|---|---|
| Full year at the dearest location | What you would spend not doing this — the honest baseline |
| Blended, as planned | The headline |
| Blended, with a 20% adverse currency move | **The planning figure** |

**The saving is denominated in a currency you neither earn nor hold.** A fifth
is an ordinary decade for a major-to-emerging pair, and it gives back a large
share of what the move bought. That is the weakest input in the model:
everything else is arithmetic on your own figures, and this is a guess about
exchange rates over decades. Quote the stressed row.

## What makes the blended figure wrong

Four checks, each of which has silently inflated a saving:

**Months that do not add to twelve.** Eleven months of legs is a year with a
month of unaccounted living costs. The model reports the gap as a range between
the cheapest and dearest leg and **refuses to spread it for you** — which leg
it belongs to changes the answer, and only you know.

**Housing paid in both places.** A split-living arrangement frequently carries
rent or ownership costs in both locations for all twelve months while occupying
one. That can erase most of the saving. Unrecorded means *cannot be
determined*, not *no*.

**Local inflation.** Not modelled. A constant real cost differential over
decades is an assumption, not a finding.

**Healthcare.** Not in these numbers, and usually the largest single line. See
`cross-border-healthcare` before treating the saving as spendable.

## The residency side-effect

A plan built for cost reasons has a tax consequence nobody chose. Five months
somewhere is comfortably under a 182-day threshold — and can still trigger a
**60-day-plus-365-over-four-years** test, which is exactly the rule that
catches a repeated seasonal arrangement.

So the model estimates days per leg and flags any that cross, or come within
three weeks of, a day test recorded in the country table. Travel plans slip by
more than three weeks routinely and the tests have no tolerance.

Two limits on that flag, both stated in the output: the estimate is months ×
30.44, not a count — **keep a contemporaneous travel log** — and the table
holds only the United States and India, so an unrecorded country produces "find
the threshold", not silence.

## What it will not do

It will not decide whether you are tax resident anywhere, model local
inflation, price healthcare, or convert currency at a rate it invented.

And it will not ask whether you want to live this way. Two households a year,
two sets of friendships, and a permanent travel schedule are the real cost of a
split arrangement, and no model here captures them.

## Closing

1. **The stressed target**, not the headline one.
2. **The years saved**, which is what the household actually feels.
3. **Any day test flagged** — a cost decision that quietly created a tax
   residency is the expensive failure mode here.
4. **What is not in the number**: healthcare, duplicate housing, local
   inflation.

---

*Not financial, tax, or legal advice. Figures are real — today's money — throughout. Tax
residency consequences of a split-living arrangement need a cross-border professional.*
