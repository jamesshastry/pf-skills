---
name: rental-deal-underwriting
description: Underwrite an investment property on NOI, cap rate, cash-on-cash, DSCR against a lender floor, and multi-year IRR with equity multiple. Use when asked whether a rental deal pencils, what a property's cap rate or cash-on-cash return is, whether a lender will finance it, how to read a broker's pro forma, or to compare two rental purchases. Run passive-loss-eligibility first — an after-tax figure is not available until that gate is passed. Reads figures from a local facts file.
requires:
  - real_estate.deals
---

# Rental deal underwriting

## Run the gate first

`passive-loss-eligibility` decides whether any tax loss from this property can
reach W-2 income. Everything in this report is **pre-investor-tax on purpose**,
because an after-tax return computed behind a shut §469 gate is wrong in the
flattering direction. If someone wants the after-tax number, they need the gate
first and then a preparer.

## NOI excludes debt service. That is the whole point.

The classic error, and the one worth stating before any figure: **net operating
income excludes the mortgage and excludes capital expenditure.**

Debt service is excluded because NOI is a property-level number. It has to be
the same figure whoever buys the building and however they finance it, or cap
rate stops comparing anything — folding the mortgage in flatters a cash
purchase and penalises a leveraged one for no economic reason.

Capex is excluded for a different reason: it is lumpy capital, not an annual
operating cost. But roofs are not optional, so the reserve goes back in **below
NOI**, in the cash flow line. A pro forma that omits it is not reporting cash
flow, it is reporting cash flow until something breaks.

So: NOI = gross rent, less vacancy and credit loss, less operating expenses.
Cash flow = NOI, less debt service, less the capital reserve.

## The four year-one metrics, and what each one is for

**Cap rate** = NOI ÷ price. Unlevered yield on the asset. Its job is comparison
across properties and against the market, nothing else. Below the thin-cap
threshold in the module, the report relabels the deal: whatever return it
produces is coming from appreciation and amortisation, not from the building.

**Cash-on-cash** = year-one cash flow ÷ cash invested, including closing costs.
The only one of the four that answers "what does this do to my bank account
this year". Negative is a position, not automatically a mistake — but it has to
be funded from somewhere for the whole hold, and the report makes you name the
source.

**DSCR** = NOI ÷ annual debt service, and it is the one with an external
referee. Lenders underwrite to a floor of roughly 1.20–1.25; below it the deal
is usually unfinanceable at that leverage, and the fix is a bigger down payment
or a lower price, never a more optimistic rent. Between the floor and the
comfort level there is about one bad quarter of slack.

Below 1.0 the property does not service its own debt and **the borrower's
salary is the reserve** — which is a leveraged bet on personal employment, and
worth saying out loud in those words.

**IRR and equity multiple** over the holding period, from the initial equity
through annual cash flows to net sale proceeds after selling costs and loan
payoff. Both are reported because either alone misleads: IRR flatters a short
hold, the multiple ignores time entirely.

## Read the IRR as a forecast, not a metric

Most of the IRR usually arrives as sale proceeds at the horizon, and the sale
price is an appreciation assumption you supplied. The report names it as the
weakest input every time, and quantifies how much of the return depends on it.

The year-one figures above it do not depend on a forecast. Trust them further.

## Named thresholds, changeable in one place

`DSCR_LENDER_FLOOR`, `DSCR_COMFORT`, `THIN_CAP_RATE`, and the defaults for
vacancy, credit loss, capital reserve and selling costs are all module
constants in `lib/pf/realestate.py`, each with the reason it holds that value.
Disagree with one and change the constant rather than arguing with the output.

Vacancy in particular defaults to a non-zero figure and says so. A package
quoting zero vacancy is quoting something that has never happened over a full
holding period, and assuming zero here would reproduce the error rather than
catch it.

## What it will not do

No price forecast, no rent-comp research, no market data — rent, expenses and
appreciation are yours. No tax layer: no depreciation, no passive-loss
treatment, no after-tax IRR. No financing shop: it prices the loan you
describe. It does not inspect, and deferred maintenance is not in these
numbers.

## Closing

1. **DSCR against the floor** first — it decides whether the deal exists.
2. **Cap rate and cash-on-cash**, separated from the forecast.
3. **IRR and multiple**, with the share of return that is sale-price
   assumption stated.
4. **The gate** — no after-tax figure until `passive-loss-eligibility` passes.

---

*Not financial, tax, or legal advice. Every figure is pre-investor-tax and
nominal.*
