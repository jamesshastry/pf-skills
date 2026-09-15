# ACA subsidy optimization

**5 years of health cover to buy privately** — ages 60 to 65.

|  |  |
|---|---|
| Expected gap-year MAGI | $118,000 |
| Poverty level, household of 4 | $32,150 |
| **% of FPL** | **367%** |
| Benchmark silver premium | $21,600 |
| Expected contribution | $9,057 |
| **Estimated credit** | **$12,543/yr** |

- **5 year(s) to fund privately**, ages 60 to 65. Health cover is not a line item in these years, it is a constraint on income — which is a different kind of planning problem from the one a retirement projection solves.

- MAGI of $118,000 against a household-of-4 poverty level of $32,150 is **367% of FPL**. That percentage, not the dollar amount, is what the credit is computed from.

- Estimated credit **$12,543/yr** against a benchmark premium of $21,600, leaving an expected contribution of $9,057.

- ⚠️ **Within 10% of the cliff** — $10,600 of headroom. At this distance MAGI is a control variable, not a forecast: a December capital gain distribution, a rebalance, or an unplanned withdrawal can cross it and cost the whole credit.

- **The credit is reconciled on the tax return.** What is taken monthly in advance is an estimate against a MAGI that is not final until December. Estimate high rather than low: overstating income means a refund, understating it means repaying the excess, and above 400% of FPL with the cliff in force the repayment is the entire year's advance credit.

- **MAGI here is not AGI and not the MAGI used elsewhere.** For the premium tax credit it is AGI plus tax-exempt interest, plus untaxed Social Security, plus excluded foreign earned income. Each of the definitions in the tax code differs slightly and they are routinely conflated — the tax-exempt interest add-back in particular surprises households holding municipal bonds precisely to keep income down.

## ⚠️ Conflict with another skill in this repository

Two skills here give **opposite instructions about the same number in the same years**. This is not a caveat; it is a contradiction, and it is reported rather than resolved silently.

### ACA subsidy taper vs Roth conversion window

*`roth-conversion-window` · `aca-subsidy-optimization` — 5 overlapping year(s), ages 60–65.*

`roth-conversion-window` reports a window at ages 60–70 and tells you to **raise** taxable income inside it. Premium tax credits taper against MAGI, so for ages 60–65 this skill tells you to **suppress** exactly the same number. **5 years are governed by both instructions.**

- **The taper is an unlisted marginal tax rate of 16.9%.** Every extra dollar of MAGI in a gap year loses that much premium credit, *on top of* the income tax on the conversion. A conversion filling a 12% bracket is therefore being done at roughly 29%, and one filling a 22% bracket at roughly 39%. Neither figure appears in any bracket table.

- At the recorded MAGI the credit is worth **$12,543/yr**, so **$62,713** is on the table across the 5 overlapping years. That is the sum a conversion programme is spending, and it is not usually counted as part of the conversion tax.

- **The cliff is the hard ceiling: $10,600 of additional MAGI in a gap year.** Convert one dollar past it and the entire remaining credit is lost at once. This is the single number to plan the conversion against — not a bracket top.

### IRMAA two-year lookback vs Roth conversion window

*`roth-conversion-window` · `medicare-enrollment-timing` — 7 overlapping year(s), ages 63–70.*

IRMAA is set from the return filed **2 years earlier**, so MAGI from age 63 onward prices Medicare premiums from 65 onward. Conversions at ages 63–70 raise premiums two years later — **7 years of the window are affected.**

- **IRMAA is a step, not a slope.** One dollar over a threshold costs the whole surcharge for the year, on both Part B and Part D, per person. For a couple that doubles it. The thresholds are annual figures and are deliberately not held in this repository — supply `assumptions.irmaa_tiers` to have the distance to the next step computed.

- It is also **appealable on a life-changing event**, and retirement is one of them (SSA-44). A premium priced off a final working year can often be reduced — a conversion is *not* a qualifying event, but the work stoppage in the same window is.

## Which years cost what

The conflict resolves into a **sequence**, not a choice. The conversion window splits into segments with different binding constraints, and they are not equally expensive to convert in.

| Ages | Years | What binds |
|---|---|---|
| 60–63 | 3 | ACA subsidy |
| 63–65 | 2 | ACA subsidy + IRMAA |
| 65–70 | 5 | IRMAA |

- **5 year(s) constrained by IRMAA only: ages 65–70.** Convert here **next**. An IRMAA step costs a defined surcharge for one year per person; a subsidy cliff costs the whole credit. The IRMAA cost is bounded and knowable, which makes these years cheaper than the gap years even though they are not free.

- **3 year(s) constrained by the subsidy only: ages 60–63.** These are pre-Medicare years outside the IRMAA lookback, so a conversion costs the taper but nothing later. Convert here **after** the IRMAA-only years and only up to the cliff headroom — past the cliff the marginal cost is not a rate, it is the whole credit.

- **2 year(s) constrained by both: ages 63–65.** Both the subsidy and the future Medicare premium respond to MAGI here. Convert **last and least**, and only up to the cliff headroom.

- **This ordering is not a recommendation to convert.** It says that *if* conversions happen, the sequence above is strictly cheaper than converting evenly across the window, which is what a bracket-filling rule read on its own would produce.

## Weakest input

`assumptions.expected_magi_in_gap_years` — a forecast of a number several years out, made by the household, that the entire result is linear in. Everything else here is a published parameter; this one is a guess, and near the cliff a 10% error in it changes the answer completely.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/healthcare.py` with their reasons; every figure above is derived, not restated. Poverty levels, the applicable-percentage schedule, the benchmark premium and whether the 400% cliff is in force all come from your facts file, not from a table in this repository — they change every year and a stale one is worse than none.*
