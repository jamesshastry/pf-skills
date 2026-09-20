---
name: survivor-needs
description: Compute how much capital a household needs after an earner's death — a present-valued capital-needs analysis against actual spending and the actual balance sheet, not a multiple of income. Use when asked how much life insurance is needed, what would happen financially if someone died, or to size a survivor coverage gap. Feeds life-insurance-review and provides related household-loss context for disability-insurance-review, which sizes income replacement independently. Reads figures from a local facts file.
requires:
  - household.members
  - household.annual_spending
  - household.balance_sheet
---

# Survivor needs

## Why this is its own skill

Life insurance and disability insurance both ask what happens when earnings
stop, but they model different losses. This skill computes the death and
survivor capital need once, and `life-insurance-review` consumes that result.
`disability-insurance-review` is a related sibling analysis: it independently
compares after-tax monthly benefits with ongoing spending and tests the
elimination period against liquid reserves. It shares household context, not
this capital-needs result.

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

## Social Security is netted — year by year, not as an average

Where the statement figures are on file (`social_security.survivors_monthly`),
the report nets survivor benefits out of the capital need. The sequence is the
whole point, so it nets each year's payable amount rather than a flat average:

- a child benefit while a child qualifies, ending at 18 (19 in school);
- a caregiver benefit only while a child is under 16 — frequently already
  expired when people assume it applies;
- nothing between those ending and the widow(er)'s benefit at 60;
- a reduced widow(er)'s benefit from 60, full at the survivor's own full
  retirement age.

An average across the horizon would carry the same present value and erase the
gap years that make the finding useful, so the report shows the phase table
instead. Combined benefits are capped by the family maximum where one is
recorded; where none is recorded the report says the total may overstate
rather than silently over-crediting.

**Both totals are shown.** Excluding Social Security as conservatism is a
defensible choice, so the report gives the need before and after netting and
lets the choice stay visible. Where no statement figures are on file, nothing
is netted and the report says so — the un-netted need is then the whole
answer, and the missing statement is usually its largest single omission.

## Closing

Report the gap as **one number**, with the derivation beside it. Then hand off:
`life-insurance-review` covers the death case, `disability-insurance-review`
the disability case. Don't recommend a product here — this skill sizes the
hole, it doesn't fill it.

Name what would move the number most: the survivor factor, the education
obligation if it's missing, and the discount rate.

## Time-series output

Emit the real-dollar survivor capital gap per earning member's stable ID. Keep
changes in Social Security modeling distinct from household changes.

---

*Not financial, tax, or legal advice.*
