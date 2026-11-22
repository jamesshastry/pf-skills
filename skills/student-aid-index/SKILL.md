---
name: student-aid-index
description: Estimate the federal Student Aid Index (SAI) for each dependent student under the FAFSA Simplification formula, compare it with cost of attendance, and decide whether need-based aid is plausible and whether moving assets (buying a home, spending down cash, shifting a child's money) can change it. Use when asked about FAFSA, SAI, EFC, financial aid eligibility, or whether to time a purchase or move savings before college applications. Reads figures from a local facts file.
requires:
  - household.members
  - household.balance_sheet
  - education.financial_aid.award_year
  - education.financial_aid.income_year
  - education.financial_aid.parent_total_income
  - education.financial_aid.parent_federal_income_tax
  - education.financial_aid.parent_earned_income
  - education.financial_aid.family_size
  - education.financial_aid.older_parent_age
  - education.financial_aid.two_parents
  - education.financial_aid.cost_of_attendance
---

# Student Aid Index

## The idea

Need-based aid is **cost of attendance minus SAI**. The SAI comes overwhelmingly
from parents' *income*; assets enter only after a 12% conversion and the same
assessment schedule, so at most **5.64%** of reportable parent assets reaches the
SAI (20% of student-held assets).

That makes one comparison decisive: **the parents' contribution from income
alone versus the cost of attendance.** If income alone already exceeds the
cost, no asset decision can create need — and every asset move made "for aid"
is a cost with no benefit.

## The decision rule

| Income-only contribution vs. highest listed cost | Report says |
|---|---|
| Above | **No need-based aid is reachable.** Don't time a home purchase, spend down savings or move a child's money for aid. On projected (unpublished) tables the verdict is shown with its margin and a recheck, not in bold. |
| Below, but assets push SAI above cost | Assets matter; each $10,000 of reportable parent assets moves SAI by up to $564. |
| Below, and SAI below cost | Need-based aid is plausible; asset placement matters at the margin. |

## Rules the report applies

- **Income year is prior-prior:** award year 2031-32 uses 2029 income; any other
  year stops the report. Assets are as of the filing date.
- **Excluded assets:** retirement accounts (`tier: age_restricted`), life-insurance
  cash values and pensions, a primary residence (`primary_residence: true`),
  personal vehicles, `pending` rows. Negative rows (liabilities) are not netted;
  `margin_debt` is netted from its own account.
- **Counted assets:** everything else, including private investments and other
  real estate. Business or farm equity is counted at its recorded value and
  flagged. **529s and Coverdells are parent assets whoever owns them**; other
  accounts owned by the student (UTMA, student brokerage) count at 20%.
- **Education accounts are counted once:** link an account to the balance-sheet
  row that already includes it with `balance_sheet_row`. An unlinked account
  next to an unclaimed `earmark: education` row stops the report.
- **Payroll allowance** follows §1087oo(c)(2): the Social Security base is
  doubled on a joint return whoever earns the wages, and Medicare includes the
  additional 0.9%.
- **Unknowns stay unknown:** a missing value, cost or student income is listed
  and makes the result a lower bound; it is never read as zero.
- **Foreign assets** count unless `include_foreign_assets: false`. The report
  notes that a real filing must follow the form's instructions.
- **No state tax allowance, no two-in-college reduction, asset protection
  allowance of zero** (2026-27 tables) — all FAFSA Simplification changes.
- A dependent with `fafsa_eligible: false` (for example, not a U.S. citizen or
  eligible noncitizen) is listed but not computed.

## What it will not do

- Model the **CSS Profile** or any institutional methodology. Many private
  colleges count home equity and divide by number in college; run each
  school's Net Price Calculator.
- Model state aid programs, Pell Grant scheduling or independent students.
- Infer income or tax. `parent_total_income` and `parent_federal_income_tax`
  are supplied, not estimated.

## Weakest input

The **income year**. A one-off gain or a job loss two years before enrolment
moves the SAI more than any asset decision. When the award year's tables are
not yet published, the latest published year is used and the report says so.

## Closing

Use the result to decide whether aid belongs in a housing or savings decision
at all — usually it does not.

*Not financial, tax, or legal advice.*
