# Life insurance review

## Insured: a1

⚠️ **Short by $815,488.** Need $1,465,488 · portable cover in force $650,000 · premiums $2,820/yr.

| Policy | Type | Benefit | Premium | Per $1k/yr | Portable |
|---|---|---|---|---|---|
| Level Term 20 | term | $500,000 | $420 | $0.84 | yes |
| Variable Universal Life | variable_universal | $150,000 | $2,400 | $16.00 | yes |
| Employer group life | group | $360,000 | $0 | — | **no** |

> $360,000 of employer cover is excluded from the gap. Including it would assume the job survives the event that creates the claim.

> **`Level Term 20` expires before the dependents do.** About 15 years of cover against 17 years of dependency. Renewing at that point means renewing at that age, in that health.

> **`Variable Universal Life` costs 19× per dollar of death benefit** what `Level Term 20` does ($16.00 vs $0.84 per $1,000/yr). That spread is the whole argument, and it does not require an opinion about investment returns.

### Level Term 20

- Term expires <DATE> — about 15 years away.

### Variable Universal Life

- **Cash value is below premiums paid** — $18,500 against $25,200. A nominal loss of $6,700 before inflation, on a product sold as an investment.
- Implied return ≈ **-5.7%/yr nominal** over about 10 years, computed generously (premiums treated as a lump sum at the midpoint). The bar for keeping it as an investment is 3% *real*.
- Surrendering has two traps worth naming before anyone acts. **Do not 1035 exchange into another permanent policy** — it feels like a fix and restarts the surrender-charge clock on the same cost architecture. And **replace the death benefit before cancelling**, never after: the new policy must be in force first, because insurability is not guaranteed.

### Employer group life

- **Employer-provided, so treat it as zero for planning.** It is real while employed, but the job ending and needing the cover are correlated events — a layoff removes the income and the policy together. Check whether it is portable or convertible, and at what rate.


---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/life.py` with their reasons; every figure above is derived, not restated. Cash-value returns are computed generously; the real figure is usually worse.*
