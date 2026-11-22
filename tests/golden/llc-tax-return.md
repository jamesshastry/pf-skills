# LLC Tax Return Workpaper

Tax year 2026; 3 LLC(s). Parameters: P.L. 119-21 §70433 and Rev. Proc. 2025-32 §2.15 ($2,000 for payments after 2025, indexed from 2027); IR-2025-128 (72.5¢ Jan-Jun) and IR-2026-29 (76¢ Jul-Dec); Rev. Proc. 2025-32 §3.55-3.56 ($260 for returns required to be filed in 2027).

## Rivera Design LLC — Schedule C (Form 1040)

**Tax year 2026**, classified as disregarded (single-member); state of registration: TX.

### The answer

**No federal entity return.** Net profit of **$201,600** goes on a2's Schedule C.

Net earnings from self-employment are $186,178 (92.35% of $201,600), at or above $400: SE tax applies. federal-tax-return computes it (with the owner's W-2 Social Security wages).

### Schedule C (Form 1040) lines

| Line | Item | Amount |
|---|---|---|
| 1 | Gross receipts or sales | $265,000 |
| 7 | Gross income | $265,000 |
| 9 | Car and truck expenses (actual, business share) | −$3,800 |
| 11 | Contract labor | −$22,000 |
| 15 | Insurance | −$3,000 |
| 22 | Supplies | −$14,000 |
| 27b | Software | −$9,000 |
| 27b | Other | −$9,200 |
| 28 | Total expenses | −$61,000 |
| 30 | Business use of home (actual) | −$2,400 |
| 31 | Net profit or (loss) | $201,600 |

Home office (actual): $2,400 claimed, $2,400 allowed against the business's income.

### Owner hand-off

Paste into `tax_return.schedule_c` — `federal-tax-return` applies the home-office limit, SE tax and §199A from it:

```yaml
- { owner: a2, business: Rivera Design LLC, gross_receipts: 265000, expenses: { supplies: 14000, software: 9000, contract_labor: 22000, insurance: 3000, other: 9200 }, vehicle: 3800, home_office: 2400, home_office_method: regular, sstb: false, w2_wages: 0, ubia: 18000 }
```

### Form 1099-NEC

Threshold for 2026: **$2,000** per payee; due <DATE>.

| Payee | Paid | Type | W-9 | 1099-NEC | Backup withholding |
|---|---|---|---|---|---|
| Lena Park | $15,000 | individual | yes | required | — |
| Brightline Studio Inc | $5,000 | corporation | no | not required | — |
| Sam Ortiz | $1,500 | individual | no | not required | — |
| Rae Quinn | $500 | individual | yes | not required | — |
| Pixel Stock Co | $3,000 | llc | unknown | not required | — |

### Deadlines

| Due | What |
|---|---|
| <DATE> | Forms 1099-NEC to payees and the IRS |
| <DATE> | Schedule C with the owner's Form 1040 (no federal entity return) |

Weekend due dates move to Monday; legal holidays are not modelled.

### Findings

- Categories software have no dedicated line and are reported as other expenses (Part V) — itemize them on the attached statement.
- Pixel Stock Co: paid by card — reported on Form 1099-K by the processor, not on 1099-NEC (Reg. §1.6041-1(a)(1)(iv)).
- State obligations for TX are not modelled — check that state's LLC registration fee, franchise or gross-receipts tax and annual report.

## Harbor Lane Studio LLC — Form 1065

**Tax year 2026**, classified as partnership (multi-member); state of registration: CA.

### The answer

**Form 1065** with ordinary business income of **−$25,444**, passed through to 2 owner(s) on Schedule K-1.

m3: box 14A $164,733 → SE tax on the member's own Schedule SE (computed by federal-tax-return).

> m3: loss of $15,267 is deductible only up to basis (§704(d)); basis is not recorded, so between 0 and $15,267 is suspended.

> m3: distributions of $10,000 with unknown basis — any excess over basis is taxable gain (§731(a)).

### Form 1065 lines

| Line | Item | Amount |
|---|---|---|
| 1a | Gross receipts or sales | $310,000 |
| 1b | Returns and allowances | −$4,000 |
| 8 | Gross income | $306,000 |
| 10 | Guaranteed payments to partners | −$180,000 |
| 13 | Rent | −$36,000 |
| 16c | Depreciation (from depreciation-election) | −$22,000 |
| 21 | Supplies | −$12,000 |
| 21 | Software | −$18,000 |
| 21 | Advertising | −$9,000 |
| 21 | Contract labor | −$30,000 |
| 21 | Insurance | −$4,000 |
| 21 | Legal and professional | −$6,000 |
| 21 | Utilities | −$5,000 |
| 21 | Meals (50% of $3,000) | −$1,500 |
| 21 | Start-up / organizational costs (Form 4562 Part VI) | −$7,944 |
| 22 | Total deductions | −$331,444 |
| 23 | Ordinary business income (loss) | −$25,444 |

Start-up and organizational costs (business began <DATE>):

| Cost | Incurred | Expensed now | Amortized this year | Left to amortize |
|---|---|---|---|---|
| §195 start-up | $54,000 | $1,000 | $2,944 (10 mo × $294) | $50,056 |
| §709 organizational | $4,000 | $4,000 | $0 (10 mo × $0) | $0 |

### Owner hand-off

| Box | Item | a1 | m3 |
|---|---|---|---|
| 1 | Ordinary business income (loss) | −$10,178 | −$15,267 |
| 4a | Guaranteed payments for services | $0 | $180,000 |
| 4c | Total guaranteed payments | $0 | $180,000 |
| 5 | Interest income | $0 | $0 |
| 6a | Ordinary dividends | $0 | $0 |
| 14A | Net earnings (loss) from self-employment | $0 | $164,733 |
| 18C | Nondeductible expenses | $600 | $900 |
| 19A / 19F | Distributions of cash | $0 | $10,000 |
| 20Z | §199A: QBI | −$10,178 | −$15,267 |
| 20Z | §199A: W-2 wages | $0 | $0 |
| 20Z | §199A: UBIA | $16,000 | $24,000 |

Paste each row into `tax_return.k1` for `federal-tax-return`:

```yaml
- { owner: a1, entity: Harbor Lane Studio LLC, form: 1065, ordinary_business_income: -10178, guaranteed_payments: 0, se_earnings: 0, interest: 0, dividends: 0, distributions: 0, qbi_income: -10178, qbi_w2_wages: 0, qbi_ubia: 16000, sstb: false, material_participation: false }
- { owner: m3, entity: Harbor Lane Studio LLC, form: 1065, ordinary_business_income: -15267, guaranteed_payments: 180000, se_earnings: 164733, interest: 0, dividends: 0, distributions: 10000, qbi_income: -15267, qbi_w2_wages: 0, qbi_ubia: 24000, sstb: false, material_participation: true }
```

### Basis and loss limit

| Owner | Start | + Contributions | + Income | − Distributions | − Nondeductible | Loss | Allowed | Suspended | Gain (excess distribution) | End |
|---|---|---|---|---|---|---|---|---|---|---|
| a1 | $8,000 | $0 | $0 | $0 | $600 | $10,178 | $7,400 | $2,778 | $0 | $0 |
| m3 | unknown | $0 | $0 | $10,000 | $900 | $15,267 | unknown | unknown | unknown | unknown |

Order: contributions and income increase basis first, then distributions, then nondeductible expenses, then losses (Reg. §1.1367-1(f); §1.704-1(d)(2)).

### Form 1099-NEC

Threshold for 2026: **$2,000** per payee; due <DATE>.

| Payee | Paid | Type | W-9 | 1099-NEC | Backup withholding |
|---|---|---|---|---|---|
| Dana Wu | $24,000 | individual | no | required | $5,760 |
| Coastline Print LLC | $6,000 | llc | yes | required | — |

California also requires EDD Form DE 542 within 20 days for individual contractors paid $600 or more: Dana Wu.

### California

| Form 568 | Amount |
|---|---|
| Annual LLC tax (FTB 3522) | $800 |
| Total California income (fee base) | $306,000 |
| LLC fee (FTB 3536) | $900 |
| 10% estimate-shortfall penalty | $90 |
| Paid (3522 + 3536 + other) | $800 |
| Balance due with Form 568 | $900 |

Form 568 with Schedule K-1 (568) per member, due the 15th day of the 3rd month. Nonresident members need Form 3832 consents or withholding (not modelled). Filing it late costs $18 × 2 member(s) = $36 per month, up to 12 months (Form 568 booklet, General Information G).

**Filing late** costs $260 × 2 owner(s) = $520 per month (§6698), up to $6,240 at 12 months — even with no tax due. Each Schedule K-1 furnished late is a separate §6722 penalty.
 A partnership of ten or fewer individual partners sharing every item pro rata can ask for relief under Rev. Proc. 84-35 — on request, not automatically.

### Deadlines

| Due | What |
|---|---|
| <DATE> | California $800 annual tax (FTB 3522) for 2026 |
| <DATE> | California LLC fee estimate (FTB 3536), $900 |
| <DATE> | Forms 1099-NEC to payees and the IRS |
| <DATE> | Form 1065 and Schedules K-1 (extension: Form 7004, six months) |
| <DATE> | California Form 568 (LLC fee balance with FTB 3536) |
| <DATE> | California $800 annual tax (FTB 3522) for 2027 |

Weekend due dates move to Monday; legal holidays are not modelled.

### Findings

- Categories software have no dedicated line and are reported as other deductions — itemize them on the attached statement.
- Box 14A treats members marked active as general partners (share of ordinary income plus guaranteed payments) and others as limited partners (guaranteed payments only, §1402(a)(13)). For an LLC member the limited-partner exception is contested (Soroban Capital Partners, T.C. 2023) — a passive label is not a safe harbor.
- Box 19: the 2025 Form 1065 instructions split cash distributions into code A (partners not providing services) and code F (partners providing services); members marked active are reported under F. Check the code list on the year's form.
- Guaranteed payments are deducted at the entity, excluded from QBI (§199A(c)(4)) and fully subject to SE tax for the recipient; no tax is withheld, so the member pays estimates.
- a1: $2,778 of the $10,178 loss exceeds basis and is suspended until basis is restored; at-risk (§465) and passive (§469) limits apply after this and are not modelled.
- A $25,444 loss. If losses recur, §183 can disallow them; the profit presumption needs a profit in 3 of 5 years. Record prior_year_results to test it.
- Dana Wu: no W-9 on file for $24,000 paid — backup withholding of 24% ($5,760) should have been withheld (§3406). The payer owes it if not; get the W-9 now.
- First year: the 2021–2023 first-year exemption has expired, so the $800 is owed for 2026, due <DATE> (15th day of the 4th month after formation).
- LLC fee of $900 against a timely estimate of $0: the 10% penalty on the shortfall is $90 (FTB 3536 was due <DATE>) — there is no preceding year, so the prior-year safe harbor is unavailable.

**Not recorded** (listed, never read as zero):

- `llc_returns[Harbor Lane Studio LLC].owner_basis_start[1].amount`

## Rivera Print Co LLC — Form 1120-S

**Tax year 2026**, classified as S corporation (Form 2553 election); state of registration: CA.

### The answer

**Form 1120-S** with ordinary business income of **$104,963**, passed through to 1 owner(s) on Schedule K-1.

S-corporation K-1 income carries no self-employment tax; payroll tax is paid on officer wages instead.

### Form 1120-S lines

| Line | Item | Amount |
|---|---|---|
| 1a | Gross receipts or sales | $180,000 |
| 2 | Cost of goods sold (supplied figure) | −$30,000 |
| 6 | Gross income | $150,000 |
| 7 | Compensation of officers | −$30,000 |
| 12 | Taxes and licenses (incl. employer payroll tax) | −$3,537 |
| 20 | Supplies | −$6,000 |
| 20 | Software | −$3,000 |
| 20 | Insurance | −$2,500 |
| 21 | Total deductions | −$45,037 |
| 22 | Ordinary business income (loss) | $104,963 |

### Owner hand-off

| Box | Item | a2 |
|---|---|---|
| 1 | Ordinary business income (loss) | $104,963 |
| 4 | Interest income | $0 |
| 5a | Ordinary dividends | $0 |
| 16C | Nondeductible expenses | $0 |
| 16D | Distributions | $90,000 |
| 17V | §199A: QBI | $104,963 |
| 17V | §199A: W-2 wages | $30,000 |
| 17V | §199A: UBIA | $26,000 |

Paste each row into `tax_return.k1` for `federal-tax-return`:

```yaml
- { owner: a2, entity: Rivera Print Co LLC, form: 1120S, ordinary_business_income: 104963, guaranteed_payments: 0, se_earnings: 0, interest: 0, dividends: 0, distributions: 90000, qbi_income: 104963, qbi_w2_wages: 30000, qbi_ubia: 26000, sstb: false, material_participation: true }
```

Officer wages arrive on the owner's W-2 — paste into `tax_return.w2`:

```yaml
- { employer: Rivera Print Co LLC, owner: a2, wages: 30000, federal_withheld: 3000, ss_wages: 30000, ss_withheld: 1860, medicare_wages: 30000, medicare_withheld: 435 }
```

### Basis and loss limit

| Owner | Start | + Contributions | + Income | − Distributions | − Nondeductible | Loss | Allowed | Suspended | Gain (excess distribution) | End |
|---|---|---|---|---|---|---|---|---|---|---|
| a2 | $20,000 | $0 | $104,963 | $90,000 | $0 | $0 | $0 | $0 | $0 | $34,963 |

Order: contributions and income increase basis first, then distributions, then nondeductible expenses, then losses (Reg. §1.1367-1(f); §1.704-1(d)(2)).

### Reasonable compensation

**Review** — the IRS position is that a shareholder-officer who performs services is paid wages before non-wage distributions (Rev. Rul. 74-44; Form 1120-S instructions, line 7). There is no ratio or percentage test.

| Owner | Officer wages | Distributions | Verdict |
|---|---|---|---|
| a2 | $30,000 | $90,000 | review |

### Form 1099-NEC

No contractors recorded.

### California

| Form 100S | Amount |
|---|---|
| California net income (approximation) | $104,963 |
| Tax at 1.5% | $1,574 |
| Minimum franchise tax | $800 |
| **Tax (greater of)** | **$1,574** |
| Paid (Form 100-ES) | $1,500 |
| Balance due with Form 100S | $74 |

Form 100S. An LLC taxed as a corporation is subject to the Corporation Tax Law and files Form 100S — not Form 568 — so it owes no LLC annual tax or LLC fee (2025 Form 568 booklet, "LLC Taxed as a Corporation").

**Filing late** costs $260 × 1 owner(s) = $260 per month (§6699), up to $3,120 at 12 months — even with no tax due. Each Schedule K-1 furnished late is a separate §6722 penalty.

### Deadlines

| Due | What |
|---|---|
| <DATE> | California Form 100-ES installment ($800) |
| <DATE> | California Form 100-ES installment ($302) |
| <DATE> | California Form 100-ES installment ($472) |
| <DATE> | Form 1120-S and Schedules K-1 (extension: Form 7004, six months) |
| <DATE> | California Form 100S (franchise tax balance due) |

Weekend due dates move to Monday; legal holidays are not modelled.

### Findings

- S election in force for the whole year. A late election needs Rev. Proc. 2013-30 relief; confirm the IRS acceptance letter (CP261) is on file.
- Categories software have no dedicated line and are reported as other deductions — itemize them on the attached statement.
- S-corporation basis here combines stock and debt basis; distributions reduce only stock basis, so a shareholder with loan basis should split them (Form 7203). A shareholder may elect to take losses before nondeductible expenses (Reg. §1.1367-1(g)); not modelled.
- Officer W-2 hand-off: box 1 wages equal the payroll amount; pre-tax 401(k) or cafeteria deferrals (which lower box 1 but not boxes 3/5) are not modelled — copy box 1 from the actual W-2.
- a2: wages of $30,000 are less than distributions of $90,000. There is no ratio test — the question is what the services would cost to hire — but this is the shape an examiner looks at. Record the comparable-pay evidence in reasonable_salary_floor.
- California net income is approximated as ordinary income plus interest and dividends ($104,963); the Form 100S computation starts from federal income with C-corporation-style California adjustments (depreciation, state tax) not modelled here.
- Form 100-ES installments fell short by <DATE> — an underpayment penalty may apply (FTB 5806, not computed; the prior-year-tax exception is not tested).

**Not recorded** (listed, never read as zero):

- `llc_returns[Rivera Print Co LLC].reasonable_salary_floor (comparable-pay evidence; asserted, never derived)`

**Weakest input:** owner basis — it decides whether a loss is deductible and whether a distribution is taxable, and it lives in records outside the year's ledger (contributions, prior K-1s, share of liabilities).

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/llc_return.py` with their reasons; every figure above is derived, not restated. This is a workpaper for checking an LLC's returns, not a filed return; it does not e-file.*
