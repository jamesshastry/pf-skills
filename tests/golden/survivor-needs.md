# Survivor needs

## If the primary (a1) income stops

|  |  |
|---|---|
| Household spending today | $96,000/yr |
| × survivor factor 75% | **$72,000/yr** |
| Less surviving income | −$0 |
| **Annual shortfall** | **$72,000** |
| Over 51 years at 3% real, before Social Security | $1,868,488 |
| Less Social Security survivor benefits | −$1,021,912 |
| **Capital for income** | **$846,577** |
| Final expenses | $20,000 |
| Education obligation | $0 |
| **Total need** | **$866,577** |
| Less assets available to survivors | −$423,000 |
| **Capital gap** | **$443,577** |

**Before netting Social Security the total need is $1,888,488.** Both figures are shown because excluding Social Security is a defensible choice — some households treat it as conservatism — and the choice should be visible rather than buried in an assumption.

### The survivor benefit does not arrive as a flat amount

Netting an average across the horizon produces the same present value and erases the only feature worth knowing about: the caregiver benefit stops at the youngest child's **16th** birthday, not their eighteenth, and a widow(er)'s benefit cannot start before 60.

| Survivor's age | Payable | What it is |
|---|---|---|
| 39–48 | $67,200/yr *(capped)* | 2 child benefit(s) + caregiver benefit |
| 49 | $57,120/yr | 1 child benefit(s) + caregiver benefit |
| 50–51 | $28,560/yr | 1 child benefit(s) |
| 52–59 | $0/yr | nothing payable |
| 60–66 | $27,456/yr | reduced widow(er)'s benefit |
| 67–89 | $38,400/yr | full widow(er)'s benefit |

**$443,577** is the figure life cover has to close. `life-insurance-review` compares it against what is in force.

- The family maximum binds in at least one year, so the total is less than the individual benefits added together. That is the point of recording it.

- **The gap: ages 52 to 59, 8 year(s) with nothing payable.** The caregiver benefit stops when the youngest child turns 16 — not 18 — and a widow(er)'s benefit cannot start before 60. Those years are funded entirely from capital, and netting a flat average across the horizon would hide them completely.

- **The surviving spouse is not a US citizen.** The unlimited marital deduction does not apply, so assets passing to them may be reduced by estate tax unless a QDOT is in place. This figure is a *need*, not a projection of what will arrive — see `citizenship-status-review` and `estate-document-review`.

- 2 dependent(s) on file but no education obligation supplied, so **none is included**. If college is intended, add `household.education_obligation` — it is often the largest single line in this calculation.

- The surviving adult has no recorded income. A single-income household carries the whole need on insurance and assets, with no earnings to fall back on — and re-entering the workforce after a long absence rarely replaces a senior salary.

- **The gap decade.** Dependents become independent in about 17 year(s), when the survivor is 56. Survivor benefits for a caregiver generally stop then and do not resume until their own retirement — roughly 6 years funded entirely from capital.

---

Both figures are **real** — today's money throughout, discounted at a real rate. Mixing a nominal rate into a real cash flow overstates the discount and understates the need.

Assets available deliberately include retirement accounts: on death they pass to the survivor. They are *not* included in the absorbability tests used by the property and casualty skills, where the household is still alive and cannot reach them.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/survivor.py` with their reasons; every figure above is derived, not restated. The survivor spending factor is a benchmark — replace it with a real post-loss budget if you have one.*
