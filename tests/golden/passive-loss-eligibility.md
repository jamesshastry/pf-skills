# Passive loss eligibility (§469 gate)

**A door is open on 1 of 2 activities.** Gulf Coast cabin (via short-stay).

Run this before `rental-deal-underwriting` and `cost-segregation-screen`. An after-tax return quoted behind a shut gate is wrong, not conservative.

| Activity | Avg stay | Rental activity? | Material participation | Door | Deductible now | Suspends |
|---|---|---|---|---|---|---|
| Cedar Park duplex | 365.0d | yes | yes | **shut** | $0 | $36,000 |
| Gulf Coast cabin | 4.0d | **no** — short-stay | yes | **short-stay** | $31,000 | $0 |

## The three doors

- **Allowance door: closed.** MAGI of $212,000 is at or above the $150,000 phase-out ceiling, so the $25,000 allowance is fully phased out. It reduces by 50% of every dollar above $100,000, which is why a household that earns enough to want it cannot have it.

- **REPS door: closed** — 260 hours is below the 750-hour floor; 260 of 2,340 total working hours is not more than 50% — this is the test a full-time job makes close to unattainable, and it is tested per spouse, not per household.

- 2 activities and no grouping election recorded. Material participation is then tested **separately for each property**, which is how a portfolio that clears the hours in aggregate fails on every individual property. Consider Reg. §1.469-9(g) — but read the disposition consequence above first; the election is not revocable at will.

## Per activity

### Cedar Park duplex

- 120 hours, and more than any other individual — material participation on the 100-hour test.
- **Shut.** $22,000 suspends and carries forward indefinitely. It is not lost: it offsets future passive income, and the whole accumulated balance is released in full on a fully taxable disposition of the activity to an unrelated party.

### Gulf Coast cabin

- 180 hours, and more than any other individual — material participation on the 100-hour test.
- Average stay of 4.0 days is at or below 7, so under Reg. §1.469-1T(e)(3)(ii)(A) this is **not a rental activity**. The per se passive rule never attaches, and material participation alone decides it.
- **Open via short-stay.** $31,000 of current loss is non-passive and reaches wage income.

## Before relying on this

- **Start the participation log today.** Dates, hours, description, kept as you go. An undocumented 750 hours is not 750 hours, and a log written after the notice arrives has been rejected repeatedly in Tax Court.
- **Recompute the average stay from the booking data** — total rental days divided by number of bookings. One long winter booking can push a four-day average over seven and close the only open door.
- **Count the cleaner's hours.** On a short-stay property they routinely exceed the owner's, and the 100-hour test requires more than *any* other individual.
- **§465 at-risk limits apply first**, and are not modelled here.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/realestate.py` with their reasons; every figure above is derived, not restated. The allowance and its phase-out band come from your facts file, not from a table in this library — see REVIEW.md A3. REPS is among the most heavily audited positions in the individual code; take it with a professional who signs the return.*
