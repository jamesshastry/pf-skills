# Financial scenario planner

Every row is a **deterministic projection**, not a fact or probability. The unchanged baseline runs through the identical monthly engine.

**No ranking.** No single objective was recorded; the table presents tradeoffs without inventing what the household values.

| Scenario | Min cash | When | Months below reserve | Terminal cash Δ | Terminal net-worth Δ | Post-recovery saving | Retirement target age | Binding |
|---|---|---|---|---|---|---|---|---|
| Primary earner unemployed for 12 months | $-17,678 | month 12 | 24 | $-89,852 | $-148,852 | $36,974/yr | 65 | emergency-fund floor |
| Keep inheritance in cash | $301,381 | month 1 | 0 | $260,000 | $260,000 | $58,574/yr | 62 | annual-savings floor |
| Invest inheritance after the pause | $105,525 | month 4 | 0 | $60,000 | $277,827 | $58,574/yr | 59 | annual-savings floor |
| Hold received stock with basis unresolved | $41,381 | month 1 | 24 | $0 | $260,000 | $58,574/yr | 59 | emergency-fund floor |
| Fund the modeled home purchase | $178,333 | month 24 | 0 | $105,185 | $209,185 | $42,000/yr | 62 | annual-savings floor |

## Primary earner unemployed for 12 months

| Baseline | Scenario | Difference |
|---|---|---|
| Terminal cash $73,148 | Terminal cash $-16,704 | $-89,852 |
| Terminal net worth $513,527 | Terminal net worth $364,675 | $-148,852 |
| Reserve floor $80,000 | Minimum $-17,678 in month 12 | 24 month(s) below |

### Event bridge

| Event | Isolated cash effect | Isolated net-worth effect | Basis |
|---|---|---|---|
| `northwind-separation` | $-74,252 | $-127,252 | isolated event effect; any composition residual remains explicit |
| `lower-pay-reemployment` | $-15,600 | $-21,600 | isolated event effect; any composition residual remains explicit |
Composition residual: cash **$-0**; net worth **$-0**. It is retained rather than forced into an event when effects overlap.

### Months that decide the result

| Month | Cash | Marketable | Employer stock | Retirement | Debt | Net worth | Events |
|---|---|---|---|---|---|---|---|
| 1 | $56,429 | $40,679 | $11,000 | $310,000 | $44,300 | $401,808 | northwind-separation |
| 12 | $-17,678 | $40,679 | $11,000 | $310,000 | $44,300 | $327,701 | northwind-separation |
| 13 | $-17,597 | $40,679 | $11,000 | $313,000 | $44,300 | $330,782 | lower-pay-reemployment |
| 24 | $-16,704 | $40,679 | $11,000 | $346,000 | $44,300 | $364,675 | lower-pay-reemployment |

Recovery conditions:
- Add at least $17,678 before month 12, or explicitly reduce an outflow before then.
- Restore cash above the $80,000 reserve floor after the first breach in month 1.
- Post-recovery annual saving must rise by $14,026.

## Keep inheritance in cash

| Baseline | Scenario | Difference |
|---|---|---|
| Terminal cash $73,148 | Terminal cash $333,148 | $260,000 |
| Terminal net worth $513,527 | Terminal net worth $773,527 | $260,000 |
| Reserve floor $80,000 | Minimum $301,381 in month 1 | 0 month(s) below |

### Event bridge

| Event | Isolated cash effect | Isolated net-worth effect | Basis |
|---|---|---|---|
| `inheritance-receipt` | $260,000 | $260,000 | isolated event effect; any composition residual remains explicit |
Composition residual: cash **$0**; net worth **$0**. It is retained rather than forced into an event when effects overlap.

### Months that decide the result

| Month | Cash | Marketable | Employer stock | Retirement | Debt | Net worth | Events |
|---|---|---|---|---|---|---|---|
| 1 | $301,381 | $40,679 | $22,000 | $313,500 | $44,300 | $661,260 | inheritance-receipt |
| 24 | $333,148 | $40,679 | $22,000 | $394,000 | $44,300 | $773,527 | — |

Recovery conditions:
- No modeled recovery condition is breached.

## Invest inheritance after the pause

| Baseline | Scenario | Difference |
|---|---|---|
| Terminal cash $73,148 | Terminal cash $133,148 | $60,000 |
| Terminal net worth $519,952 | Terminal net worth $797,778 | $277,827 |
| Reserve floor $80,000 | Minimum $105,525 in month 4 | 0 month(s) below |

### Event bridge

| Event | Isolated cash effect | Isolated net-worth effect | Basis |
|---|---|---|---|
| `inheritance-receipt-invest` | $260,000 | $260,000 | isolated event effect; any composition residual remains explicit |
| `diversified-transfer` | $-200,000 | $17,827 | isolated event effect; any composition residual remains explicit |
Composition residual: cash **$0**; net worth **$0**. It is retained rather than forced into an event when effects overlap.

### Months that decide the result

| Month | Cash | Marketable | Employer stock | Retirement | Debt | Net worth | Events |
|---|---|---|---|---|---|---|---|
| 1 | $301,381 | $40,845 | $22,090 | $313,500 | $44,300 | $661,516 | inheritance-receipt-invest |
| 4 | $105,525 | $242,161 | $22,361 | $324,000 | $44,300 | $677,746 | diversified-transfer |
| 24 | $133,148 | $262,675 | $24,255 | $394,000 | $44,300 | $797,778 | — |

Recovery conditions:
- No modeled recovery condition is breached.

## Hold received stock with basis unresolved

| Baseline | Scenario | Difference |
|---|---|---|
| Terminal cash $73,148 | Terminal cash $73,148 | $0 |
| Terminal net worth $513,527 | Terminal net worth $773,527 | $260,000 |
| Reserve floor $80,000 | Minimum $41,381 in month 1 | 24 month(s) below |

### Event bridge

| Event | Isolated cash effect | Isolated net-worth effect | Basis |
|---|---|---|---|
| `stock-receipt` | $0 | $260,000 | isolated event effect; any composition residual remains explicit |
Composition residual: cash **$0**; net worth **$0**. It is retained rather than forced into an event when effects overlap.

### Months that decide the result

| Month | Cash | Marketable | Employer stock | Retirement | Debt | Net worth | Events |
|---|---|---|---|---|---|---|---|
| 1 | $41,381 | $300,679 | $22,000 | $313,500 | $44,300 | $661,260 | stock-receipt |
| 24 | $73,148 | $300,679 | $22,000 | $394,000 | $44,300 | $773,527 | — |

Unknown inputs retained: `stock-receipt.cost_basis`, `stock-receipt.tax_rate`, `stock-receipt.transaction_cost`.

Recovery conditions:
- Restore cash above the $80,000 reserve floor after the first breach in month 1.

## Fund the modeled home purchase

| Baseline | Scenario | Difference |
|---|---|---|
| Terminal cash $73,148 | Terminal cash $178,333 | $105,185 |
| Terminal net worth $513,527 | Terminal net worth $722,712 | $209,185 |
| Reserve floor $80,000 | Minimum $178,333 in month 24 | 0 month(s) below |

### Event bridge

| Event | Isolated cash effect | Isolated net-worth effect | Basis |
|---|---|---|---|
| `inheritance-receipt-home` | $260,000 | $260,000 | isolated event effect; any composition residual remains explicit |
| `maple-ridge-purchase` | $-154,815 | $-50,815 | isolated event effect; any composition residual remains explicit |
Composition residual: cash **$0**; net worth **$0**. It is retained rather than forced into an event when effects overlap.

### Months that decide the result

| Month | Cash | Marketable | Employer stock | Retirement | Debt | Net worth | Events |
|---|---|---|---|---|---|---|---|
| 1 | $301,381 | $40,679 | $22,000 | $313,500 | $44,300 | $661,260 | inheritance-receipt-home |
| 4 | $191,125 | $40,679 | $22,000 | $324,000 | $460,300 | $665,504 | maple-ridge-purchase |
| 24 | $178,333 | $40,679 | $22,000 | $394,000 | $460,300 | $722,712 | — |

Recovery conditions:
- Post-recovery annual saving must rise by $9,000.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/scenario.py` with their reasons; every figure above is derived, not restated. No scenario is written back into the household facts.*
