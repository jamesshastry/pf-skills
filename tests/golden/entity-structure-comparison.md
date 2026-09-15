# Entity structure comparison

Business: $265,000 revenue − $61,000 expenses = **$204,000 net profit** · graphic_design

**S-Corp election produces the most take-home** on these figures: $149,018.

| Structure | Owner salary | Payroll tax | §199A deduction | Income tax | Take-home |
|---|---|---|---|---|---|
| Schedule C / single-member LLC | — | $28,341 | $37,966 | $36,447 | **$139,211** |
| S-Corp election | $72,000 | $11,016 | $25,298 | $41,566 | **$149,018** |
| C-Corp | $72,000 | $11,016 | none | $62,630 | **$130,354** |

*Take-home is cash in the owners' hands after federal and state tax, before any retirement contribution. The federal figure applies your marginal rate to taxable income rather than a bracket schedule, so the **gaps between rows** are reliable and the levels are approximations.*

## The salary optimum

W-2 salary reduces payroll tax exposure **and** reduces qualified business income. Those pull in opposite directions, so reasonable salary has an optimum rather than a floor.

| Salary | §199A deduction | Payroll tax | Take-home |
|---|---|---|---|
| $72,000 | $25,298 | $11,016 | **$149,018** |
| $93,780 | $20,609 | $14,348 | $144,960 |
| $116,220 | $15,778 | $17,782 | $140,779 |
| $138,000 | $11,089 | $21,114 | $136,721 |
| $159,780 | $6,399 | $24,446 | $132,663 |
| $182,220 | $1,568 | $27,880 | $128,482 |
| $204,000 | $42 | $28,376 | $127,679 |

- **Take-home falls monotonically as salary rises.** Every dollar moved from distribution to salary costs payroll tax and shrinks QBI, and nothing pushes the other way. The optimum is therefore the *lowest defensible* salary, and 'defensible' is the binding constraint — not arithmetic.

## The same election at a different profit level

The verdict is not a property of the business, it is a property of the profit. A reasonable salary that is defensible in a good year consumes most of a slow year's profit, leaving little to shelter as a distribution while the running cost stays the same.

**A slow year** — $118,000 revenue, $57,000 net profit

- **The S-Corp election loses $4,927/yr net of its $2,400 running cost.** Stay on Schedule C. The election is not a one-way door, but it is a standing obligation: quarterly payroll filings that must happen whether or not the business had a good year.

## What the arithmetic says, and what it does not

**Schedule C / single-member LLC**

- Taxable income is below the §199A threshold, so the W-2 wage limit does not apply at all. Salary buys no deduction here — it only costs FICA and shrinks QBI.
- Half the SE tax is deducted above the line, and that deduction also **reduces QBI** — as does a deductible self-employed health insurance premium and any employer retirement contribution. Neither of the last two is modelled here; both make the §199A figure above slightly optimistic. See `solo-retirement-plan-choice`.

**S-Corp election**

- Taxable income is below the §199A threshold, so the W-2 wage limit does not apply at all. Salary buys no deduction here — it only costs FICA and shrinks QBI.

**C-Corp**

- **No §199A deduction exists for a C-Corp**, and the profit is taxed twice when it comes out. Retaining earnings defers the second layer rather than removing it, and retention has its own limits — the accumulated earnings tax and the personal holding company rules.
- **The C-Corp figure is optimistic and should be read as a ceiling.** State *corporate* income tax and franchise tax are not modelled — the state rate here is applied only to what reaches the owners — and most states tax corporate income as well. Where the comparison is close, that omission alone can decide it.
- The case for a C-Corp is usually **not** this arithmetic. It is §1202 qualified small business stock on an eventual sale, an outside investor who will not hold S-Corp shares, or a genuine need to retain capital in the business. None of those are modelled here, and the first depends entirely on an exit this skill knows nothing about.

- **The S-Corp election nets $9,806/yr** after its $2,400 running cost, at a salary of $72,000. That clears the cost comfortably.

## The weakest input

**The reasonable salary floor of $72,000.** It is an assertion, not a computation, and it carries the whole S-Corp result. If it cannot be supported with comparable compensation data, the election is not supportable either — the IRS can recharacterise distributions as wages, with payroll tax, penalties and interest.

**Beneficial ownership information (BOI) reporting is not modelled here.** It has been reported that an August 2026 FinCEN final rule exempts US domestic companies, leaving only foreign-formed entities in scope. **That is unverified** — it is repeated as reported, not asserted, and the Corporate Transparency Act's scope has moved more than once. Check fincen.gov/boi before concluding you have nothing to file. The penalty falls on the filer.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/entity.py` with their reasons; every figure above is derived, not restated. An entity election has legal and liability consequences beyond tax, and the S-Corp election has deadlines. Take this to a CPA before filing Form 2553.*
