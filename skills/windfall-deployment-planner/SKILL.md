---
name: windfall-deployment-planner
description: Compare cash, investing, debt payoff, home funding, or split uses of a recorded windfall after its tax reserve and decision pause, using the shared monthly scenario engine. Use after windfall-management has characterized a receipt in a local facts file, or for an explicitly labeled preliminary comparison; never treat gross stock value or unknown basis as spendable cash.
requires:
  - meta.as_of
  - meta.currency
  - household.members
  - household.balance_sheet
  - household.annual_spending
  - debts
  - cash_flow.scenarios
  - housing.status
  - housing.monthly_rent
  - retirement.annual_savings
  - transitions.windfall
  - scenario_planning.scenarios
---

# Windfall deployment planner

## The decision

After `windfall-management` establishes the receipt's character, tax reserve,
reporting exposure and decision-pause date, compare explicit uses of the net
amount. If the pause is live, block deployment unless the scenario says
`preliminary: true`—and label that result preliminary.

## Cash is not stock

A cash receipt needs an explicit after-tax amount or gross amount plus reserve.
A stock receipt remains a marketable asset unless an explicit liquidation has
known basis, tax rate and transaction cost. Unknown basis never becomes zero,
and gross market value is never labeled investable cash.

Use the shared scenario engine for holding cash, portfolio contribution, debt
payoff, home purchase and split alternatives. Transfers change liquidity and
asset composition, not net worth; tax, transaction and closing costs reduce net
worth. Rank only for a recorded objective.

Do not recommend securities, pick tax lots, waive the pause, execute a trade,
or overwrite facts. Hand execution and wash-sale review to the portfolio and tax
workflows.

*Not financial, tax, or legal advice.*
