# Retirement readiness

At the central assumptions — 4.0% withdrawal, 5% real return — the target of **$2,400,000** is reached in **20 years**, at age **61**.

|  |  |
|---|---|
| Annual spending | $96,000 |
| Investable assets | $423,000 |
| Annual savings | $42,000 |

## The answer is the spread, not the middle

| Withdrawal rate | Target | 3% real | 5% real | 7% real |
|---|---|---|---|---|
| **3.5%** | $2,742,857 | age 69 | age 63 | age 59 |
| **4.0%** | $2,400,000 | age 66 | age 61 | age 57 |
| **4.5%** | $2,133,333 | age 64 | age 59 | age 56 |

**The plausible range is age 56 to 69.** Quoting the middle cell as *the* answer would imply a precision this cannot support — a half-point change in either assumption moves the date by years.

## Caveats that matter more than the arithmetic

- Every figure here is **real** — today's money, discounted at a real return. A nominal projection produces a much larger and entirely meaningless number.
- **This is a deterministic projection, not a simulation.** It assumes a constant real return, which no real sequence delivers. Its value is the sensitivity table, not the point estimate — and it says nothing about sequence-of-returns risk, which is the dominant danger in the first few years of drawdown. For distributions rather than a single path, use a dedicated Monte Carlo tool.

- **Spending is the strongest lever, and it works twice.** A dollar less of annual spending cuts the target by 20–29× *and* raises savings. Nothing on the return side comes close.
- **The withdrawal rate is a rule of thumb, not a law.** It came from historical sequences over a fixed horizon. Longer retirements, different asset mixes and different fee levels all move it.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/retirement.py` with their reasons; every figure above is derived, not restated. Deterministic projection — for distributions, use a dedicated Monte Carlo tool.*
