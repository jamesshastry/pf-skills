---
name: contribution-space-audit
description: Audit whether all available tax-advantaged contribution space is being used — employer plan against the §415(c) limit, elective deferral against §402(g), catch-up eligibility, IRA space, and HSA. Flags unused after-tax headroom and the backdoor Roth pro-rata trap. Use when asked whether someone is saving tax-efficiently, maximising retirement contributions, or about mega-backdoor Roth. Reads figures from a local facts file.
requires:
  - household.members
  - contributions.year
---

# Contribution space audit

## Statutory limits are the riskiest numbers here

Every other threshold in this repository is a judgement you can argue with.
These are **facts that change annually** and are simply wrong once stale.

`lib/pf/limits.py` holds a small table keyed by year. A year not in it returns
`UNKNOWN`, and the skill reports that it cannot check anything rather than
applying last year's figures. That refusal is the feature: a confidently quoted
superseded limit will be believed and acted on.

Even for years in the table, the report says to verify against irs.gov before
acting. Do not remove that line.

## Order of operations

Space is not fungible. Filling it in the wrong order leaves value behind:

1. **Employer match** — an immediate return nothing else matches. See
   `employer-match-audit`.
2. **HSA**, if eligible. The only triple-tax-advantaged account.
3. **Elective deferral to the §402(g) limit**, plus catch-up if age permits.
4. **IRA space**, backdoor if income precludes a direct Roth.
5. **After-tax plan contributions with in-plan conversion** — see the trap
   below.
6. **Taxable brokerage** for anything left.

## Three things that are commonly got wrong

**Catch-up sits outside §415(c).** The total that can land in an employer plan
is the §415(c) limit *plus* catch-up, which is why the real ceiling exceeds the
headline number people quote. The SECURE 2.0 enhanced catch-up for ages 60–63
**replaces** the age-50 amount rather than stacking on top of it.

**After-tax contributions without a conversion route are a trap.** The
mega-backdoor route needs *both* after-tax contributions and either in-plan
Roth conversion or in-service withdrawal. With after-tax alone, earnings
accumulate taxable-on-withdrawal — worse than a plain brokerage account for
most people. The report insists on both before recommending it, and flags when
after-tax contributions are being made with no recorded conversion route.

**The backdoor Roth pro-rata rule.** If the person holds *any* pre-tax IRA
balance — traditional, SEP, or SIMPLE — a backdoor conversion is taxed
proportionally across all of them, and it is not the tax-free step it appears
to be. A 401(k) balance does not count; an IRA balance does. The report raises
this on every backdoor contribution, because the balance that ruins it is
frequently one somebody forgot they had.

## Also checked

Compensation above the §401(a)(17) cap, which limits the pay figure that plan
contributions and match are calculated on — and can quietly reduce a
percentage-based match below what the headline rate implies.

## Closing

1. **Total unused space** as one number, then the table.
2. **Whether the after-tax route is actually available**, not just theoretically
   possible — both features, confirmed in the plan document.
3. **The pro-rata check**, if any backdoor contribution is in play.
4. **Note the year.** These numbers expire; the report is a snapshot.

---

*Not financial or tax advice. Verify all limits against irs.gov.*
