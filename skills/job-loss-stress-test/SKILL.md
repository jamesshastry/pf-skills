---
name: job-loss-stress-test
description: Stress a recorded employment-loss bundle that changes after-tax income, severance, benefits, health cost, retirement contributions, vesting, and employer stock together on the shared monthly scenario engine. Use when a household wants current- and essential-spending runway plus recovery conditions from a local facts file without treating correlated job exposures as independent shocks.
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
  - equity_comp
  - scenario_planning.scenarios
---

# Job-loss stress test

## The decision

Decide whether accessible cash survives the unemployment interval and remains
above the emergency-fund floor. A path that recovers later still fails if cash
runs out first.

## One correlated event

Use the `employment_loss` bundle in `lib/pf/scenario.py`. Salary, bonus and
equity cash income, future vesting, employer match, held employer stock and
replacement health cost belong to one event. Apply each consequence once.

Require an affected person, event month and after-tax income loss. Explicitly
mark unknown duration, severance, unemployment benefits, health cost,
contribution/match loss, unvested forfeiture and employer-stock decline. Never
infer any of them from gross pay. A permanent lower re-employment income belongs
in a following `compensation_change` event.

Show both current-spending and theoretical essential-spending runway, but do not
pretend the household achieves the spending cut unless the scenario records it.
Do not sell assets or tap retirement accounts without an explicit event.

*Not financial, tax, or legal advice.*
