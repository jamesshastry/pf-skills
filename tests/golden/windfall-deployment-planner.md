# Windfall deployment planner

## Decision pause

`windfall-management` reports a live 90-day pause. Non-preliminary deployment cases are blocked.
The remaining cases are explicitly **preliminary**; they are planning comparisons, not permission to act.

## Deployment comparison

| Case | Receipt form | Spendable receipt | Min cash | Terminal cash Δ | Terminal net-worth Δ | Binding |
|---|---|---|---|---|---|---|
| Keep inheritance in cash | cash receipt | $260,000 | $301,381 | $260,000 | $260,000 | annual-savings floor |
| Invest inheritance after the pause | cash receipt | $260,000 | $105,525 | $60,000 | $277,827 | annual-savings floor |
| Hold received stock with basis unresolved | asset receipt | **not cash:** asset is retained, so gross market value is not cash | $41,381 | $0 | $260,000 | emergency-fund floor |
| Fund the modeled home purchase | cash receipt | $260,000 | $178,333 | $105,185 | $209,185 | annual-savings floor |

**Unknown rather than zero:** `stock-receipt.cost_basis`, `stock-receipt.tax_rate`, `stock-receipt.transaction_cost`.

## Tax and basis boundary

| Recorded windfall | Gross amount | Tax character | Basis rule | Pause |
|---|---|---|---|---|
| Inheritance from Ana's aunt | $260,000 | not income | stepped up | **live** |
| Northwind RSU vest | $95,000 | income | unchanged | elapsed |
| Synthetic family stock gift | $260,000 | not income | carryover | elapsed |

The scenario engine reserves only taxes explicitly supplied in the scenario. State tax, NIIT, AMT, holding period and transaction costs remain missing unless recorded; no effective rate is inferred.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/scenario.py and lib/pf/transitions.py` with their reasons; every figure above is derived, not restated. This comparison cannot execute any deployment.*
