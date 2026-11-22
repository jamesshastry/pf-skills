---
name: llc-tax-return
description: Prepare the tax workpaper for a U.S. LLC for one tax year from its bookkeeping ledger, by federal classification — Schedule C figures for a disregarded single-member LLC, Form 1065 with a K-1 per member for a partnership, or Form 1120-S with officer wages and a K-1 per shareholder for an S corporation — plus 50% meals, the home-office limit, start-up and organizational costs, owner basis and loss limits, reasonable compensation, 1099-NEC obligations, filing deadlines and late penalties, and California Form 568 (annual tax and LLC fee) or Form 100S. Use when closing an LLC's books, checking a preparer's entity return, or producing the Schedule C or K-1 rows that the federal-tax-return skill reads. Prepares and checks; does not e-file. Reads figures from a local facts file.
requires:
  - tax_return.tax_year
  - llc_returns
---

# LLC Tax Return Workpaper

## The idea

An LLC has no tax identity of its own. **Its classification decides which
return exists, which lines the ledger lands on, and what reaches each owner.**
The same ledger is a Schedule C (disregarded), a Form 1065 (partnership) or a
Form 1120-S (S corporation), and the costly mistakes are classification
mistakes: SE tax charged on S-corp K-1 income, guaranteed payments left out of
a partner's SE earnings, an S corporation paying its owner only
distributions, a California fee estimate never sent, a contractor with no W-9.

The decision it supports: **are this LLC's returns right, filed on time, and
is each owner's share in their own return in the right form?**

## What it computes

| Area | Rule applied |
|---|---|
| Ledger → lines | Each expense category is mapped to its Schedule C, Form 1065 or Form 1120-S line (2025 forms); unknown categories go to other expenses with a prompt to itemize. Meals at 50% (§274(n)). |
| Home office | Disregarded only. Simplified ($5 × up to 300 sq ft, no carryforward) or actual (Form 8829); cannot create a loss, excess carried forward. A partnership or S corporation does not deduct it — the report says what the member should do instead. |
| Start-up / organizational | §195 (and §709 for a partnership, §248 for an S corporation): $5,000 expensed in the year business begins, reduced dollar for dollar above $50,000, the rest over 180 months from the month business began. A disregarded LLC has no §248/§709, so formation costs join §195. |
| Disregarded | No federal entity return. Spouses under Rev. Proc. 2002-69 get one row each, split by `se_share`. The Schedule C row in exactly the shape `tax_return.schedule_c[]` takes, so `federal-tax-return` computes SE tax and §199A. States whether net SE earnings reach the $400 floor. |
| Partnership | Ordinary business income after guaranteed payments; K-1 boxes 1, 4a, 4c, 5, 6a, 14A (share plus guaranteed payments for active members, guaranteed payments only otherwise), 18C nondeductible expenses, 19A/19F distributions (2025 codes: F for partners providing services), 20Z §199A items. `material_participation` is a separate input from `active`. Rows for `tax_return.k1[]`. |
| S corporation | Officer wages and employer payroll tax deducted; K-1 boxes 1, 4, 5a, 16C, 16D, 17V; no SE tax. Officer W-2s for `tax_return.w2[]` in that skill's field names. Distributions out of proportion to shares are flagged (one class of stock). |
| Reasonable compensation | The IRS position (Rev. Rul. 74-44; Form 1120-S instructions, line 7): services are paid as wages before distributions. **Flag** at zero wages with profit or distributions, or below an asserted `reasonable_salary_floor`; **review** when wages are under distributions. No ratio is treated as a rule. |
| Basis | Partnership outside basis (§704(d)) or S-corp stock + debt basis (§1366(d)): contributions and income, then distributions, then nondeductible expenses, then losses. Excess distributions are gain; losses beyond basis are suspended. Unknown basis gives a bounded answer. |
| Hobby loss | A loss with `prior_year_results` is tested against the §183(d) 3-of-5-years presumption. |
| 1099-NEC | Payees at or above the year's threshold, except corporations (attorneys always). `w9_on_file: false` → 24% backup withholding flag (unknown is bounded, not asserted). Card and payment-network payments are 1099-K, not 1099-NEC. Due January 31. California adds EDD DE 542 for individual contractors. |
| Deadlines and penalties | Schedule C with the 1040; Form 1065 / 1120-S by the 15th day of the 3rd month, with the per-owner monthly late penalty (§6698/§6699) and the Rev. Proc. 84-35 note for small partnerships. |
| California | Disregarded or partnership: Form 568, $800 annual tax (FTB 3522), LLC fee by total California income (FTB 3536, estimate due the 15th day of the 6th month of the LLC's taxable year counted from formation; 10% penalty on a short estimate unless it covered last year's fee), the 15-day first-year exemption, and the $18-per-member late-filing penalty. S corporation: Form 100S at the greater of 1.5% of net income and the $800 minimum, 100-ES installments cumulatively 30/70/70/100% with the $800 due first; **no** Form 568, annual LLC tax or LLC fee. Other states: named as not modelled. |

Year-specific figures (1099-NEC threshold, standard mileage rate, late-filing
penalty) are a cited table per tax year (2025, 2026); a year not in the table
uses the nearest and says so.

## Unknown is not zero

- A `null` figure that determines income (receipts, COGS, an expense,
  guaranteed payments, officer wages, employer payroll tax) **stops** that
  LLC's workpaper and lists it.
- A `null` that only feeds a check — owner basis, a distribution, a
  contractor's W-9 or entity type, a California payment, `depreciation` —
  is listed, and the check is reported as bounded or undetermined.
- An absent list means none; a list set to `null` means nobody looked.

## What it will not do

- **Refuses, with a pointer**: rental or real-estate LLCs
  (`passive-loss-eligibility`), asset-level depreciation and §179 detail
  (`depreciation-election` — enter the amount it produces), inventory beyond
  a supplied COGS figure, multi-state apportionment, foreign owners and §1446,
  C-corporation classification, special allocations / §754 / §704(c), payroll
  filing mechanics (941/940/DE 9), an S election effective mid-year.
- Does not compute the owner's SE tax, §199A deduction or income tax — those
  belong to `federal-tax-return` once the hand-off rows are pasted in.
- At-risk (§465) and passive (§469) limits after basis are named, not applied.
- California net income for Form 100S is approximated from federal ordinary
  income; whether an LLC electing S status gets the corporate first-year
  minimum-tax exemption is flagged, and the $800 kept.
- Calendar tax year only; weekend due dates roll, holidays do not.

## Weakest input

**Owner basis.** It decides whether a loss is deductible and whether a
distribution is taxable, and it lives outside the year's ledger —
contributions, prior K-1s, and each member's share of liabilities.

## Closing

Paste the hand-off rows into the facts file and run `federal-tax-return` (and
`ca-tax-return`); a disagreement with a preparer's return is a question to
resolve, not an answer.

*Not financial, tax, or legal advice.*
