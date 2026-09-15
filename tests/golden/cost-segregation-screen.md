# Cost segregation screen

**No property here justifies commissioning a study.** None of 2 clears the 3× benefit-to-fee bar at the conservative end of the range.

**1 of them returns zero for a reason that is not arithmetic**: the §469 gate is shut, so the accelerated deduction enlarges a suspended passive loss rather than reducing tax. Accelerating a loss you cannot deduct is worth nothing — and the study fee is real money.

§469 gate, per activity: **Cedar Park duplex** shut · **Gulf Coast cabin** short-stay.

| Property | §469 gate | Depreciable basis | Reclassified (range) | Year-1 tax saving | PV of the timing benefit | Study fee | Ratio |
|---|---|---|---|---|---|---|---|
| Cedar Park duplex | **shut** | $340,000 | $51,000–$102,000 | $4,451–$8,902 | $0–$0 | $6,500 | — |
| Gulf Coast cabin | open | $355,000 | $53,250–$106,500 | $4,647–$9,295 | $2,285–$4,570 | $6,500 | 0.4× |

The reclassified column is a **screening range**, not an estimate. Producing the actual figure is what the study is.

## Cedar Park duplex

Straight-line recovery 27.5 years.

- Screening range only: a study typically reclassifies 15.0%–30.0% of depreciable basis to 5-, 7- and 15-year property. The real number depends on the building, and producing it **is** the study. Land is never depreciable and must already be excluded from `depreciable_basis` — if the purchase price was entered here, every figure below is overstated.
- **The gate is shut, so the benefit is zero this year.** The $4,451–$8,902 above is what the deduction would be worth *if it could be deducted*. It cannot: it enlarges a suspended passive loss instead, released only against future passive income or on disposition. **Accelerating a loss you cannot use is worth nothing** — and it costs the study fee. Run `passive-loss-eligibility` first and come back if a door opens.

## Gulf Coast cabin

Straight-line recovery 27.5 years.

- Screening range only: a study typically reclassifies 15.0%–30.0% of depreciable basis to 5-, 7- and 15-year property. The real number depends on the building, and producing it **is** the study. Land is never depreciable and must already be excluded from `depreciable_basis` — if the purchase price was entered here, every figure below is overstated.
- Cost segregation is a **timing** benefit, not a permanent one. Over a 10-year hold at 7.0%, deferring $4,647–$9,295 of tax is worth $2,285–$4,570 today. Quoting the year-1 saving as the value of the study overstates it by the whole reversal.
- At the conservative end, present-value benefit of $2,285 against a $6,500 fee is 0.4× — does not clear the 3× bar, so the screen is inside its own error bars — get a free feasibility estimate before paying for the study.
- **Recapture reverses part of it on sale.** The reclassified 5- and 7-year personal property is §1245 property, recaptured at **ordinary income rates** rather than the §1250 rate that applies to the building. If the marginal rate at sale exceeds the unrecaptured §1250 rate, the study has converted some future capital-rate gain into future ordinary income — a rate cost, not just a timing one. A short hold makes that worse, because the deferral has less time to be worth anything.
- Weakest input: the reclassified share. Everything above moves linearly with it, and it is a range precisely because nobody knows it until an engineer walks the building.

## Before acting

- **Confirm land is excluded** from `depreciable_basis`. If the purchase price went in, every figure above is overstated and nothing here can detect it.
- **Ask for the free feasibility estimate** before paying for a study. Most providers give one, and it is a better number than this screen.
- **Decide the exit first.** A sale triggers §1245 recapture at ordinary rates; an exchange defers it. See `1031-exchange-modeling`.
- **A study can be applied to a prior year** via a change in accounting method, without amending. That is a preparer conversation, not a reason to hurry.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/realestate.py` with their reasons; every figure above is derived, not restated. The bonus depreciation percentage and the tax rates come from your facts file, not from a table in this library — the bonus figure is legislated and has changed in most recent years.*
