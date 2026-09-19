---
name: housing-affordability
description: Reconcile household income and cash uses, determine a feasible home-price target and stress-tested ceiling, test cash-only closing reserves, and model rent-first or other phased housing transitions. Use when asked how much home a household can afford or whether a proposed purchase and occupancy timeline fits. Reads figures from a local facts file.
requires:
  - household.members
  - household.balance_sheet
  - retirement.annual_savings
  - cash_flow.scenarios
  - housing.monthly_rent
  - housing.purchase
  - housing.affordability
  - housing.transition
---

# Housing affordability

## The decision

Find a target price that survives four separate constraints: current cash flow,
a conservative income case, lender DTI when supplied, and cash-only closing
liquidity after the reserve requirement. Report every limit and name the one
that binds. A conservative ceiling is a stress boundary, not the only price the
household may consider.

## Reconcile before calculating

Income components are the source of gross income. Recorded gross, taxes,
after-tax cash income, and legacy retirement savings are cross-checked when
both sides exist. A material mismatch blocks the answer instead of becoming a
footnote.

After-tax cash income means compensation after taxes but before the separately
listed retirement contributions, payroll deductions, and committed uses. The
savings floor is the greater of its dollar amount and gross-income-rate amount
when both are supplied.

## The invariant

Pre-housing surplus contains neither rent nor owner cost. Subtract the full
owner cash cost from it. The report also calculates the equivalent renter
bridge and asserts the two owner-savings figures agree. Never subtract only
incremental ownership cost from a pre-rent surplus.

Mortgage principal is a cash outflow here. It is not an economic cost in
`rent-vs-buy`; that report answers a different question after feasible prices
are known.

## Liquidity is not a synonym for cash

Use `liquidity_class`, not the legacy `tier`, for reserves. Marketable stock
must be sold through the taxable sources-and-uses ledger before its proceeds
become closing cash. The sale replaces an asset; it does not create wealth.
Missing basis, holding period, losses, account debt, or tax rates blocks the
liquidation calculation.

## Phases

Treat current renting, tenant operation, owner occupancy, and land carry as
mutually exclusive phases. A rent-first property joins to the existing rental
underwriting and §469 gate by label. Tenant income and current-home rent stop
at conversion; owner costs begin then. The property table remains nominal and
pre-investor-tax unless an explicit tax result exists, and a shut or unresolved
§469 gate contributes zero current tax benefit.

Never invent an owner-occupancy deadline. If owner-occupied financing is
assumed, compare the planned tenant period with the actual requirement recorded
in the facts file and block an inconsistent plan.

## Closing

Lead with the target and stress-tested ceiling, then show the current-income,
lender, and liquidity limits. Keep cash-flow affordability separate from the
economic-cost comparison. Name every default and every unclassified asset.

## Time-series output

Emit current, stress, liquidity, and each named cash-flow price ceiling. Keep
current and conservative cases separate even when calculated on the same date.

---

*Not financial, tax, or legal advice. Nominal cash flow throughout.*
