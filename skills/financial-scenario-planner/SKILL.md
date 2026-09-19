---
name: financial-scenario-planner
description: Run deterministic, explicitly recorded what-if events against a reconciled named cash-flow baseline and compare monthly liquidity, net worth, saving, debt, retirement timing, and recovery conditions. Use when a household wants local scenario tradeoffs without mutating its facts file, forecasting probabilities, or executing any financial action; reads a local facts file.
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
  - scenario_planning.scenarios
---

# Financial scenario planner

## The decision

Compare explicit alternatives against the unchanged baseline. Rank them only
when `scenario_planning.objective` records what the household is optimizing;
otherwise present tradeoffs without naming a winner.

## Method

Use `lib/pf/scenario.py`. Its monthly path must reconcile opening cash plus
after-tax inflows less spending, employee contributions, taxes and explicit
outflows to closing cash. Keep cash, marketable, retirement and illiquid assets
and debt separate. Transfers change composition, while costs and market changes
change net worth.

Events are typed and exhaustively dispatched. Apply their documented precedence,
reject conflicts, and surface unknown inputs. A stress is adverse by design, a
sensitivity changes one assumption, and neither is an observed fact.

## Guardrails

Never infer tax from gross income, stock basis from value, benefits from job
loss, an immediate spending cut, or automatic asset sales. A terminally solvent
path fails if it breaches cash or the reserve floor earlier. Use the shared
domain engines for emergency reserves, retirement, housing, concentration,
insurance and windfall characterization.

This skill cannot trade, transfer, sell, change elections, file forms, overwrite
facts, or assign probabilities to deterministic paths.

*Not financial, tax, or legal advice.*
