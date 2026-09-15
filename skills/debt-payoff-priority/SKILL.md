---
name: debt-payoff-priority
description: Order debts for payoff and price the difference between the avalanche and snowball methods in dollars, on an after-tax basis, including the compare-against-investing question. Use when asked which debt to pay first, whether to pay off a loan early or invest instead, or how to structure a payoff plan. Reads figures from a local facts file.
requires:
  - debts
---

# Debt payoff priority

## Show both, price the difference

Most treatments of this pick a side. **Avalanche** (highest rate first)
minimises interest and is mathematically correct. **Snowball** (smallest
balance first) closes accounts sooner and is the one people actually finish.

This skill runs both and states the cost of the difference in dollars.

That number is usually small, and it is the only honest way to present the
choice. If snowball costs a few hundred dollars and is the plan that gets
completed, **it is the better plan.** Telling someone their preference is
irrational, and then watching them abandon the optimal schedule in month four,
helps nobody.

Guidance: pick avalanche when the gap is large or the rates are far apart. Pick
snowball when past attempts have stalled. Above all, don't let the choice
itself become the reason nothing starts.

## After-tax, or the ordering can be wrong

Deductible interest is not comparable to non-deductible interest at the same
headline rate. A 7% deductible loan costs 5.32% after tax at a 24% marginal
rate — **below** a 6% non-deductible one that looks cheaper on the sticker.

The avalanche ordering uses after-tax rates for exactly this reason. The report
shows both columns so the inversion is visible rather than mysterious.

## Both simulations roll freed minimums forward

When a debt clears, its minimum payment joins the pool attacking the next
target. Both methods do this — otherwise the comparison would be unfair to
whichever method happens to clear a large minimum first, and the reported gap
would be an artefact of the model rather than of the ordering.

## The third option

Not accelerating at all, and investing instead. The report makes this
comparison only when `assumptions.expected_return_apr` is supplied — it is
skipped rather than assumed.

**State the asymmetry when you present it.** The arithmetic compares a
*certain* return against an *uncertain* one, which is not like-for-like. Paying
down debt is risk-free and irreversible; investing is neither. Reasonable
people take the guaranteed return even when the expected value favours
investing, and that is a preference, not an error. Say so rather than pushing.

Above about 15%, the debate is academic — those rates beat essentially any
investment on a risk-adjusted basis.

## When the schedule doesn't terminate

If minimum payments don't cover interest, balances grow forever and the
simulation says so instead of looping.

This is important to name clearly: it is a **restructuring problem, not an
ordering one.** The question stops being which debt to target and becomes how
to increase total payment or renegotiate terms. Offering an ordering here would
be answering the wrong question politely.

## Closing

1. **Both orderings, with the dollar cost of choosing snowball.**
2. **A recommendation**, not a menu — but one that respects the preference.
3. **The invest-instead comparison** if the assumption was supplied, with the
   certainty asymmetry stated.
4. **One next action**, which is usually "set the extra payment up as a
   standing transfer."

## Out of scope

Refinancing and consolidation options, credit-score effects, and negotiation
with creditors. Mortgage payoff strategy interacts with housing decisions —
see cluster 8 when it lands.

---

*Not financial or tax advice.*
