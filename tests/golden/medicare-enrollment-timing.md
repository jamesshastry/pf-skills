# Medicare enrollment timing

**Medicare at 65 — 24 years away.** The year that prices the first premium is the one at age **63**, not 65.

|  |  |
|---|---|
| Initial Enrolment Period | 7 months — 3 before, the birthday month, 3 after |
| Special Enrolment Period (Part B) | 8 months after current-employment coverage ends |
| Part D creditable-coverage gap | 63 days |
| Part B late penalty | 10% per full 12 months — **permanent** |
| Part D late penalty | 1% per uncovered month — **permanent** |
| Premium-free Part A | 40 quarters of covered employment |
| Employer-size threshold | 20 employees — decides who pays primary |
| IRMAA lookback | 2 years |

- **The Initial Enrolment Period is 7 months**: the 3 months before the month of the 65th birthday, that month, and the 3 after. Enrolling in the first three is what avoids a gap in cover; enrolling later in the window delays the start date.

- **250 employees — the group plan is primary.** Part B can be delayed without penalty while that coverage continues, and an **8-month Special Enrolment Period** opens when the employment or the coverage ends, whichever comes first.

- **The Part B penalty is 10% of the standard premium for every full 12 months of eligibility without enrolment, and it is permanent** — two years late means 20% added for life, not for two years. The standard premium itself is an annual figure and is not held here; supply `assumptions.part_b_standard_premium_monthly` for a dollar amount.

- **The Part D penalty is 1% of the national base beneficiary premium per uncovered month, also permanent**, and it applies even to someone who takes no prescriptions — the penalty is for the gap, not for the claims. Creditable drug coverage must not lapse for more than 63 days. Ask the employer plan in writing whether it is creditable; the notice is a legal requirement and it is routinely filed unread.

- **Part A is premium-free** — 40 quarters recorded against the 40 required.

- **IRMAA looks back 2 years.** The premium at 65 is priced from the return for the year the household turns 63 — which is usually a final working year or a conversion year, and is therefore usually the worst year to be measured on. See `aca-subsidy-optimization` for the overlap with the conversion window; the two skills are describing one decision.

- **$100,000 of headroom to the next tier**, which costs a further $1,052/yr per person if crossed. It is a step, not a slope — one dollar over pays the whole step.

- **IRMAA is appealable after a life-changing event**, and work stoppage is one — file SSA-44 rather than paying a surcharge priced off a final working year. A Roth conversion is *not* a qualifying event, which is precisely why conversion years need planning and retirement years often do not.

- ⚠️ **HSA contributions must stop 6 months before Part A begins.** Part A can be granted retroactively up to that far back, and any contribution inside the retroactive period is an excess contribution with a penalty attached. Claiming Social Security also enrols Part A automatically, which catches people who never chose to enrol at all. Cross-check `hsa-review` — the two skills share this constraint and only this one names the deadline.

## What lateness costs, as a multiplier

The penalty is a percentage of a premium this repository does not hold, so it is shown as the multiplier it applies for the rest of the enrollee's life. Multiply it by the standard premium for the year to get a figure.

| Years late | Part B surcharge | Part D surcharge (same gap) |
|---|---|---|
| 1 | +10% | +12% |
| 2 | +20% | +24% |
| 3 | +30% | +36% |
| 5 | +50% | +60% |

Both are permanent and both are charged monthly for life. A three-year delay is not a three-year problem.

## ⚠️ The same MAGI conflict, one layer on

IRMAA is priced from a return filed two years earlier, which puts it in direct tension with `roth-conversion-window` — and with `aca-subsidy-optimization`, which is pulling the same number the same way. All three are describing one decision about one variable.

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

For the full partition of the conversion window — which years are free, which are constrained by the subsidy, and which by both — run `aca-subsidy-optimization`. It holds the sequencing; this skill holds the enrolment deadlines.

## Weakest input

`healthcare.employer_employees` — a single integer that flips the Part B answer from 'safe to delay' to 'enrol now or be uninsured for the Medicare share'. It is also the fact a household is least likely to have checked, and counts can change year to year.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/healthcare.py` with their reasons; every figure above is derived, not restated. Part B and Part D premiums and the IRMAA tier thresholds are annual figures published by CMS and are deliberately not stored here — supply them in the facts file for dollar amounts.*
