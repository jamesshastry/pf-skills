---
name: social-security-timing
description: Evaluate Social Security claiming age using the statutory adjustment schedule, framed as longevity insurance rather than a break-even calculation, with particular attention to survivor benefits in a single-income household. Use when asked when to claim Social Security, whether to take benefits early, or about spousal and survivor benefits. Reads figures from a local facts file.
requires:
  - household.members
---

# Social Security timing

## Not a break-even calculation

The usual framing — *at what age does waiting pay off?* — quietly assumes you
know when you will die, and answers the wrong question.

The benefit is **inflation-adjusted and lasts as long as you do**. Delaying is
therefore the purchase of longevity insurance, and the risk being insured is
**living a long time**, not dying early. A break-even age treats the good
outcome as the one where you die on schedule.

Reframe it before showing any numbers.

## The survivor decision, which is usually the whole argument

**For a single-income couple this dominates everything else.**

When one spouse dies, the household keeps the **larger** of the two benefits —
not both. Delaying the higher earner's claim permanently raises the floor under
the survivor for the rest of their life, often for decades. A spouse with no
earnings record has nothing of their own to fall back on.

This consideration routinely outweighs the break-even arithmetic, and is
routinely left out of it. The report raises it automatically when the household
has one earner and more than one adult.

## The spouse's own record

A short work history does **not** reduce spousal or survivor benefits — neither
requires the spouse's own credits, and the report says so plainly, because the
opposite intuition wastes years. What a thin record does change:

- **No floor.** Every dollar flows through the worker's record, so anything
  interrupting payment there interrupts all of it rather than part of it.
- **Coupled filing.** A spousal benefit cannot begin until the worker files, so
  delaying the worker's claim silently defers the spouse's income too — that
  cost belongs in the delay calculation.
- **The 50% test on further credits.** Building the spouse's record raises the
  household total only once their own benefit would exceed half the worker's
  PIA. Against a 35-year average a late, short career rarely clears that bar.
  The report gives the verdict where both statements are on file
  (`social_security.spouse_own_projected_monthly`) and the dollar threshold
  where only the worker's is.

Whether benefits are payable abroad is an answer recorded from SSA or left
unknown. The exceptions are specific, this skill does not encode them, and
that refusal stands.

## What the table is and isn't

The report shows the **statutory adjustment schedule** — the percentage of the
full-retirement-age amount at each claiming age. Roughly 70% at 62 and 124% at
70 for a full retirement age of 67.

Where the statement figures are on file (`social_security.retirement_monthly`),
each row gains its dollar amount — transcribed, never computed. Without them
the percentages decide nothing on their own, and the report sends the reader
to their statement rather than inventing a figure.

Full retirement age steps in months across the 1955–1959 birth years, and the
skill **deliberately refuses to approximate it** for that band. A plausible
rounded number would be believed. Send them to their statement.

## Good and bad reasons to claim early

**Good:** poor health with a genuinely shortened life expectancy; needing the
income now with no alternative; a portfolio large enough that the benefit is
irrelevant either way.

**Bad:** *getting back what I paid in* — the benefit is not an account balance.
*The programme might change* — if anything that argues for delaying, since
changes have historically protected those already claiming and those close to
it.

Say which is which. People arrive with the bad reasons and they deserve a
straight answer.

## Also worth raising

Claiming early while still working triggers the **earnings test**, withholding
benefits above an annual threshold. Spousal benefits have their own rules and
are not modelled here.

## Closing

1. **Reframe away from break-even** before any numbers.
2. **The adjustment table**, with dollar amounts beside the percentages where
   the statement is on file.
3. **The survivor argument**, if it applies — leading, not buried.
4. **The spouse's own record**, where there is a spouse — including the 50%
   test before anyone decides more credits mean more income.
5. **Send them to their statement** for the actual amounts — theirs and, where
   it matters, the spouse's.

---

*Not financial advice. Benefit amounts, spousal eligibility and earnings-test
thresholds come from ssa.gov.*
