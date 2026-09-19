# Job-loss stress test

## Primary earner unemployed for 12 months

| Runway view | Months | What it assumes |
|---|---|---|
| Current spending | 6.1 | No immediate spending cut |
| Essential spending | 6.8 | Comparison only unless a spending-change event records it |

| Liquidity test | Result |
|---|---|
| Opening cash | $40,000 |
| Emergency-fund floor | $80,000 |
| Minimum cash | **$-17,678 in month 12** |
| Months below reserve | 24 |
| Liquidity verdict | **fails before terminal recovery** |

### Correlated event bundle

| Event | Person | Duration | Income loss / mo | Severance | Benefits / mo | Health / mo | Unvested lost | Stock change |
|---|---|---|---|---|---|---|---|---|
| `northwind-separation` | a1 | 12 | $11,652 | $24,175 | $1,850 | $975 | $41,000 | -50% |

Explicit liquidation order (the engine still sells only through a recorded withdrawal event): `cash-main` → `taxable-brokerage`.
Recorded employment-loss recovery begins in month **13**; any lower ongoing pay must be a separate `compensation_change` event.

Annual saving during the shock: **$0**; after recovery: **$36,974**. Binding constraint: **emergency-fund floor**.

Recovery conditions:
- Add at least $17,678 before month 12, or explicitly reduce an outflow before then.
- Restore cash above the $80,000 reserve floor after the first breach in month 1.
- Post-recovery annual saving must rise by $14,026.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/scenario.py` with their reasons; every figure above is derived, not restated. This is an adverse deterministic stress, not a forecast.*
