---
name: feie-vs-ftc
description: Price a tax year both ways — the foreign earned income exclusion on Form 2555 against the foreign tax credit on Form 1116 — and report the consequences the two tax bills do not capture: IRA eligibility, the refundable child tax credit, carryforward credits, and the five-year revocation lock. Use when living or working abroad, when deciding which election to make on a US return, or when someone has offered the rule of thumb about high-tax and low-tax countries. Reads figures from a local facts file.
requires:
  - household.members
  - expat.foreign_earned_income
  - expat.foreign_tax_on_earned_income
---

# FEIE vs FTC

## The idea

The rule of thumb — **credit in a high-tax country, exclusion in a low-tax
one** — is directionally right and insufficient. It answers *which produces
the smaller tax bill this year*, and that is a smaller question than the one
being asked.

The election also moves four things that no current-year comparison shows:

| It also moves | Which matters because |
|---|---|
| **IRA eligibility** | Income excluded under §911 cannot support an IRA contribution. Take the exclusion, then fund a Roth, and you have made an excess contribution — taxed at 6% **every year it stays in the account**, not once |
| **The refundable child tax credit** | Filing Form 2555 disqualifies the household from the additional CTC outright. For an expat with little US tax left to offset, the refundable portion is frequently the only part of the credit worth anything |
| **Carryforward credits** | The credit route banks unused foreign tax for ten years. The exclusion banks nothing |
| **Revocation** | Electing out of the exclusion locks you out for five years absent IRS consent. The decision is about six years, not one |

A comparison reporting only the current-year tax bill gets this wrong for
exactly the households where it matters — the ones with children, an IRA
habit, and a plan that changes. That is this skill's reason to exist.

## In a high-tax country both answers are often zero

Worth knowing before reading the table. When foreign tax comfortably exceeds
what the US would charge, **both routes produce no US tax**, and the
current-year comparison decides nothing at all. The entire decision is then
the carryforward, the child credit and the IRA — the section the rule of thumb
does not have.

## Two mechanics that surprise people

**The exclusion does not drop you into the bottom bracket.** Income above the
cap is taxed at the rates that would have applied had nothing been excluded —
the §911 stacking rule. The exclusion removes income from the *top* of the
stack, not the bottom, which is why it disappoints at higher incomes.

**Foreign tax on excluded income is not creditable.** You cannot exclude the
income and credit the tax paid on it. Exclude all of it and the credit on it
is gone entirely — a real cost in a country whose rate is moderate rather than
nil.

## Where it refuses

**No recommendation is made when something unvalued points the other way.**
If the arithmetic favours the credit but the five-year lock cuts against it,
or if the refundable child credit cannot be valued because the per-child
amount is not recorded, the report says so and stops. A recommendation that
ignores a factor it could not measure is worse than no recommendation, because
it looks the same as one that weighed everything.

**The brackets, the standard deduction, the exclusion cap and the refundable
child credit come from your facts file — asked for, never fetched.** They are
year-specific, and a stale bracket table produces a confident dollar figure
that is wrong by an amount nobody can see. `REVIEW.md` A3 records why they are
not held in this repository. Without them the report gives the *structure* of
the decision and refuses the figure.

## What it will not do

Self-employment tax, the foreign housing exclusion, NIIT, AMT, itemised
deductions, the passive credit basket, state conformity, and treaty positions
are all outside the model and named in the report rather than assumed away.
Several of them are individually larger than the gap being decided.

It does not produce a filing position. Nothing in this cluster does.

## Closing

1. **Read the two tax bills, then ignore them if they are equal** — which in a
   high-tax country they often are.
2. **The adjustments table is the decision.** Anything marked *not valued* is
   a question for you, not a rounding item.
3. **Check the prior year's return for a Form 2555** before switching. It
   decides whether this is a free choice or a five-year commitment.
4. **Then take it to a cross-border CPA or EA.** This sizes the decision; it
   does not make it.

---

*Not financial, tax, or legal advice. Rates and limits change annually; keep the facts file
current and year-matched.*
