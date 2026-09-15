# Contribution space audit

**$52,650 of tax-advantaged space is unused this year.**

| Space | Used | Ceiling | Unused |
|---|---|---|---|
| Employer plan (§415(c)) | $28,100 | $72,000 | **$43,900** |
| …of which elective deferral (§402(g)) | $24,500 | $24,500 | — |
| IRA — a1 | $7,500 | $7,500 | — |
| HSA (family) | $0 | $8,750 | **$8,750** |

- *Employer plan (§415(c))* — §415(c) is $72,000. No catch-up at this age — it becomes available at 50.
- *…of which elective deferral (§402(g))* — Pre-tax and Roth combined. After-tax contributions do not count against this, which is what makes the after-tax route possible.
- *IRA — a1* — roth_backdoor
- *HSA (family)* — The only triple-tax-advantaged account available.

- Limits used are the 2026 figures from `lib/pf/limits.py` (IRS annual cost-of-living adjustments for 2026). They change annually; **verify against irs.gov before acting on any number here.**

- **$43,900 of employer-plan space is unused, and no after-tax contributions are being made.** If the plan permits after-tax contributions *and* in-plan Roth conversion or in-service withdrawal, that headroom can be filled. Both features are required — after-tax contributions without a conversion route leave earnings growing in a taxable-on-withdrawal bucket, which is worse than a plain brokerage account for most people. Check the summary plan description for both before acting.

- IRA for `a1` is a backdoor Roth. **Check the pro-rata rule**: if that person holds *any* pre-tax IRA balance — traditional, SEP, or SIMPLE — the conversion is taxed proportionally across all of them, and the step is not the tax-free move it appears to be. A 401(k) balance does not count; an IRA balance does.

## Order of operations

Space is not fungible, and filling it in the wrong order leaves value behind:

1. **Employer match** — an immediate return nothing else matches. Never leave it on the table; see `employer-match-audit`.
2. **HSA**, if eligible. The only triple-tax-advantaged account: deductible in, untaxed growth, untaxed out for medical.
3. **Elective deferral to the §402(g) limit**, plus catch-up if age permits.
4. **IRA space**, backdoor if income precludes a direct Roth.
5. **After-tax plan contributions with in-plan conversion**, if and only if the plan offers both.
6. **Taxable brokerage** — unlimited, and the right home for anything left over.

> **After-tax contributions without a conversion route are a trap.** The earnings grow taxable-on-withdrawal, which is worse than a plain brokerage account for most people. Both features have to be present.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/limits.py` with their reasons; every figure above is derived, not restated. Statutory limits change annually — verify against irs.gov before acting.*
