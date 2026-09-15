---
name: survivor-needs
description: Compute how much capital a household needs if an earner's income stops — a present-valued capital-needs analysis against actual spending and the actual balance sheet, not a multiple of income. Use when asked how much life or disability insurance is needed, what would happen financially if someone died, or to size a coverage gap. Feeds life-insurance-review and disability-insurance-review. Reads figures from a local facts file.
requires:
  - household.members
  - household.annual_spending
  - household.balance_sheet
---

# Survivor needs

## Why this is its own skill

Life insurance and disability insurance ask the same question — *what does this
household need if an income stops* — and answer it with different products.
Computing the need twice guarantees two answers that eventually disagree.

So the need is computed once, here, and both coverage skills consume it.

## Capital needs, not a multiple of income

The common rule of thumb is ten to twelve times income. It ignores the balance
sheet entirely, and is therefore wrong in both directions: it over-insures a
household with substantial assets and modest spending, and under-insures a
young household with none.

The method here:

```
(household spending × survivor factor − surviving income)
  present-valued over the survivor's horizon at a real rate
  + final expenses
  + education obligation
  − assets that pass to the survivors
  = the gap insurance has to close
```

Every term is checkable, and the report shows all of them.

## Two things to get right

**Keep it real, not nominal.** Real spending discounted at a real rate. Mixing
a nominal rate into a real cash flow overstates the discount and understates
the need — quietly, and by a lot over a forty-year horizon. This is a
documented defect class, which is why the arithmetic is in `lib/pf/survivor.py`
with tests rather than in prose.

**Assets available here are not the same as liquid assets.** On death,
retirement accounts pass to the survivor, so they count. In the property and
casualty skills the household is still alive and cannot reach them, so they
don't. Same balance sheet, two different subtotals, for a real reason — say so
rather than letting it look like an inconsistency.

## The survivor factor is a benchmark

One fewer adult removes some consumption and almost none of the fixed costs.
Housing, utilities, insurance, and transport barely move. The default is a
population estimate, and it is the weakest input here.

If the household has thought about a post-loss budget, use that instead — it is
better data than any benchmark. Say which one you used.

## The gap decade

Worth raising unprompted, because almost nobody plans for it.

When dependents become independent, survivor benefits for a caregiving spouse
generally stop — and do not resume until that spouse reaches their own
retirement age. The years in between are funded entirely from capital, by
someone who may have been out of the workforce for two decades.

The report computes when that window opens and how long it runs. For a
household with young children and a non-earning spouse it is often the largest
single driver of the number, and it is invisible in a multiple-of-income
calculation.

## Closing

Report the gap as **one number**, with the derivation beside it. Then hand off:
`life-insurance-review` covers the death case, `disability-insurance-review`
the disability case. Don't recommend a product here — this skill sizes the
hole, it doesn't fill it.

Name what would move the number most: the survivor factor, the education
obligation if it's missing, and the discount rate.

---

*Not financial, tax, or legal advice.*
