# Housing affordability

## BLOCKED — financing or occupancy assumption

- Investment financing fails the recorded DSCR test: 0.64 is below 1.20.
- The target transition misses its prorated savings floor in 4 phase/scenario row(s).

**Target $520,000 exceeds the stress-tested ceiling of $98,030.**

All figures in this report are **nominal cash flow**. Affordability includes mortgage principal. The separate `rent-vs-buy` report treats principal as equity and compares the economic cost only after a price has been shown feasible here.

## Capacity and constraints

| Constraint | Limit |
|---|---|
| Current-income capacity | $263,262 |
| **Stress-tested ceiling** | **$98,030** |
| Controlling conservative case | Conservative employed |
| Lender maximum | $408,507 |
| Investment lender maximum | $277,721 |
| Liquidity/down-payment limit | $98,030 |
| Binding constraint | cash-only post-close reserve |

| Named income scenario | Kind | Cash-flow price limit |
|---|---|---|
| Current compensation | current | $263,262 |
| Conservative employed | conservative | $140,252 |

The stress-tested ceiling is a constraint, not the household's only affordable price. The **target** remains a separate decision below it.

## Reconciled cash-flow scenarios

| Scenario | Income components | Gross | Taxes | After-tax cash |
|---|---|---|---|---|
| Current compensation | bonus $21,350, equity $25,950, salary $132,700 | $180,000 | $40,173 | $139,827 |
| Conservative employed | bonus $8,030, equity $5,000, salary $132,700 | $145,730 | $30,190 | $115,540 |

| Scenario | Employee retirement + IRA | Employer retirement | Other payroll | Non-housing | Timed obligations | Other committed | Pre-housing surplus | Savings floor | Renter savings |
|---|---|---|---|---|---|---|---|---|---|
| Current compensation | $42,000 | $0 | $2,357 | $48,321 | $7,333 | $1,775 | $38,041 | $9,000 | $9,241 |
| Conservative employed | $30,000 | $0 | $2,157 | $48,321 | $7,333 | $1,775 | $25,954 | $7,286 | $-2,846 |

`pre-housing surplus` excludes both rent and ownership. The savings floor is the greater of the recorded dollar and gross-income-rate requirements when both are present.

## Candidate prices

| Price | Scenario | Full owner cash/yr | Principal/yr | Remaining savings | Savings rate | Post-close cash | Reserve months | Result |
|---|---|---|---|---|---|---|---|---|
| $87,500 | Current compensation | $14,219 | $731 | $23,822 | 13.2% | $39,179 | 6.6 | passes |
| $87,500 | Conservative employed | $14,219 | $731 | $11,735 | 8.1% | $39,179 | 6.6 | passes |
| $287,500 | Current compensation | $31,085 | $2,400 | $6,956 | 3.9% | $-16,109 | -2.2 | **fails** |
| $287,500 | Conservative employed | $31,085 | $2,400 | $-5,131 | -3.5% | $-16,109 | -2.2 | **fails** |
| $363,750 | Current compensation | $37,515 | $3,037 | $526 | 0.3% | $-37,188 | -4.7 | **fails** |
| $363,750 | Conservative employed | $37,515 | $3,037 | $-11,561 | -7.9% | $-37,188 | -4.7 | **fails** |
| $520,000 | Current compensation | $50,692 | $4,342 | $-12,651 | -7.0% | $-80,382 | -8.9 | **fails** |
| $520,000 | Conservative employed | $50,692 | $4,342 | $-24,738 | -17.0% | $-80,382 | -8.9 | **fails** |

Invariant checked on every row: `pre-housing surplus − full owner cash cost` equals `renter savings − (owner cash cost − rent)`. Incremental ownership cost is never subtracted from a pre-rent surplus.

Tax benefit excluded: itemization, filing status, deduction cap, and the renter baseline were not modeled.

### Target owner cash ledger

| Annual cash line | Amount |
|---|---|
| Principal and interest | $29,032 |
|   of which principal | $4,342 |
| Property tax | $9,620 |
| Insurance | $1,800 |
| Maintenance | $5,200 |
| HOA | $5,040 |
| PMI | $0 |
| Other owner costs | $0 |
| **Gross owner cash cost** | **$50,692** |
| Incremental tax benefit | excluded |

## Closing sources and uses

| Source | Amount |
|---|---|
| Cash and cash equivalents at face value | $40,000 |
| Marketable securities (not cash at par) | $45,000 |
| Restricted assets (not closing funds) | $338,000 |
| Illiquid assets (not closing funds) | $0 |
| Unclassified assets (excluded) | $0 |
| Spendable taxable-sale proceeds | $23,368 |

| Taxable liquidation | Amount |
|---|---|
| Gross sale proceeds | $27,970 |
| Less account debt payoff | −$4,321 |
| Less federal tax reserve | −$281 |
| Less state tax reserve | −$0 |
| **Spendable proceeds** | **$23,368** |
| Net-worth change from sale | −$281 |

The gross proceeds replace securities; they are not new wealth. Only taxes reduce net worth in this conversion ledger, while debt payoff removes an equal liability.

| Target sources and uses | Amount |
|---|---|
| Opening gross financial assets | $423,000 |
| Less securities sold | −$27,970 |
| Plus cash proceeds received | $27,970 |
| Less account debt payoff | −$4,321 |
| Less taxes reserved | −$281 |
| Less down payment and closing | −$143,750 |
| **Post-close financial assets and cash** | **$274,648** |

## Housing transition

Occupancy converts on **<DATE>**; financing is classified **investment**.

| Initial investment financing | Amount |
|---|---|
| Investment-property down payment | $130,000 |
| Investment-property closing costs | $13,750 |
| Initial investment loan | $390,000 |
| Investment lender test | DSCR 0.64 |
| Loan balance entering owner phase | $384,760 |
| Refinance cost | $6,500 |
| Cash reserve assumption | 6.0 months |

| Phase | Months | Current rent | Tenant gross | Vacancy/credit | Management | Turnover | Maintenance | Cap reserve | Tax | Insurance | HOA | Debt service | Other | Net cash flow |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Tenant phase | 15 | $36,000 | $58,214 | $3,493 | $4,371 | $1,150 | $3,550 | $2,503 | $12,118 | $2,754 | $6,347 | $37,943 | $0 | $-52,014 |
| Owner-occupancy phase | 21 | $0 | $0 | $0 | $0 | $0 | $9,217 | $0 | $17,051 | $3,190 | $8,933 | $50,805 | $6,500 | $-95,698 |

| Phase | Scenario | Pre-housing cash | Housing cash flow | Remaining cash | Prorated savings floor | Result |
|---|---|---|---|---|---|---|
| Tenant phase | Current compensation | $47,551 | $-52,014 | $-4,463 | $11,250 | **fails** |
| Tenant phase | Conservative employed | $32,442 | $-52,014 | $-19,572 | $9,108 | **fails** |
| Owner-occupancy phase | Current compensation | $66,572 | $-95,698 | $-29,126 | $15,750 | **fails** |
| Owner-occupancy phase | Conservative employed | $45,420 | $-95,698 | $-50,278 | $12,751 | **fails** |
| **Combined** | Current compensation | — | $-147,712 | **$-33,589** | $27,000 | — |
| **Combined** | Conservative employed | — | $-147,712 | **$-69,850** | $21,860 | — |

Combined transition cash flow: **$-147,712**. The tenant phase is nominal and pre-investor-tax. Current rent and tenant income both end when owner occupancy begins.
The transition table evaluates the recorded **target property only**; its rent and operating expenses are not extrapolated to unrelated candidate prices.

- The §469 gate is shut or the loss is suspended; current rental tax benefit is zero.
- Taxable sale has not been checked against the household wash-sale policy; excluded-list overlap: PFE, XOM.

## Cross-skill checks

- **downpayment-vs-retirement:** A down payment moves a large sum out of invested assets. `housing-affordability` uses it at closing while `retirement-readiness` otherwise projects from a balance sheet that still includes the pre-close assets. Re-run the retirement projection with the down payment and closing costs removed from investable assets, and with ownership costs rather than rent in spending. The retirement date usually moves, and that movement is part of the price of the house.
- **downpayment-vs-emergency-reserve:** Closing funds and the emergency reserve compete for the same cash, while marketable stock is not cash at par for either purpose. Treat the reserve as a use at closing, not as money left over after the down payment. Count only cash equivalents at face value; convert planned securities through the taxable sources-and-uses ledger first. A price that needs the emergency reserve to close fails the liquidity test.
- **housing-cashflow-vs-savings-floor:** A lender may approve debt service that consumes the annual saving needed for the retirement plan. Apply the greater of the dollar and gross-income-rate savings floors before calling a price feasible. The lender maximum remains a separate outer limit, never the household target.
- **housing-liquidation-vs-wash-sale:** Selling taxable lots for closing can realise gains or losses while automated purchases or rebalancing can disallow the loss during the wash-sale window. Name the lots sold, reserve tax from basis and holding period, and clear every purchase channel against the exclusion list before relying on a loss. Use new money or tax-advantaged trades to rebalance without recreating the sold position.
- **rental-first-vs-passive-loss:** The rental-first plan may show a tax loss, but §469 can suspend it instead of reducing the cash cost of the tenant phase. Join the proposed property to its §469 activity by label. Keep the phase pre-investor-tax and use zero current tax benefit unless the gate affirmatively opens; a suspended loss is deferred value, not closing-period cash.
- **employer-income-vs-housing-stress:** The same employer can supply salary, bonus, and equity while also driving the asset decline that accompanies a job loss. Build the conservative case from named compensation components, reducing variable and employer-correlated income without counting any component twice. Use that case for the stress ceiling and keep the current case as capacity, not as the sole answer.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/housing_affordability.py` with their reasons; every figure above is derived, not restated. No market prices, tax rules, or loan-occupancy deadlines are fetched; the report uses only recorded facts.*
