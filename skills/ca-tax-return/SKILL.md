---
name: ca-tax-return
description: Prepare a California resident income tax return workpaper (Form 540 with Schedule CA) for one tax year, starting from the federal return. Applies each California disagreement with federal law as a named Schedule CA line (HSA add-backs, Treasury interest, no SALT cap, $1M mortgage limit), then the CA deduction, rate schedule, exemption credits, renter's credit, Behavioral Health Services Tax, payments, refund or balance due, next year's 30/40/0/30 estimated payments, and any single-member LLC's $800 tax and fee. Use when preparing or checking a California 540, estimating a CA refund or balance due, planning CA estimated payments, or checking LLC tax deadlines. Reads figures from a local facts file; prepares and checks, never e-files.
requires:
  - meta.jurisdiction
  - tax_return.tax_year
  - tax_return.filing_status
  - tax_return.state
  - tax_return.taxpayers
---

# California Tax Return

## The idea

California starts from **federal AGI** and then disagrees with it in a short,
enumerable list of places. CA returns go wrong because one of those
disagreements was missed, not because someone misread the rate schedule. So the
skill takes the federal return as given (from `federal-tax-return`) and applies
each disagreement as a named Schedule CA line. Then it carries the result
through Form 540.

## What the report decides

| Question | Rule applied |
|---|---|
| What is California AGI? | Federal AGI − Treasury interest, U.S.-obligation fund dividends, taxable state refund, Social Security, and HSA distributions not used for medical costs (already taxed by CA) + HSA payroll/employer contributions (W-2 box 12 W, else `hsa.employer_contributions`), the HSA deduction, HSA earnings, non-CA municipal interest (the box 8 amount), and depreciation differences |
| Itemize or standard? | Larger of the CA standard deduction or CA itemized. CA itemized allows no state income tax or SDI and has no SALT cap. It keeps a $1M mortgage limit, a 7.5% medical floor, a 50%-of-AGI charitable limit, and miscellaneous deductions above 2%. Above the federal-AGI threshold it is cut by 6% of the excess, capped at 80% |
| Tax | CA rate schedule (1%–12.3%). Capital gains and qualified dividends are ordinary income |
| Exemption credits | Personal, blind, senior and dependent credits, each reduced by $6 for every $2,500 ($1,250 MFS) of federal AGI over the threshold |
| Renter's credit | Only if `ca.renter: true` and CA AGI is at or under the limit. Applied with other no-carryover credits **before** credits that carry over (R&TC §17039), never above the remaining tax |
| Behavioral Health Services Tax | 1% of taxable income over $1M. **The threshold does not double for joint filers** |
| Payments | CA withholding (W-2 box 17), estimates, overpayment applied. **SDI is not a payment.** Since 2024 SDI has no wage cap, so no excess-SDI credit exists |
| Penalty for underpaying estimates this year? | FTB 5805 regular method. Required annual payment is the smaller of 90% of this year's tax or 100% of last year's (110% if prior CA AGI > $150K). At $1M+ AGI, only the 90% test applies. Withholding counts as paid evenly; installments are 30/40/0/30 |
| Next year's estimates | Prior-year safe harbor (100%/110% of this year's tax) less withholding, paid 30/40/0/30 on Apr 15, Jun 15, (Sep 15: 0), Jan 15. The safe harbor is barred when **next** year's CA AGI is $1M or more ($500K MFS). Without `ca.next_year_agi_estimate` the schedule is printed on that condition. With an estimate at or above the line, the report says a projection is needed |
| LLC | $800 annual tax by the 15th day of the 4th month (FTB 3522). The fee runs $900 to $11,790 once total CA income reaches $250K, with the estimate due the 15th day of the 6th month (FTB 3536). An LLC formed in 2021–2023 owed no first-year tax. From 2024, the first year is owed by the 15th day of the 4th month after the Secretary of State filing |

## How to read it

- **Incomplete** means a figure was `null`. Each missing entry says which way it
  biases the result. An unknown HSA earnings figure, for example, makes CA AGI a
  lower bound. A null itemized item means the standard deduction is used, so the
  tax is an upper bound.
- **Projection** means the tax year's indexed CA amounts are not in the module
  yet. The latest published year is used instead. That overstates tax slightly,
  because indexing only raises the brackets.
- The tax comes from the rate schedule. Below $100,000 of taxable income the
  form uses the tax table, which can differ by a few dollars.

## What it will not do

Refuses, with a pointer:

- Part-year and nonresident returns (Form 540NR)
- The other-state tax credit (Schedule S)
- Kiddie tax (FTB 3800 / 3803)
- Rental, passive and K-1 income (FTB 3801)
- A taxpayer who can be claimed as a dependent
- Registered domestic partners
- Years before the earliest shipped table

**Flags but does not compute:** CA AMT (Schedule P), the Individual Shared
Responsibility penalty, refundable credits (CalEITC, YCTC), and penalty amounts.

## Closing

**Weakest input:** the federal return. Every line here starts from federal AGI.
After that, the HSA figures, because they are the CA adjustment most often
missed. Statutory amounts live in `lib/pf/ca_return.py` with their FTB sources,
and stay marked unverified until a human checks them.

*Not financial, tax, or legal advice.*
