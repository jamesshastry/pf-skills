# Rebalancing rules

**The rule fires.** 4 class(es) breached their band; $67,750 of buying restores the target, of which **$0 would require a taxable sale**.

## Drift against the bands

| Class | Target | Actual | Drift | Band | Binds | Trade |
|---|---|---|---|---|---|---|
| bond | 25% | 15.2% | -9.8% | ±5.0% | absolute | buy $38,750 |
| cash | 5% | 10.1% | +5.1% | ±1.2% | relative | sell $20,250 |
| intl_equity | 20% | 12.7% | -7.3% | ±5.0% | absolute | buy $29,000 |
| us_equity | 50% | 62.0% | +12.0% | ±5.0% | absolute | sell $47,500 |

The band is **5% absolute or 25% relative, whichever binds first** — the tighter of the two, per class.

## The rule

- **Band policy: 5% absolute or 25% relative, whichever binds first.** Checked every 3 months. The absolute band alone never fires on a small sleeve — a class targeted at 5% would have to disappear entirely — and the relative band alone tolerates a 12.5pp move in a 50% class. Each covers the other's blind spot.

- **The review is overdue** — due <DATE>, 121 days ago. A rule nobody runs is indistinguishable from no rule.

- **$67,750 of buying and $67,750 of selling would restore the target** — about 17.2% of the portfolio. That is the size of the correction, not an instruction: which holdings and which lots is a portfolio-tool question and deliberately not answered here.

- **Direct the next $34,000 of contributions to the underweight classes first.** Buying with new money corrects the drift without selling anything, which means without realising a single dollar of gain. At $34,000/yr of contributions this covers 50% of it.

- **The whole correction can be made without realising a taxable gain**, using contributions, sheltered accounts, and cash. Selling inside a tax-deferred or Roth account is not a taxable event, so the correction is free there; doing the identical trade in the taxable account is not.

- **Order of operations, in cost order:** new contributions → dividends and interest redirected rather than reinvested → sales inside sheltered accounts → cash → taxable sales last. Most households run this list backwards because the taxable account is the one they look at.

- Next scheduled check: **<DATE>** (passed).

## Decide it once

| | Bands | Calendar |
|---|---|---|
| Trigger | The portfolio moves | The date arrives |
| Trades when nothing moved | No | Yes |
| Misses a move between checks | Only up to the check interval | Yes, for up to a year |
| Needs a check cadence anyway | Yes — 3 months | The cadence *is* the rule |
| Failure mode | Checking too often becomes market-watching | Rebalancing on a date that happens to be a bad one |

Either beats the third option, which is what happens by default: the decision gets made afresh whenever someone opens the account, which is the moment when it is hardest to make well.

- $28,000 in earmarked account(s) (college_529) is excluded. Money committed to a dated obligation has its own glide path and its own deadline; counting it as household equity overstates how much risk this household can actually carry.

- **4 of 4 classes are outside their band.** Overweight: cash +5.1%, us_equity +12.0%. Underweight: bond -9.8%, intl_equity -7.3%. What to do about it is `rebalancing-rules`, which is a separate decision from whether the target itself is right.


---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/portfolio.py` with their reasons; every figure above is derived, not restated. Trade sizes are the size of the correction, not an order list — which lots to sell, and the tax on each, is a portfolio-tool question.*
