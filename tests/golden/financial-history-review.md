# Financial history review

**Observed facts, historical analyses, and projections remain three separate clocks.** No row below combines them.

## Material comparable changes

| Metric | Clock / case | Beginning | Ending | Change | % | Driver | Unexplained |
|---|---|---|---|---|---|---|---|
| `retirement.target` | analysis / current | USD 2,405,714 | USD 2,491,429 | USD 85,715 | 3.6% | household | USD 85,715 |
| `household.net_worth` | observed / observed | USD 305,000 | USD 370,000 | USD 65,000 | 21.3% | household | USD 65,000 |
| `housing.cash_flow_price_ceiling` | analysis / current | USD 481,000 | USD 498,000 | USD 17,000 | 3.5% | household | USD 17,000 |
| `household.asset_balance` | observed / observed | USD 80,000 | USD 95,000 | USD 15,000 | 18.8% | household | USD 15,000 |
| `household.asset_balance` | observed / observed | USD 19,000 | USD 25,000 | USD 6,000 | 31.6% | household | USD 6,000 |
| `housing.cash_flow_price_ceiling` | analysis / conservative | USD 337,000 | USD 342,000 | USD 5,000 | 1.5% | household | USD 5,000 |
| `emergency_fund.months_held` | analysis / current | 4.0 months | 6.0 months | 2.0 months | 50.0% | household | 2.0 months |

## Period tables

### `emergency_fund.months_held` · analysis / current

| Effective | Calculated | Value | Source | Model |
|---|---|---|---|---|
| <DATE> | <DATE> | 4.0 months | emergency-fund-sizing | pf-skills-v1 |
| <DATE> | <DATE> | 5.1 months | emergency-fund-sizing | pf-skills-v2 |
| <DATE> | <DATE> | 6.0 months | emergency-fund-sizing | pf-skills-v2 |

### `household.asset_balance` · observed / observed · `acct-bond`

| Effective | Calculated | Value | Source | Model |
|---|---|---|---|---|
| <DATE> | — | USD 19,000 | household.balance_sheet | observed |
| <DATE> | — | USD 25,000 | household.balance_sheet | observed |

### `household.asset_balance` · observed / observed · `acct-brokerage`

| Effective | Calculated | Value | Source | Model |
|---|---|---|---|---|
| <DATE> | — | USD 80,000 | household.balance_sheet | observed |
| <DATE> | — | USD 85,000 | household.balance_sheet | observed |
| <DATE> | — | USD 90,000 | household.balance_sheet | observed |
| <DATE> | — | USD 95,000 | household.balance_sheet | observed |

### `household.asset_balance` · observed / observed · `acct-fx`

| Effective | Calculated | Value | Source | Model |
|---|---|---|---|---|
| <DATE> | — | USD 50,250 | foreign statement converted to USD | observed |

### `household.asset_balance` · observed / observed · `acct-fx`

| Effective | Calculated | Value | Source | Model |
|---|---|---|---|---|
| <DATE> | — | USD 53,100 | foreign statement converted to USD | observed |

### `household.net_worth` · observed / observed

| Effective | Calculated | Value | Source | Model |
|---|---|---|---|---|
| <DATE> | — | USD 305,000 | household.balance_sheet+debts | observed |
| <DATE> | — | **unknown** | household.balance_sheet+debts | observed |
| <DATE> | — | USD 340,000 | household.balance_sheet+debts | observed |
| <DATE> | — | USD 370,000 | household.balance_sheet+debts | observed |

### `housing.cash_flow_price_ceiling` · analysis / conservative · `cash-conservative`

| Effective | Calculated | Value | Source | Model |
|---|---|---|---|---|
| <DATE> | <DATE> | USD 337,000 | housing-affordability | pf-skills-v1 |
| <DATE> | <DATE> | USD 342,000 | housing-affordability | pf-skills-v2 |

### `housing.cash_flow_price_ceiling` · analysis / current · `cash-current`

| Effective | Calculated | Value | Source | Model |
|---|---|---|---|---|
| <DATE> | <DATE> | USD 481,000 | housing-affordability | pf-skills-v1 |
| <DATE> | <DATE> | USD 498,000 | housing-affordability | pf-skills-v2 |

### `retirement.target` · analysis / current

| Effective | Calculated | Value | Source | Model |
|---|---|---|---|---|
| <DATE> | <DATE> | USD 3,120,000 | retirement-readiness-sensitivity | pf-skills-v2 |

### `retirement.target` · analysis / current

| Effective | Calculated | Value | Source | Model |
|---|---|---|---|---|
| <DATE> | <DATE> | USD 2,405,714 | retirement-readiness | pf-skills-v1 |
| <DATE> | <DATE> | USD 2,491,429 | retirement-readiness | pf-skills-v2 |

## Finding transitions

| Finding | From | To | Driver | Reason |
|---|---|---|---|---|
| `skill.employer.concentration.risk.verdict` | open | worsened | **methodology** | Model now includes the income side |
| `skill.employer.concentration.risk.verdict` | worsened | closed | household | Household sold vested employer shares |

## Deliberately kept separate

- household.asset_balance has separate series: observed/observed/USD-nominal, observed/observed/USD-nominal/{'fx_date': '<DATE>', 'source_currency': 'CAD'}, observed/observed/USD-nominal/{'fx_date': '<DATE>', 'source_currency': 'CAD'}
- housing.cash_flow_price_ceiling has separate series: analysis/conservative/USD-nominal, analysis/current/USD-nominal
- retirement.target has separate series: analysis/current/USD-nominal, analysis/current/USD-real

## Data gaps

- household.net_worth at <DATE>: partial snapshot cannot support a household total

Changes without recorded flows remain unexplained residuals. No partial period was annualized and no missing date was carried forward.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/timeseries.py` with their reasons; every figure above is derived, not restated.*
