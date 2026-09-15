# Emergency fund sizing

✅ **Adequate.**

|  |  |
|---|---|
| Liquid assets | $85,000 |
| Monthly spending | $8,000 |
| Months held | **10.6** |
| Target months | **10** |
| Target | **$80,000** |

### How the target was built

- Base 3 months
- +3 single earner — no second income to fall back on, and no partial-loss case
- +2 dependents — longer job search, less room to cut living costs
- +2 28% of income is variable — pay can fall sharply with no job loss at all

Measured against **`liquid` assets only** — not net worth, and not retirement accounts. A household with a large 401(k) and no cash cannot pay a deductible.

- Adequate. No action.

- For context: cutting to essential spending only (about $6,000/month) stretches the same $85,000 to **14 months**. The target above deliberately uses full spending — a crisis is a bad time to be discovering which costs are actually fixed.

## Why this gates everything else

The property and casualty skills refuse to recommend dropping any coverage from a household below **3 months**, whatever the price arithmetic says. Self-insuring a risk means paying for it out of the buffer; without one, the household meets an ordinary setback with credit-card debt at 20%+ and the saving is erased several times over.

That floor is a single constant shared by both skills (`cash.MIN_BUFFER_MONTHS`), so the two cannot disagree about it.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/cash.py` with their reasons; every figure above is derived, not restated.*
