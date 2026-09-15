---
name: solo-retirement-plan-choice
description: Compare a Solo 401(k), a SEP IRA and a defined benefit plan for an owner-only business, using the statutory §415(c) and catch-up limits already in the repository. Use when a self-employed person or single-owner S-Corp asks which retirement plan to open, how much they can contribute, whether a SEP or Solo 401(k) shelters more, or how much a defined benefit plan could shelter. Reads figures from a local facts file.
requires:
  - business.gross_revenue
  - business.expenses
  - household.members
---

# Solo retirement plan choice

## The idea

For an owner-only business this decision is usually not close, and the reason
is structural rather than marginal.

**A SEP IRA has only an employer contribution.** Roughly 25% of W-2
compensation, or 20% of net self-employment earnings. That is all of it: no
elective deferral, no catch-up.

**A Solo 401(k) has the same employer piece and an elective deferral on top**,
plus catch-up at 50 and over which sits *outside* the §415(c) limit. At any
income where the employer percentage alone does not already reach §415(c), the
Solo 401(k) shelters more — by approximately the whole deferral limit.

That gap only closes at the income where 25% of compensation hits §415(c) on
its own. Below it, which is most owner-operators, a SEP is leaving the deferral
on the table for nothing.

## This skill does not recompute contribution space

§415(c), the elective deferral limit and the catch-up rules are already
tabulated in `lib/pf/limits.py`, marked unverified, and registered for
verification. A Solo 401(k) is an **employer plan**, so those same numbers
govern it. Reading them twice is how two figures in one repository come to
disagree.

For what is already used across every account this year — 401(k), IRA, HSA —
use `contribution-space-audit`. This skill answers only which plan to open.

## The entity choice caps the plan

Plan compensation for an S-Corp owner is **W-2 salary only.** Distributions are
not compensation and buy no plan space.

So a salary minimised for payroll-tax reasons in
`entity-structure-comparison` also caps the employer contribution at 25% of
that smaller number. The two decisions are one decision. Optimise them
separately and you will get both wrong — the payroll saving is visible and the
lost plan space is not.

For a Schedule C the employer contribution is deductible against qualified
business income too, so the after-tax value of a contributed dollar is less
than the marginal rate suggests: the §199A deduction shrinks by 20 cents of
that same dollar.

## Defined benefit: a real option, and no figure

A defined benefit plan can shelter $100,000–$300,000 or more for an older,
high-income, cash-rich owner-operator. That is the reason to look at it, and it
is the reason this skill refuses to produce a number.

The limit is §415(b) — a *benefit* limit — and the deductible contribution is
whatever an enrolled actuary certifies is needed to fund it, given age,
compensation history and assumed returns. An estimate here would be a
plausible-looking figure with nothing behind it.

What can be said without an actuary:

- It is a **funding commitment**, not an annual election. The contribution is
  largely mandatory in bad years too.
- It suits stable, high income. It is wrong for volatile income.
- It is generally right above roughly age 45, because the shorter the funding
  window the larger the required annual contribution.
- It carries actuarial and administration fees every year, and terminating
  early has consequences.

## The year the business hires

This is where the SEP goes wrong, and it is worth knowing before choosing one.

A **SEP requires the same percentage of pay for every eligible employee.**
Free while the business is owner-only; a direct cost of hiring afterwards. The
plan chosen for its simplicity becomes the reason a first hire is unaffordable.

A **Solo 401(k) stops being solo** when a non-spouse employee becomes eligible
— it becomes an ordinary 401(k) with nondiscrimination testing and real
administration.

A spouse working in the business is not a disqualifying employee and can have
their own deferral and employer contribution, which frequently doubles what an
owner-operator couple can shelter.

## What it will not do

**No defined benefit figure.** See above.

**No figure for a year that is not in the limits table.** `limits.py` returns
UNKNOWN for a year it has not been given rather than quietly applying last
year's numbers, and this skill reports that rather than estimating.

**It does not model the Roth choice.** A Solo 401(k) can take Roth deferrals
and a SEP historically could not; whether Roth is right is a tax-rate question
belonging to `roth-conversion-window` and the contribution audit.

**It does not track deadlines for you.** They differ by plan and are the thing
most often missed: a Solo 401(k) generally must *exist* before the year ends
even though it can be funded later, while a SEP can be established and funded
up to the return due date. Check the current rule.

## Closing

1. **The gap between the two totals** is the elective deferral. That is the
   whole finding for most owner-only businesses.
2. **Check the salary** if the business is on payroll — it caps the employer
   piece, and that cost belongs next to the payroll-tax saving.
3. **Defined benefit** if income is high, stable and the owner is older — then
   go to an actuary, not to a calculator.
4. **Ask what happens when you hire**, before choosing, not after.

---

*Not financial, tax, or legal advice.*
