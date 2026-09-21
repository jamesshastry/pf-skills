# Home offer strategy

## BLOCKED — the evidence or affordability chain is incomplete

- Investment financing fails the recorded DSCR test: 0.64 is below 1.20.
- The housing transition misses its savings floor in 4 phase/scenario row(s).

Comparable evidence is still shown below, but no opening offer or walk-away price is recommended while a blocker remains.

All values are **nominal dollars**. The report uses only supplied, verified closed sales; it fetches no market data and is not an appraisal.

## Subject and evidence

| Measure | Result |
|---|---|
| Property | Maple Ridge home |
| List price | $525,000 |
| Verified comps passing selection | 3 of 4 (minimum 3) |
| Stress-tested affordability ceiling | $98,030 |
| Adjusted-value core range | $517,500–$520,000 |
| Median adjusted value | $520,000 |
| Full adjusted-value range | $515,000–$520,000 |

## Comparable adjustments

| Comp | Source | Sold | Age | Miles | Concessions | Adjustments | Adjusted | Adj. $/sf | Gross adj. | Use |
|---|---|---|---|---|---|---|---|---|---|---|
| comp-a | synthetic MLS record A | $510,000 | 46d | 0.4 | $5,000 | +$15,000 | $520,000 | $289 | 3.0% | included |
| comp-b | synthetic MLS record B | $530,000 | 61d | 1.1 | $10,000 | −$5,000 | $515,000 | $286 | 2.9% | included |
| comp-c | synthetic MLS record C | $515,000 | 107d | 0.8 | $0 | +$5,000 | $520,000 | $289 | 1.0% | included |
| comp-old | synthetic MLS record D | $600,000 | 333d | 4.5 | $0 | $0 | $600,000 | $333 | 0.0% | excluded: sale is 333 days old; limit is 180; distance 4.5 mi exceeds 2 mi |

Adjustments are signed from each comparable to the subject. Seller concessions are removed before adjustments; they are not counted twice.

## Property evaluation workflow

| Stage | Skills | Why |
|---|---|---|
| Feasibility | housing-affordability + rent-vs-buy | Set the financial ceiling and compare ownership cost. |
| Property diligence | ca-sfh-disclosure-review + ca-condo-hoa-disclosure-review | Review condition, title, insurability, and association evidence. Run the one applicable California review; use local professional review elsewhere. |
| Price and bid | **home-offer-strategy** | Normalize verified closed sales and set opening and walk-away prices. |
| Whole-plan check | conflict-check + financial-scenario-planner | Resolve competing uses of cash and test the balance-sheet path. Run before committing material cash or debt. |

## Terms and next checks

Comp arithmetic does not price title defects, insurability, deferred maintenance, HOA exposure, or legal terms. Run the applicable property disclosure review and keep inspection, financing, appraisal, title, insurance, and legal protections unless the responsible professionals have separately priced the risk. Use `conflict-check` and a housing scenario before committing material cash or changing the debt plan.

**Weakest input:** the adjustment ledger. Generic dollars per square foot or an agent-selected comp set can make exact arithmetic support a false conclusion.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/home_offer.py` with their reasons; every figure above is derived, not restated.*
