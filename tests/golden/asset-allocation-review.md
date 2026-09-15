# Asset allocation review

**3 of 4 classes are outside their band**, against $395,000 of classified holdings.

## Target against actual

| Class | Target | Actual | Value | Drift | Band | Status |
|---|---|---|---|---|---|---|
| bond | 25% | 15.2% | $60,000 | -9.8% | ±5.0% | **outside** |
| cash | 5% | 21.5% | $85,000 | +16.5% | ±1.2% | **outside** |
| intl_equity | 20% | 12.7% | $50,000 | -7.3% | ±5.0% | **outside** |
| us_equity | 50% | 50.6% | $200,000 | +0.6% | ±5.0% | in band |

- $28,000 in earmarked account(s) (college_529) is excluded. Money committed to a dated obligation has its own glide path and its own deadline; counting it as household equity overstates how much risk this household can actually carry.

- **3 of 4 classes are outside their band.** Overweight: cash +16.5%. Underweight: bond -9.8%, intl_equity -7.3%. What to do about it is `rebalancing-rules`, which is a separate decision from whether the target itself is right.

## Glide path

Horizon **19 years** · reference equity band **68%–88%** · held **63%**.

- At a **19-year horizon** the reference equity share is 68%–88%. This is a convention, not a calculation: published glide paths disagree with each other by about this much at any given age, which is why it is reported as a band. Anywhere inside it is a defensible policy; the width is the honest part.

- Held equity is **63%**, below the band. Over a 19-year horizon the dominant risk is not a drawdown, it is inflation quietly removing the purchasing power of the non-equity half while it waits.

## Asset location

| Account type | bond | cash | intl_equity | us_equity | Total |
|---|---|---|---|---|---|
| tax_deferred | $60,000 | — | $50,000 | $200,000 | $310,000 |
| taxable | — | $85,000 | — | — | $85,000 |

- **Income-producing assets are already held in sheltered accounts.** This is the correct placement and worth recording as policy so that the next contribution does not quietly undo it.

- **No Roth or HSA assets are recorded.** The account whose growth is never taxed is the one that should hold the highest-expected-return assets, and this household has nowhere to put them. That is a contribution-space question before it is a location question — see `contribution-space-audit`.

- Location is worth doing **only while the allocation stays fixed.** Using it as a reason to change the mix — 'more equity because it is in the Roth' — converts a free improvement into a risk decision made for a tax reason.

## The boundary

- **This sets the policy; it does not place the trades.** Which funds, which lots, and in what order is a portfolio-tool question — see `rebalancing-rules` for whether the drift above is even worth correcting yet.
- **Balances, not market prices.** Every figure is from the facts file as of `meta.as_of`. Bands exist because the exact number does not matter; if a class is sitting on its band edge, re-read the balances before acting on it.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/portfolio.py` with their reasons; every figure above is derived, not restated. The weakest input is `account_type` on each holding: without it the location analysis cannot run at all.*
