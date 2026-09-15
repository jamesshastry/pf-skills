# Survivor needs

## If the primary (a1) income stops

|  |  |
|---|---|
| Household spending today | $96,000/yr |
| × survivor factor 75% | **$72,000/yr** |
| Less surviving income | −$0 |
| **Annual shortfall** | **$72,000** |
| Over 51 years at 3% real | **$1,868,488** |
| Final expenses | $20,000 |
| Education obligation | $0 |
| **Total need** | **$1,888,488** |
| Less assets available to survivors | −$423,000 |
| **Capital gap** | **$1,465,488** |

**$1,465,488** is the figure life cover has to close. `life-insurance-review` compares it against what is in force.

- **The surviving spouse is not a US citizen.** The unlimited marital deduction does not apply, so assets passing to them may be reduced by estate tax unless a QDOT is in place. This figure is a *need*, not a projection of what will arrive — see `citizenship-status-review` and `estate-document-review`.

- 2 dependent(s) on file but no education obligation supplied, so **none is included**. If college is intended, add `household.education_obligation` — it is often the largest single line in this calculation.

- The surviving adult has no recorded income. A single-income household carries the whole need on insurance and assets, with no earnings to fall back on — and re-entering the workforce after a long absence rarely replaces a senior salary.

- **The gap decade.** Dependents become independent in about 17 year(s), when the survivor is 56. Survivor benefits for a caregiver generally stop then and do not resume until their own retirement — roughly 6 years funded entirely from capital.

---

Both figures are **real** — today's money throughout, discounted at a real rate. Mixing a nominal rate into a real cash flow overstates the discount and understates the need.

Assets available deliberately include retirement accounts: on death they pass to the survivor. They are *not* included in the absorbability tests used by the property and casualty skills, where the household is still alive and cannot reach them.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/survivor.py` with their reasons; every figure above is derived, not restated. The survivor spending factor is a benchmark — replace it with a real post-loss budget if you have one.*
