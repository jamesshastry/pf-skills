---
name: cash-yield-review
description: Compare the yield on liquid holdings against a benchmark rate and quantify what idle cash is costing per year, including the state-tax treatment of Treasury interest. Use when asked about savings account rates, money market funds, where to park cash, or what to do with excess cash. Reads figures from a local facts file.
requires:
  - household.balance_sheet
---

# Cash yield review

## The rare unambiguous answer

Most personal finance involves trade-offs. This one mostly doesn't: moving cash
from an account paying near zero to a competitive money market is **the same
risk, the same liquidity, more yield.** There is no side of the trade to be
talked out of.

Which is why a large balance earning nothing is the most common unforced error
on a household balance sheet — not because it's a hard call, but because
nobody looks.

## The benchmark comes from the facts file

`assumptions.cash_benchmark_apr` is **asked for, never fetched.**

Live market data is out of scope, and a rate hard-coded into a skill goes stale
silently — producing confident nonsense in both directions depending on which
way rates moved. If the benchmark is missing, the report says so and compares
nothing.

Check the `cash_benchmark_as_of` date. A benchmark from two years ago is worse
than none.

## `tier: liquid` does not mean cash

A stock position is spendable within days, which makes it liquid. It is not a
cash-yield candidate, and asking for its yield is the wrong question.
`asset_class` keeps the review off holdings it has no business reviewing; rows
without one are reviewed as cash and flagged.

## Unknown yields are the finding

A holding with no `yield_apr` recorded means nobody has looked. The number is
on the statement. Tell the user to go and read it rather than assuming a rate —
the assumption is exactly as likely to hide the problem as to reveal it.

## Compare after tax, or the ranking can be wrong

**Interest on US Treasuries is exempt from state income tax.** Interest from a
bank account or a prime money market is not. Two vehicles with the same gross
yield are therefore not the same holding, and in a high-tax state the exemption
is frequently worth **more than the headline yield difference it is hiding
behind** — so a gross comparison can rank the wrong one first.

Supply `marginal_tax_rate`, `niit_rate` and `state_tax_rate` and the report
does the comparison properly. Supply only some of them and it falls back to
gross and says so: without the state rate the exemption cannot be valued, and
the exemption is the entire point.

## Separate the durable part from the floating part

This is the finding worth leading on, and the one a single number destroys.

A gross yield advantage is a function of where short rates happen to sit. It
can vanish next quarter. **The state-tax exemption is structural** — worth the
state rate applied to whatever the yield is — so it survives convergence.

The report splits them and values the exemption at the *lower* of the two
yields, making it a floor rather than a forecast. Quote the floor. A household
told "$860/yr" will act on a figure that is two-thirds temporary; told "$553
guaranteed, up to $860 while the spread lasts", they can decide properly.

In a state with no income tax the exemption is worth nothing, and the report
says so rather than staying silent — which is why the jurisdiction belongs in
the facts file rather than being assumed.

## The boundary worth stating

This is about **not leaving free yield on the table.** It is not about taking
risk with the buffer.

Keep the emergency fund liquid and boring. Money that has to be available on a
bad day should not be anywhere that could be down on that day, and reaching for
yield with it defeats the reason for holding it. The report closes on this
every time, because "optimise the cash" is an easy sentence to over-read.

## Closing

1. **The durable floor first**, then the total. Not the other way round.
2. **Any unknown yields**, as a "go and look" item.
3. **Before acting**: yields entered net of expenses, redemption fees checked,
   settlement confirmed. A placed order is not a held position.
4. **The boundary**: buffer stays boring.

---

*Not financial or tax advice. Rates change; keep the benchmark current.*
