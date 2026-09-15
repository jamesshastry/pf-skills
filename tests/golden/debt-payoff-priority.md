# Debt payoff priority

**$44,300** across 4 debt(s) · minimums $865/mo · extra $600/mo.

| Debt | Balance | APR | After tax | Minimum |
|---|---|---|---|---|
| personal_loan | $1,800 | 3.00% | 3.00% | $60 |
| credit_card | $6,200 | 22.49% | 22.49% | $155 |
| auto_loan | $14,800 | 6.29% | 6.29% | $410 |
| student_loan | $21,500 | 5.85% | 4.45% *ded.* | $240 |

## The two orderings

| Method | Order | Months | Total interest |
|---|---|---|---|
| **Avalanche** (rate) | credit_card → auto_loan → student_loan → personal_loan | 34 | $4,253 |
| **Snowball** (balance) | personal_loan → credit_card → auto_loan → student_loan | 34 | $4,541 |

Both simulations roll a cleared debt's minimum payment into the next target, so the only difference is the order.

- **Snowball costs $287 more** than avalanche. That is the entire price of the psychologically easier schedule. If closing the first account quickly is what makes the plan get finished, it is worth paying — the optimal schedule that gets abandoned in month four is not optimal.

- **Paying these down early competes with investing rather than beating it:** `personal_loan` (3.00% after tax), `auto_loan` (6.29% after tax), `student_loan` (4.45% after tax), against an assumed 7.00% expected return. The arithmetic favours investing — but the arithmetic is comparing a **certain** return against an **uncertain** one, which is not a like-for-like comparison. Paying down debt is risk-free and irreversible; investing is neither. Reasonable people choose the guaranteed return, and that is a preference, not an error.

- 1 debt(s) at 15% or above. At those rates paying down beats essentially any investment on a risk-adjusted basis, and the ordering debate is academic — target them first under either method.

## How to choose

**Avalanche is mathematically correct. Snowball is the one people finish.** The cost of the difference is stated above in dollars, which is the only honest way to present it — a few hundred dollars for a plan that actually gets completed is a good trade, and the optimal schedule abandoned in month four is not optimal.

Pick avalanche if the gap is large or the rates are far apart. Pick snowball if past attempts have stalled. Do not let the choice itself become the reason nothing starts.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/debt.py` with their reasons; every figure above is derived, not restated.*
