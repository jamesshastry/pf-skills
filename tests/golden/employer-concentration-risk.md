# Employer concentration risk

**100% of income and 5% of investable assets depend on Northwind.** Overall severity: **severe** (income severe, assets within guideline).

|  |  |
|---|---|
| Employer-linked income | $180,000/yr |
| Held shares | $22,000 |
| Unvested pipeline | $41,000 |
| Investable assets | $423,000 |
| **Total at risk** | **$243,000** |

Unvested equity is counted as exposure but is **not** on the balance sheet — it is contingent on employment, which is the thing at risk.

## The joint scenario

Shares fall **50%** and the job ends for **12 months** — modelled together, because the event that causes one tends to cause the other.

|  |  |
|---|---|
| Value of held shares lost | $11,000 |
| Income lost over 12 months | $180,000 |
| Unvested pipeline forfeited | $41,000 |
| **Combined** | **$232,000** |
| Liquid assets after the decline | $74,000 |
| **Runway at current spending** | **9 months** |

> **Never stress-test these separately.** Two independent tests, each survivable, can describe a combined event that is not. A layoff and a share-price decline are not independent draws.

## Findings

- **100% of household income and 5% of investable assets depend on Northwind, and $243,000 in total.** These are not two exposures, they are one. The event that ends the income is the same class of event that reprices the stock, so any analysis that stress-tests them separately understates the risk.

- **Income concentration is the binding constraint here, not the portfolio.** 100% of household income comes from one employer. No amount of diversification on the asset side changes that, and it is not fixable by selling anything — the levers are a second income, a larger buffer, and not adding employer stock on top of it.

- Holdings are 5% of investable assets, within the 10% guideline. The income concentration is the remaining question.

- **No sell-at-vest policy is in force.** Vested shares are a decision made afresh every quarter, which in practice means they accumulate. Holding vested shares is mathematically identical to receiving the cash and immediately buying the employer's stock with it — an act nobody would perform deliberately at this concentration. Adopt the policy once so it stops being a recurring judgement call made under a disposition effect.

- Diversifying is not a market call. Selling does not predict the shares will fall — it declines to keep making a large undiversified bet whose downside is correlated with unemployment. If the holding would not be bought today at today's price with cash, holding it is the same decision.

## What this skill does not do

It produces a **policy**, not a transaction. Factor exposure, tax-lot selection, wash-sale timing and trade execution need positions and market data, and belong to a portfolio tool. The output here is a standing rule the household adopts once — which is the part that actually changes outcomes, because it removes a recurring decision made under pressure.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/concentration.py` with their reasons; every figure above is derived, not restated.*
