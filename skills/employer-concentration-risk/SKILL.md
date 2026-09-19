---
name: employer-concentration-risk
description: Measure a household's combined dependence on one employer — income, held shares, and the unvested pipeline treated as a single correlated exposure — and model the joint scenario where the share price falls and the job ends together. Produces a standing policy, not a trade. Use when asked about company stock concentration, whether to sell vested shares, or single-employer risk. Reads figures from a local facts file.
requires:
  - household.members
  - household.balance_sheet
  - household.annual_spending
  - equity_comp
---

# Employer concentration risk

## One bet, not two

Salary, bonus, vesting equity, held shares, and the unvested pipeline are all a
position in the same company. **The event that ends the income is the same
class of event that reprices the stock.**

This is why the skill refuses to run two separate stress tests. A layoff test
and a market-decline test, each individually survivable, can describe a
combined event that is not — and separate tests will always look reassuring
because each is only half the loss.

The report models them jointly: shares fall by half, the job ends for a year,
the unvested pipeline evaporates. That is not a tail scenario. It has happened
to most well-known employers, and the three events are the *same* event.

## Unvested equity is exposure, not an asset

It never appears on the balance sheet — it is contingent on continued
employment, which is precisely the thing at risk. Counting it as net worth
inflates the balance sheet using the asset most likely to disappear in the
scenario that matters.

But it must be counted as *exposure*, because losing it is part of the loss.

## The output is a policy

**`sell_at_vest` is the highest-leverage field here**, because it converts a
recurring quarterly judgement into a decision made once.

The framing that lands: *holding vested shares is mathematically identical to
receiving the cash and immediately buying the employer's stock with it.* Nobody
would perform that act deliberately at high concentration — but not-selling
feels different from buying, and that asymmetry is what lets the position grow.

Two supporting arguments worth having ready:

**Diversifying is not a market call.** Selling doesn't predict the shares will
fall. It declines to keep making a large undiversified bet whose downside is
correlated with unemployment.

**The buy-today test.** If the household wouldn't buy this position today, at
today's price, with cash — holding it is that same decision.

## The boundary, which matters most here

This skill answers *how exposed, and what standing rule.* It does **not**
compute factor exposures, select tax lots, time trades, or handle wash sales.
Those need positions and market data and belong to a portfolio tool.

Say so explicitly in the output. The temptation to drift across that line is
strongest in this skill, and two codebases holding two versions of the same
rule is exactly what this project is organised to prevent.

## Closing

1. **The two percentages together** — income share and asset share — because
   either alone understates it.
2. **The joint scenario**, with runway in months.
3. **The policy question**, not a trade recommendation.
4. **Hand off** the execution question, with the seam named.

## Time-series output

Emit income share, asset share, joint loss, and runway with the recorded stress
assumptions. A changed model version must not be described as diversification.

---

*Not financial or tax advice. Selling concentrated positions has tax
consequences this skill does not model.*
