---
name: asset-allocation-review
description: Compare the household's recorded target allocation against what it actually holds, check the equity share against a horizon-based glide path, and review asset location — which account type holds which asset class. Use when asked about target allocation, how much should be in stocks or bonds, glide paths, whether the portfolio has drifted, or where a particular asset class should be held. Reads balances from a local facts file.
requires:
  - household.balance_sheet
  - portfolio.target_allocation
---

# Asset allocation review

## The idea

An allocation is a **policy**: a mix the household decided on once, in a calm
moment, with reasons. Everything afterwards is either honouring it or quietly
departing from it. This report says which.

It asks three questions, and the third is the one nobody asks:

1. **What is the target, and what is actually held?**
2. **Does the equity share match the horizon?**
3. **Which account type holds which asset class?**

## The target is recorded, never inferred

`portfolio.target_allocation` is read from the facts file. The report will not
reverse-engineer a target from current holdings, because that makes drift
definitionally zero and turns the review into a description.

A target that does not sum to 100% is reported as a recording error and is
**not renormalised** — scaling it silently would invent a policy nobody chose.

## Unknown is not "other"

A holding with no `asset_class` is excluded from every figure, *including the
denominator*, and named in the report. Folding it into an "other" bucket would
produce a tidy table that is wrong in a direction no reader can see.

Earmarked money — a 529 against a dated education obligation — is excluded on
purpose. It has its own glide path and its own deadline, and counting it as
household equity overstates how much risk the household can carry.

## The glide path is a band, not a number

The reference equity share is built from **horizon, not age**. Age is a proxy
for horizon and a poor one: two forty-year-olds retiring at 55 and at 70 have
very different capacities to wait out a drawdown, and the age-based rules of
thumb get the second one wrong.

It is reported as a ±10pp band because published glide paths disagree with each
other by about that much at any given age. Anywhere inside the band is a
defensible policy. **The width is the honest part** — a single number invites
the household to treat a convention as a calculation.

Inside ten years of the target date, the report changes the question. Sequence
of returns, not expected return, becomes the thing the allocation has to
survive, and a point estimate of equity share does not answer it.

## Asset location is the free one

Moving a bond fund from a taxable account into a 401(k) changes **nothing**
about the household's risk and everything about its after-tax return. That is
exactly why it goes unexamined: no number on any statement moves.

The ordering the report checks:

| Asset | Where it belongs | Why |
|---|---|---|
| Bonds, REITs — income-producing | Tax-deferred | Ordinary income taxed annually whether or not you sell; sheltering it removes a drag that recurs every year |
| Highest expected return | Roth or HSA | Growth there is **never** taxed, so a dollar of return is worth more in that account than in any other |
| Broad equity | Taxable | Long-term rates, control over realisation, the step-up at death, and it is the only account where a loss is usable |

Two cautions the report carries every time:

- It is worth doing **only while the allocation stays fixed.** "More equity
  because it is in the Roth" converts a free improvement into a risk decision
  taken for a tax reason.
- Location can only be judged where `account_type` is recorded. Without it,
  half this report is unavailable — and that is the weakest input here.

## What it will not do

- **No market data, no prices, no holdings lookup.** Every figure comes from
  balances already written down.
- **No trades.** It does not say which funds to buy, which lots to sell, or
  when. That needs lot-level positions and belongs to a portfolio tool.
- **No view.** It compares what is held against what was decided. It has no
  opinion on whether equities are expensive.
- **It does not size the correction's tax cost** — `rebalancing-rules` does.

## Closing

1. **Where the drift is**, and which classes are outside their band.
2. **Whether the equity share and the horizon agree**, as a band.
3. **The location swap**, if there is one — the same risk for more money.
4. **The boundary**: policy here, execution elsewhere.

---

*Not financial, tax, or legal advice.*
