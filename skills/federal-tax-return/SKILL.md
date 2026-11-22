---
name: federal-tax-return
description: Prepare a U.S. federal Form 1040 workpaper for one tax year from source-document figures (W-2, 1099-INT/DIV/B, Schedule C, HSA, IRA/8606, Schedule A) — line-by-line income, AGI, deduction, taxable income, regular tax, AMT, credits, SE tax, NIIT, Additional Medicare Tax, payments, refund or balance due, the underpayment-penalty safe harbor, next year's quarterly estimates, the forms triggered and a checklist of missing documents. Use when checking a return before filing, reconciling tax software output, deciding whether estimated payments are enough, or explaining a surprise balance due. Prepares and checks; does not e-file. Reads figures from a local facts file.
requires:
  - tax_return.tax_year
  - tax_return.filing_status
  - tax_return.taxpayers
---

# Federal Tax Return Workpaper

## The idea

A return is a **chain of dependent lines**: AGI sets the medical floor, the
SALT cap and the charitable floor; the deduction sets taxable income; taxable
income sets the QBI limit, the capital-gain bands and the credit phase-outs.
One unknown link makes every later line a guess. So the skill computes the
chain from the documents themselves, and when a figure that determines tax is
missing it **stops and lists it** rather than filling the gap.

The decision it supports is narrow and practical: **is this return right, and
is enough being paid in, on time?**

## What it computes

| Area | Rule applied |
|---|---|
| Wages | W-2 box 1, including RSU vesting and bonus. Supplemental wages withheld at the 22% flat rate against a higher marginal rate are named as a cause of any balance due. |
| Interest, dividends | Treasury interest is taxable here and carried for the state return; qualified dividends and net long-term gain use the 0/15/20% worksheet. Schedule B above the threshold. |
| Social Security, state refund | Taxable benefits by the 1040 worksheet (50%/85% tiers; MFS living together has no base); a state/local refund taxable only to the extent last year's itemized SALT deduction saved tax. |
| Capital gains | Short and long netting, wash-sale add-back, the loss limit (half for MFS), and the carryover split short/long using the Schedule D worksheet. |
| Schedule C | Net profit or loss; home office cannot create a loss (carried forward unless the simplified method was used); SE tax only at or above the earnings floor, with the OASDI base reduced by the owner's W-2 Social Security wages; half deductible. |
| QBI | 20% below the threshold, limited by taxable income less net capital gain. In and above the phase-in range: the W-2-wage/UBIA limit and SSTB phase-out, **or a refusal** if sstb, w2_wages and ubia are not recorded. A net loss gives no deduction and carries forward. The 2026 minimum deduction applies to active businesses. |
| K-1s | Partnership and S-corp K-1s for a materially participating owner (from `llc-tax-return`): ordinary income and guaranteed payments to Schedule E part II, interest and dividends to their lines, 1065 SE earnings to Schedule SE with wage-base netting (no SE tax on 1120S income), QBI items into §199A. Distributions are informational; basis stays with the entity skill. |
| HSA | Deduction = personal contributions within the self/family limit, prorated by eligible months, net of employer contributions. Catch-up for the account owner (self-only) or each spouse 55+ (family). Excess flagged. Non-qualified distributions are taxed, with the 20% additional tax when the account owner is under 65. |
| IRA / backdoor Roth | Entries are aggregated per owner. A `deductible` contribution passes the §219(g) workplace-plan phase-out first, and the rest becomes basis. Then the Form 8606 pro-rata rule applies using the summed Dec 31 traditional/SEP/SIMPLE balance. A non-zero balance is a finding. |
| Deduction | Itemized (reusing `cashflow.ItemizedDeductionRules`: SALT cap and phase-down, medical floor, mortgage debt limit, 60/30/50% charitable AGI limits with carryforward, 0.5% charitable floor, 2/37 limitation) vs standard plus 65+/blind amounts **plus** the non-itemizer cash charitable deduction. Plus the 65+ senior deduction for 2025–2028, which is added back for AMT. On MFS, the return must itemize when the spouse itemizes. |
| Credits | Child tax credit and credit for other dependents with the phase-out and refundable ACTC. The residency test accounts for a child born or who died in the year. Foreign tax credit by the simplified election, or by the Form 1116 limit on routed foreign-source income with the capital-gain rate adjustment and carryover. Excess Social Security withheld by two different employers. |
| Foreign income | `foreign` interest, dividends and capital transactions are routed to lines 2b, 3a/3b and Schedule D. Schedule B Part III is triggered whenever foreign accounts or income exist. Foreign rent and unrouteable totals are refused. |
| Other taxes | NIIT on the lesser of net investment income and MAGI over the threshold; Additional Medicare Tax on wages plus SE income, crediting employer withholding under the per-employer rule; AMT with the standard or SALT add-back. |
| Payments | Withholding plus estimates; refund or balance due. |
| Penalty | Safe harbor = lesser of 90% of this year's tax and 100% (110% above the prior-AGI threshold) of last year's, tested quarter by quarter with withholding spread evenly. Next year's quarterly estimate from the 100/110% rule. |

Parameters are a cited table per tax year (2025, 2026). A year not in the
table uses the nearest and every figure is labelled a projection.

## Unknown is not zero

- A `null` figure that determines tax (wages, a basis, a Schedule C amount,
  a year-end IRA balance when converting, prior 8606 basis) **stops** the
  report with the list.
- A `null` deduction (an itemized amount, HSA coverage) is left out and the
  result is labelled an **upper bound on tax**; a `null` payment leaves the
  refund **undetermined**.
- An absent list means none on file; a list set to `null` means unknown.

## What it will not do

- **Refuses**: foreign rent, PFIC rows and the old single `foreign.income`
  total; §199A REIT dividends and unrecaptured §1250 gain on a 1099-DIV;
  non-conversion IRA distributions; passive K-1s, trust K-1s, K-1 rental income, §179 and other
  K-1 codes, and rental/passive activities (see `passive-loss-eligibility`),
  depreciation schedules (`depreciation-election`),
  PFICs (`pfic-divest-or-comply`), nonresident or dual-status returns, ISO
  exercises and other AMT preferences, collectibles and §1250 gain, the excess
  business loss limit, and foreign income outside the passive category
  (`feie-vs-ftc`).
- **Flags without computing**: the kiddie tax on a dependent's own return,
  FBAR and Form 8938 (`foreign-reporting-audit`), the annualized-income
  penalty method, the AMT foreign tax credit, the HSA last-month rule, and
  the qualifying-relative tests for dependents aged 19+.
- Not modelled: tips/overtime/car-loan deductions, education credits, EITC,
  dependent-care credit, SEP/solo-401(k) and SE health-insurance adjustments.
  A return that needs them is understated by this workpaper.
- It does not e-file, and IRS tax tables (which round taxable income below
  the table ceiling to bands) can differ from the exact formula by a few dollars.

## Weakest input

**Basis** — 1099-B cost basis for noncovered shares and the Dec 31 traditional
IRA balance for Form 8606. Neither is on the year's forms, and each moves
taxable income dollar for dollar.

## Closing

Use the workpaper to check software output line by line and to set next
year's estimates; a disagreement is a question to resolve, not an answer.

*Not financial, tax, or legal advice.*
