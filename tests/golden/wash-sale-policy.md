# Wash sale policy

⚠️ **1 retirement account(s) are outside the exclusion list.** A replacement purchase there disallows the loss **permanently, with no basis adjustment**.

## The window

|  | Days |
|---|---|
| Before the sale | 30 |
| After the sale | 30 |
| Total, including the day of sale | 61 |

Source: IRC §1091 and IRS Publication 550 (wash sales); Rev. Rul. 2008-5 (purchase in an IRA disallows the loss with no basis adjustment). Verification status: *unverified — check against irs.gov Publication 550*.

## Account coverage

| Account | Type | Policy applied | Loss if breached |
|---|---|---|---|
| cash | taxable | yes | deferred into the replacement's basis |
| brokerage | taxable | yes | deferred into the replacement's basis |
| retirement_401k | tax_deferred | **unknown** | **permanently disallowed, no basis adjustment** |
| college_529 | education | yes | — |

## Excluded securities

| Ticker | Reason | Sold on | Source | Purchase safe from |
|---|---|---|---|---|
| XOM | harvested_loss | <DATE> | direct_index | **never, while harvesting continues** |
| PFE | harvested_loss | <DATE> | direct_index | **never, while harvesting continues** |
| KO | harvested_loss | **unrecorded** | direct_index | **never, while harvesting continues** |

## The rule

- **The window is 30 days before the sale and 30 days after it — 61 days in total.** The half that gets missed is the one before, because a purchase that has already happened cannot be undone once the loss is taken. A dividend reinvestment, an automatic monthly contribution, or a rebalancing buy inside that window is a purchase like any other.

- **The test is *substantially identical*, not identical.** A different fund tracking the same index is the case everyone argues about; the same fund in a different account, or the fund's own ETF share class, is not arguable at all. A policy written against tickers is a policy against the easy half of the rule — write it against the exposure.

- **The rule spans every account the household controls, not just the one holding the loss.** Both spouses, every broker, every retirement account. Nothing reconciles these for you: each broker reports wash sales only within its own accounts, so a cross-broker wash sale is invisible on both 1099-Bs and the taxpayer is still the one who owes it.

- **A replacement purchase inside an IRA destroys the loss outright.** Under Rev. Rul. 2008-5 the loss is disallowed and — unlike an ordinary wash sale — **no basis adjustment is available**, because the IRA is not a taxpayer that can inherit it. An ordinary wash sale defers the loss; this one deletes it. It is the single most expensive wash-sale mistake available, and it is made by an automatic contribution nobody was watching.

- **1 retirement account(s) are not covered by the exclusion list: `retirement_401k`.** This is the finding. Every automatic contribution and every reinvested dividend in those accounts is a purchase, and if it lands on an excluded security within the window, the corresponding loss in the taxable account is gone permanently. Coverage is recorded as unknown rather than false for 1 of them, which is the same exposure: nobody has checked.

- Whether a spouse's accounts are covered is not recorded. Purchases by a spouse count; this needs an answer rather than an assumption.

- **Meridian Direct harvests continuously, so the exclusion list is not a list with an expiry date — it is a standing prohibition.** A security sold at a loss this month may be sold again next month, restarting the window each time. Treat every name on the list as permanently unbuyable everywhere else until the provider removes it, and re-pull the list on a schedule rather than at the moment of a trade.

- **What this does not do:** it does not identify losses, value them, choose replacement securities, or decide when to harvest. Those need lot-level positions and live prices and belong to a portfolio tool. This is the standing rule that tool has to obey.

## Writing the policy down

1. **Scope**: every account either spouse controls, at every broker, including IRAs, Roth IRAs, 401(k)s and HSAs.
2. **Prohibition**: no purchase of any listed security, or anything substantially identical to it, by any means — including automatic contributions, dividend reinvestment, and rebalancing buys.
3. **Duration**: until the provider removes the name. Where harvesting is continuous, treat the list as standing rather than dated.
4. **Refresh**: re-pull the list on a schedule. A list pulled at the moment of a trade is pulled too late to cover the 30 days before it.
5. **Turn off automatic reinvestment** in every account holding a listed name. It is the most common way this rule gets broken by someone who agreed to it.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/portfolio.py` with their reasons; every figure above is derived, not restated. This is a policy, not a harvest: it never identifies a loss, values one, or picks a replacement security. The weakest input is `wash_sale_policy_applied` — unrecorded coverage is treated as no coverage.*
