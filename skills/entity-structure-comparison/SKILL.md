---
name: entity-structure-comparison
description: Compare take-home pay for an owner-operator under Schedule C, an S-Corp election and a C-Corp, including self-employment tax, the §199A qualified business income deduction, the reasonable-salary optimum, and whether the S-Corp saving clears the cost of running it. Use when asked whether to form an LLC, elect S-Corp status, incorporate, set an owner salary, or how the QBI deduction affects any of that. Reads figures from a local facts file.
requires:
  - business.gross_revenue
  - business.expenses
---

# Entity structure comparison

## The idea

Almost every S-Corp comparison in circulation models one thing: salary below
the Social Security wage base avoids 15.3% self-employment tax, distributions
do not, therefore minimise salary. That is half of the interaction.

The other half is that **W-2 salary also reduces qualified business income.**
An S-Corp's QBI is what is left after salary and after the employer half of
FICA, so every dollar moved into salary removes about $1.08 of QBI and 20 cents
of §199A deduction with it.

Model the first without the second and you get a confident recommendation that
is wrong — sometimes by thousands of dollars a year, and in a direction that
depends on which of three regimes the household is in.

## Reasonable salary has an optimum, not a floor

Three regimes, and they give opposite advice:

| Where taxable income sits | What salary does | The answer |
|---|---|---|
| Below the §199A threshold | Costs FICA, shrinks QBI | **Lowest defensible salary** |
| Above it, non-service | Buys deduction — the 50%-of-W-2 limit binds | **Interior optimum, near 28% of pre-salary profit** |
| Above it, service business | QBI is phased out to nothing | **Lowest defensible salary again** |

The middle row is the one a rule of thumb destroys. Above the threshold the
deduction is capped at 50% of W-2 wages, so paying *too little* salary throws
away deduction. The optimum is where `0.5 × salary` meets
`0.2 × (profit − salary − employer FICA)`, which lands near 28% of pre-salary
profit — and the report finds it by sweeping the curve rather than asserting
the ratio, because the ratio moves with the facts.

The curve is flat near the top. Being approximately right is worth nearly as
much as being exactly right; do not over-fit the salary to the dollar.

## A Schedule C above the threshold has no wage limit to stand on

This is the finding most comparisons miss entirely. A sole proprietorship pays
no W-2 wages. Above the §199A threshold, a non-service business with no wages
and no qualified property gets **no QBI deduction at all**.

For a profitable non-service owner-operator over the threshold, that — not the
payroll saving — is frequently the entire argument for electing S-Corp status.

## QBI is computed here, not in a skill of its own

Deliberately. Separating them invites exactly the error this skill exists to
prevent: optimising payroll tax in one report and the deduction in another,
with nothing reconciling the two.

## The election has to clear its own cost

An S-Corp costs money that a Schedule C does not: payroll processing, a
separate 1120-S return, state franchise or minimum tax, a registered agent.
Record `business.s_corp_annual_cost` and the report gives a verdict instead of
a number. Below roughly 2× the running cost the saving is reported as marginal
— a recurring quarterly filing obligation is not free even when the invoice is
small, and one missed payroll deposit penalty eats a year of it.

If outside W-2 wages already consume the Social Security wage base, most of the
saving is already gone before the comparison starts: only the 2.9% Medicare
rate remains on the sheltered distribution.

## Year-specific figures come from your facts file

The Social Security wage base, the §199A threshold and its phase-in range are
**asked for, never fetched and never stored here.** They change annually, and
`REVIEW.md` A3 records the repository's statutory table as unverified and not
to be grown. Absent them the report stops and lists what is missing rather than
producing figures it cannot stand behind.

Rates fixed in statute and not indexed — 12.4% OASDI, 2.9% Medicare, 20%
§199A, 21% corporate — are constants in `lib/pf/entity.py` with their reasons.

## Living abroad does not remove self-employment tax

**The foreign earned income exclusion is an income tax exclusion.** A US
citizen running a Schedule C from abroad can exclude the profit from income tax
and still owe the full 15.3% on it. A totalization agreement can eliminate it
where one applies; the FEIE cannot.

Excluded income is also not qualified business income, so the salary curve
above is not valid without knowing which income is excluded. See `feie-vs-ftc`
for the exclusion arithmetic and the cross-border country table for residency.
This skill owns entity choice; it does not own residency.

## What it will not do

**It will not tell you what a reasonable salary is.** That is a facts and
circumstances determination — what the work is, what comparable people are paid
for it, how much of the profit is labour rather than capital. It needs
comparable compensation data this skill does not have. Supply
`business.reasonable_salary_floor` and the sweep starts there; leave it out and
the sweep starts at zero, which is the left-hand end of a curve, not a
recommendation.

**It does not model a bracket schedule.** Your marginal rate is applied to
taxable income. Read the gaps between structures, which are close to right, not
the absolute levels, which are approximations.

**It does not model state corporate tax or franchise tax**, so the C-Corp row
is a ceiling. Several states also refuse to recognise S-Corps, or tax them
separately.

**It does not model the reasons a C-Corp is usually chosen** — §1202 qualified
small business stock, an investor who will not hold S-Corp shares, a genuine
need to retain capital. Those depend on an exit this skill knows nothing about.

**It does not decide BOI reporting.** It has been *reported* that an August
2026 FinCEN final rule exempts US domestic companies from beneficial ownership
information reporting. That is repeated as reported and **is not verified
here**. Check fincen.gov/boi. A confident "you are exempt" is the worst
available failure, because it is believed and it fails in the direction of not
filing.

**It is a single-year comparison.** An S-Corp election is not costless to
unwind, and revoking one has a five-year wait before re-electing.

## Closing

1. **The gaps between structures**, not the absolute take-home figures.
2. **Which regime you are in** — it decides whether salary should be minimised
   or optimised, and the advice reverses between them.
3. **Whether the saving clears the running cost**, with the cost recorded.
4. **The reasonable salary** is the weakest input and carries the whole result.
   Everything else is arithmetic; this one is a judgement you must defend.
5. Take it to a CPA before filing Form 2553 — the election has deadlines.

---

*Not financial, tax, or legal advice.*
