---
name: medicare-enrollment-timing
description: Work out which Medicare enrolment window applies, what a late Part B or Part D enrolment costs permanently, whether Part A is premium-free, and how the two-year IRMAA lookback prices income earned at 63 into a premium paid at 65. Surfaces the same modified-AGI conflict with roth-conversion-window that aca-subsidy-optimization reports. Use when asked about turning 65, Medicare enrolment, working past 65, COBRA before Medicare, Part B penalties, or IRMAA surcharges. Reads figures from a local facts file.
requires:
  - household.members
---

# Medicare enrollment timing

## The idea

Almost everything else in this repository is reversible. **A late Medicare
enrolment is not.** The Part B penalty is 10% of the standard premium for every
full twelve months of eligibility without cover, the Part D penalty is 1% of the
national base premium per uncovered month, and both are charged every month for
the rest of the enrollee's life.

A three-year delay is not a three-year problem. That asymmetry is the whole
reason this is a skill and not a calendar reminder.

## The window depends on one integer

If employment continues past 65 with group coverage, the enrolment window is a
Special Enrolment Period rather than the Initial Enrolment Period — **but only
if the group plan is primary**, and that turns on whether the employer has 20 or
more employees.

At 20+, the group plan pays first, Part B can be deferred safely, and an
8-month SEP opens when the employment or the coverage ends.

Below 20, **Medicare is primary**. The group plan is entitled to pay only what
it would owe as secondary, so someone who has not enrolled is uninsured for the
share Medicare would have paid — and finds out at a claim, not at enrolment.
This is the most expensive misunderstanding in the subject, and the report
refuses to guess the employee count.

## COBRA is not coverage from current employment

Neither is retiree coverage, nor a marketplace plan, nor a spouse's retiree
plan. None of them creates a Part B Special Enrolment Period and none is
creditable for Part B.

A household that treats eighteen months of COBRA as a bridge past 65 accrues the
permanent penalty for the whole of it while believing it is covered. If one
finding here is worth reading twice, it is this one.

## IRMAA looks back two years

The premium at 65 is set from the tax return for the year the household turned
**63** — typically a final working year, a severance year, or a conversion year,
and therefore typically the worst year to be measured on.

IRMAA is a **step, not a slope**. One dollar over a threshold pays the whole
surcharge for the year, on Part B and Part D, per person. For a couple both
enrolled, double it.

It is also **appealable after a life-changing event**, and work stoppage is one
— form SSA-44. A Roth conversion is not a qualifying event, which is exactly why
conversion years need planning and retirement years often do not.

## The conflict, again

This is the third pull on one variable. `roth-conversion-window` says raise
MAGI in early retirement. `aca-subsidy-optimization` says suppress it in the
pre-65 years. IRMAA says suppress it from 63 onward, because that is when the
lookback starts biting.

The report computes the overlap between the conversion window and the lookback
and names it. `aca-subsidy-optimization` holds the full partition of the window
and the sequencing rule; this skill holds the deadlines. Run both — they are
describing one decision.

## The HSA deadline that catches people

HSA contributions must stop **six months before Part A begins**, because Part A
can be granted retroactively that far. Anything contributed inside the
retroactive period is an excess contribution with a penalty.

Claiming Social Security enrols Part A automatically, which catches people who
never chose to enrol at all. `hsa-review` shares this constraint; only this
skill names the deadline.

## What it will not do

- Quote a premium. Part B, Part D and the IRMAA tiers are annual CMS figures,
  deliberately not stored here — review finding A3. Supply them and the report
  computes distances and step costs; omit them and it reports the structure.
- Choose between Original Medicare plus Medigap and Medicare Advantage. That is
  a network and underwriting question, and the Medigap guaranteed-issue window
  is a real deadline worth raising with a broker.
- Handle disability-based eligibility before 65, or ESRD.

## Closing

1. **Which window applies**, and the one integer that decides it.
2. **What lateness costs**, as a permanent multiplier.
3. **Part A quarters** — fixable only before 65.
4. **The IRMAA year**, which is two before the premium year.
5. **The conflict**, with a pointer to the skill holding the sequencing.

---

*Not financial, tax, or legal advice. Premiums, tier thresholds and the
national base premium change annually — confirm them before acting on any
figure.*
