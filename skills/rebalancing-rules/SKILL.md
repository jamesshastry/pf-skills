---
name: rebalancing-rules
description: Decide band versus calendar rebalancing as a standing rule rather than a repeated judgement, compute current drift per asset class against 5-absolute/25-relative bands, and size how much of the correction can be made without realising a taxable gain. Use when asked how often to rebalance, whether the portfolio needs rebalancing now, what a rebalancing band should be, or how to rebalance without a tax bill. Reads balances from a local facts file.
requires:
  - household.balance_sheet
  - portfolio.target_allocation
---

# Rebalancing rules

## The idea

Rebalancing is not a decision to make each time. It is a **rule to adopt once**,
so that the next time the portfolio has moved, nothing has to be decided at all.

A household without a rule does not rebalance less often — it rebalances
whenever it happens to look, which is correlated with markets having moved
sharply, which is the worst available trigger.

## Bands or calendar. Either. Not neither.

| | Bands | Calendar |
|---|---|---|
| Trigger | The portfolio moves past a threshold | The date arrives |
| Trades when nothing has moved | No | Yes |
| Misses a move between checks | Only up to the check interval | Yes, for up to a year |
| Still needs a cadence | Yes — check quarterly | The cadence *is* the rule |
| Failure mode | Checking too often turns into market-watching | Rebalancing on a date that happens to be a bad one |

The calendar rule's real virtue is that the **date decides, not the portfolio**,
so it cannot become market timing. The band rule's is that it acts when
something has actually happened. Both are defensible. Not choosing is not.

## The band: 5 absolute or 25 relative, whichever binds first

Both numbers are constants in `lib/pf/portfolio.py` with their reasons, and
each covers the other's blind spot:

- **5 percentage points absolute.** Below this, the tracking error against the
  target is smaller than the spread, the tax, and the chance of being wrong
  about the target in the first place.
- **25% of the class's own target.** A 5pp absolute band can never fire on a
  class targeted at 5% — it would have to vanish entirely and still not breach.
  The relative band is what governs small sleeves.

The tighter of the two applies per class. For a 50% target that is the absolute
band; for a 5% target it is 1.25pp.

## The finding that costs real money

**A correction made in a taxable account realises gains. The same correction
made inside a 401(k) or an IRA costs nothing.**

So the rule is not "rebalance" — it is an ordering, and most households run it
backwards because the taxable account is the one they look at:

1. **New contributions** directed to the underweight class. Corrects drift
   without selling anything.
2. **Dividends and interest redirected** rather than automatically reinvested.
3. **Sales inside sheltered accounts** — tax-deferred, Roth, HSA. Not a taxable
   event, so the correction is free there.
4. **Cash**, in any account. Its basis is its value; selling it realises
   nothing.
5. **Taxable sales, last.** This is the only step with a tax attached.

The report sizes each layer and tells you how much, if any, has to come from
step 5. When that figure is zero, the whole correction is free — and that is
worth knowing *before* deciding whether the drift is tolerable.

## Tolerating drift is a legitimate answer

The band is a band, not a target. If restoring the last two percentage points
requires a taxable sale, the honest comparison is the tax paid now against the
tracking error avoided — and the tracking error frequently loses. The report
says the size of the taxable portion rather than instructing you to pay it.

## What it will not do

- **It does not choose lots.** Which tax lots to sell, their holding periods,
  and the gain on each need lot-level data and belong to a portfolio tool.
- **It does not harvest losses, and it does not check wash sales.** If the
  household has an exclusion list, a rebalancing *buy* can trigger a wash sale
  — see `wash-sale-policy`, which is the rule this plan has to obey.
- **It does not set the target.** That is `asset-allocation-review`.
- **It does not use market prices.** Drift is computed from recorded balances
  as of `meta.as_of`. If a class is sitting on its band edge, re-read the
  balances before acting.

## Closing

1. **Whether the rule fires**, and on which classes.
2. **The size of the correction**, and how much of it is free.
3. **The taxable remainder**, as a number to weigh — not an instruction.
4. **The policy itself**, if one is not recorded. That is the actual gap.

---

*Not financial, tax, or legal advice.*
