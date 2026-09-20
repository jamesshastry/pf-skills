---
name: tax-planning
description: Review U.S. filed-return history alongside current income, contribution, investment, charitable, and retirement facts to identify tax-reduction moves and expose their liquidity, timing, eligibility, and future-tax tradeoffs. Use when a household wants a prioritized annual or multi-year U.S. tax plan grounded in a local facts file rather than generic deductions.
requires:
  - meta.as_of
  - meta.currency
  - meta.jurisdiction.country
  - household.members
  - household.balance_sheet
  - contributions.year
  - assumptions.marginal_tax_rate
  - assumptions.state_tax_rate
  - tax_planning.returns[].tax_year
  - tax_planning.returns[].adjusted_gross_income
  - tax_planning.returns[].taxable_income
  - tax_planning.returns[].federal_total_tax
  - tax_planning.returns[].state_income_tax
  - tax_planning.returns[].filing_status
  - tax_planning.returns[].state
  - tax_planning.current_year.tax_year
  - tax_planning.current_year.projected_adjusted_gross_income
  - tax_planning.current_year.projected_taxable_income
  - tax_planning.current_year.projected_federal_total_tax
  - tax_planning.current_year.projected_state_income_tax
  - tax_planning.current_year.projected_payments
  - tax_planning.current_year.filing_status
  - tax_planning.current_year.state
---

# Tax planning

## The decision

Decide which tax moves deserve action this year, using filed returns as the
baseline and current household facts as the constraint. Rank quantified
current-year reductions first, then multi-year timing choices. Never total the
opportunities until their overlap has been modeled.

## Use history correctly

Read filed-return figures through `lib/pf/tax_planning.py`. Compare AGI, taxable
income, federal tax, state tax, and effective rate across tax years. Keep tax
liability separate from payments: a refund is not a low tax bill, and a balance
due is not itself a failure to minimize tax. Missing years remain gaps.

A historical rate change identifies a question, not its cause. Do not attribute
it to deductions, income mix, filing status, legislation, or geography unless
the corresponding facts establish that explanation.

## Candidate moves

Use the shared domain engines rather than recreating their rules:

- contribution limits and HSA room come from `lib/pf/limits.py`;
- appreciated gifts and deduction bunching come from `lib/pf/charity.py`;
- taxable loss lots come from the recorded balance sheet, with the usable loss
  and rate supplied by tax software rather than inferred here;
- a low-income Roth conversion is a scenario that raises tax now and may lower
  it later, never a current-year deduction.

For every candidate show the amount affected, current-year tax change, any
separately estimated future benefit, confidence, and the tradeoffs. Those
tradeoffs include cash lockup, future ordinary tax, loss of Roth treatment,
wash-sale exposure, charitable irrevocability, AGI limits, ACA subsidies,
IRMAA, and uncertain future rates wherever applicable.

## Boundaries

This is a planning screen, not tax preparation. It does not infer brackets,
perform capital-gain netting, choose lots, establish eligibility, amend a
return, file an election, or treat an unrecorded state rule as zero. Current
rates and indexed limits must be verified for the relevant tax year before
acting. Route implementation details to the named specialist skill and a tax
professional where the result depends on return-level law.

The opportunity engine is U.S.-specific. For any other recorded country it may
display the supplied history but produces no U.S. contribution, HSA, loss,
charitable, or Roth strategy.

*Not financial, tax, or legal advice.*
