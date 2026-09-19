# Rental deal underwriting

**2 of 3 deals fail the 1.20 DSCR floor** — Maple Ridge home, Gulf Coast cabin. At that leverage the property does not service its own debt and the borrower's salary is the reserve.

Every figure below is **pre-investor-tax and nominal**. No after-tax return is available until `passive-loss-eligibility` says a §469 door is open.

| Deal | Price | Cash in | NOI yr1 | Cap rate | CoC | DSCR | IRR | Multiple |
|---|---|---|---|---|---|---|---|---|
| Maple Ridge home | $520,000 | $143,750 | $19,454 | 3.74% | -8.97% | **0.64** | -7.0% | 0.79× |
| Cedar Park duplex | $420,000 | $156,000 | $28,740 | 6.84% | 3.12% | 1.34 | 9.6% | 1.81× |
| Gulf Coast cabin | $420,000 | $51,000 | $13,116 | 3.12% | -35.62% | **0.44** | -5.6% | 0.30× |

NOI excludes debt service **and** capital expenditure — that is what makes the cap rate comparable across differently financed buyers. The capital reserve is subtracted below NOI, in cash flow.

## Maple Ridge home

Loan $390,000 · annual debt service $30,354 · net sale proceeds at exit $150,423

| Year | Gross rent | NOI | Debt service | Capex reserve | Cash flow |
|---|---|---|---|---|---|
| 1 | $46,284 | $19,454 | $30,354 | $1,990 | $-12,891 |
| 2 | $47,719 | $19,913 | $30,354 | $2,052 | $-12,494 |
| 3 | $49,198 | $20,380 | $30,354 | $2,116 | $-12,090 |

- **DSCR of 0.64 is below the 1.20 lender floor.** Most DSCR and agency programmes will not write it at this leverage. The fix is a larger down payment or a lower price, not a more optimistic rent — and if the property cannot service its own debt, the borrower's W-2 is the reserve.
- Cap rate of 3.7% is below 5.0%. Whatever return this deal produces is coming from appreciation and amortisation, not from the asset's income. The 2.8% appreciation assumption is therefore doing most of the work in the IRR below, and it is an assumption, not a cash flow.
- Year-1 cash-on-cash is -9.0% — the property consumes $12,891 of outside cash per year. That is a position, not necessarily a mistake, but it has to be funded from somewhere for 3 years and the funding has to be named.
- Weakest input: the **2.8% appreciation** assumption — $150,423 of the return arrives as sale proceeds at the horizon, so the IRR is a forecast wearing a metric's clothes. The year-1 figures above it are not.

## Cedar Park duplex

Loan $273,000 · annual debt service $21,466 · net sale proceeds at exit $232,142

| Year | Gross rent | NOI | Debt service | Capex reserve | Cash flow |
|---|---|---|---|---|---|
| 1 | $48,000 | $28,740 | $21,466 | $2,400 | $4,874 |
| 2 | $49,440 | $29,523 | $21,466 | $2,472 | $5,584 |
| 3 | $50,923 | $30,326 | $21,466 | $2,546 | $6,314 |
| 4 | $52,451 | $31,151 | $21,466 | $2,623 | $7,062 |
| 5 | $54,024 | $31,997 | $21,466 | $2,701 | $7,830 |
| 6 | $55,645 | $32,866 | $21,466 | $2,782 | $8,617 |
| 7 | $57,315 | $33,757 | $21,466 | $2,866 | $9,425 |

- DSCR of 1.34 clears the 1.25 comfort level — the property services its own debt with margin.
- Weakest input: the **3.0% appreciation** assumption — $232,142 of the return arrives as sale proceeds at the horizon, so the IRR is a forecast wearing a metric's clothes. The year-1 figures above it are not.

## Gulf Coast cabin

Loan $378,000 · annual debt service $29,723 · net sale proceeds at exit $136,663

| Year | Gross rent | NOI | Debt service | Capex reserve | Cash flow |
|---|---|---|---|---|---|
| 1 | $31,200 | $13,116 | $29,723 | $1,560 | $-18,167 |
| 2 | $32,136 | $13,430 | $29,723 | $1,607 | $-17,899 |
| 3 | $33,100 | $13,751 | $29,723 | $1,655 | $-17,627 |
| 4 | $34,093 | $14,078 | $29,723 | $1,705 | $-17,349 |
| 5 | $35,116 | $14,412 | $29,723 | $1,756 | $-17,066 |
| 6 | $36,169 | $14,753 | $29,723 | $1,808 | $-16,778 |
| 7 | $37,254 | $15,101 | $29,723 | $1,863 | $-16,484 |

- **DSCR of 0.44 is below the 1.20 lender floor.** Most DSCR and agency programmes will not write it at this leverage. The fix is a larger down payment or a lower price, not a more optimistic rent — and if the property cannot service its own debt, the borrower's W-2 is the reserve.
- Cap rate of 3.1% is below 5.0%. Whatever return this deal produces is coming from appreciation and amortisation, not from the asset's income. The 3.0% appreciation assumption is therefore doing most of the work in the IRR below, and it is an assumption, not a cash flow.
- Year-1 cash-on-cash is -35.6% — the property consumes $18,167 of outside cash per year. That is a position, not necessarily a mistake, but it has to be funded from somewhere for 7 years and the funding has to be named.
- Weakest input: the **3.0% appreciation** assumption — $136,663 of the return arrives as sale proceeds at the horizon, so the IRR is a forecast wearing a metric's clothes. The year-1 figures above it are not.

## Before acting

- **Verify rents against signed leases**, not a broker's pro forma. Market rent and in-place rent are different numbers and only one of them is collectable next month.
- **Get the last two years of operating statements** and the property tax bill. Taxes usually reassess on sale, and the seller's bill is not yours.
- **Insurance is quoted, not estimated.** In several markets it is now the line that moves a deal from workable to not.
- **The reserve is not the down payment.** Capital events arrive early and do not wait for the reserve to accumulate.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/realestate.py` with their reasons; every figure above is derived, not restated. Rent, expenses and appreciation are yours, not fetched. The IRR depends mostly on the appreciation assumption; the year-one figures do not.*
