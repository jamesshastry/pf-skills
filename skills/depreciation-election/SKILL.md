---
name: depreciation-election
description: Compare §179 expensing, bonus depreciation and the standard mileage rate for an owner-operator's business assets, including the taxable-income limit on §179, the heavy-vehicle GVWR exception to the luxury auto caps, the 50% business-use test and recapture. Use when asked whether to expense or depreciate equipment, whether to buy a heavy SUV or truck for the tax deduction, or whether to claim mileage or actual expenses on a business vehicle. Reads figures from a local facts file.
requires:
  - business.assets
---

# Depreciation election

## The idea

A deduction and a deduction are not the same deduction. Three things separate
them, and each is where an owner-operator gets caught.

## 1. §179 cannot create a loss. Bonus can.

§179 is limited to taxable income from the trade or business. Elect more than
that and the excess does not vanish — it carries forward indefinitely — but it
is **not this year's deduction**, and a decision made on the headline figure
assumed it was.

Bonus depreciation has no income limitation. It can drive the business to a
loss, which may be exactly what is wanted or exactly what is not.

In a thin year the two elections look identical on the invoice and behave
completely differently on the return. That is the whole distinction, and it
runs opposite to the usual advice: a loss is only worth creating if it can be
used.

## 2. Business use must stay above 50%, and falling below it is retroactive

Below 50% business use, neither §179 nor bonus is available at all — the asset
goes on straight line under ADS and the personal share is not deductible.

Worse, if use *drops* below 50% in a later year, the accelerated deduction
already taken is recaptured as ordinary income. That arrives in a year the cash
has been spent and the vehicle is worth less than the tax on it.

The report raises this unprompted when business use is within ten points of the
line. A thin margin over the test is a reason to take the **smaller**
deduction, not the larger one.

## 3. Year one decides the vehicle method — in one direction only

This asymmetry is the decision, and it is invisible in a year-one comparison:

| Year-one choice | What stays available |
|---|---|
| Actual expenses with depreciation | **Standard mileage is closed off permanently** for this vehicle |
| Standard mileage | Either method later — but actual expenses only on straight line |

Standard mileage is the reversible choice. If the two are close in year one,
that optionality is worth something the arithmetic does not show. The standard
rate also already *includes* depreciation, so nothing may be claimed separately
on the same vehicle in the same year, and it reduces basis for the eventual
sale.

## On the heavy-vehicle deduction, honestly

The >6,000 lb GVWR exception to the §280F luxury auto caps is real. A vehicle
above that line escapes the passenger-auto first-year cap, and the year-one
deduction can be large. Between 6,000 and 14,000 lb an SUV is still subject to
a separate §179 cap; above 14,000 lb it generally is not.

It is also **the most aggressively marketed line in small-business tax**, and
the marketing omits the conditions:

- The vehicle must be **placed in service and actually used** in the business
  this year, not bought in December and driven in March.
- Business use must exceed 50%, and the proof is a **contemporaneous mileage
  log** — not a reconstruction after a notice arrives.
- Recapture on a later drop below 50% is real and is ordinary income.
- The deduction is a percentage of *business-use* cost. At 60% use, 40% of the
  purchase is not deductible at all, ever.

A deduction is worth your marginal rate. Buying a vehicle to obtain one costs
the full price. It is worth doing only if the business needed the vehicle.

## Year-specific figures come from your facts file

The §179 limit and its phase-out, the bonus percentage, the SUV cap, both
§280F auto caps and the standard mileage rate are **asked for, never stored
here.** They change annually or by legislation — the bonus percentage has been
legislated up and down more than once — and `REVIEW.md` A3 records the
repository's statutory table as unverified and not to be grown.

Absent a figure, the report names the missing field and produces **no number
for that election**. It does not fall back to last year's.

Two distinct auto caps exist: one where bonus is claimed and a lower one where
it is not. Supplying only the first makes the §179 line optimistic, and the
report says so rather than quietly using the wrong one.

## What it will not do

**It does not produce a multi-year schedule.** This is a year-one election
comparison plus what the election forecloses. MACRS tables for years two
onward are not modelled.

**It does not compare actual expenses against mileage in full** unless
`actual_operating_cost` is recorded. Fuel, insurance, repairs and registration
are deductible under the actual method and already inside the standard rate;
without them the comparison is depreciation against a rate that includes more
than depreciation.

**It does not compute state deductions.** Several states decouple from bonus
and some from §179. A state figure cannot be inferred from the federal one.

**It does not determine whether an asset qualifies.** Listed property rules,
placed-in-service timing, related-party purchases and the difference between an
SUV, a pickup with a six-foot bed and a van all change the answer. GVWR here is
a screen, not a determination.

**It will not assume business use.** Unknown is not 100%, and that assumption
would inflate every figure in the report at once.

## Closing

1. **What actually lands this year** — after the §179 income limit, not the
   headline election.
2. **Whether the election closes off standard mileage**, if it is a vehicle.
3. **How much margin there is over the 50% test**, and what recapture would
   cost if it went.
4. **Whether the business needed the asset.** A purchase is not a saving.

---

*Not financial, tax, or legal advice. Confirm every year-specific figure
against irs.gov for the year the asset was placed in service.*
