# Social Security timing

Full retirement age **67**. Benefit relative to the full-retirement amount:

| Claim at | Benefit |
|---|---|
| 62 | 70% |
| 63 | 75% |
| 64 | 80% |
| 65 | 87% |
| 66 | 93% |
| 67 | 100% ← full |
| 68 | 108% |
| 69 | 116% |
| 70 | 124% |

Percentages are the statutory adjustment, applied to your own benefit amount — which comes from your Social Security statement, not from this skill.

### Your recorded amounts, beside the percentages

| Claim at | Monthly | Annual |
|---|---|---|
| 62 | $2,240 | $26,880/yr |
| 67 | $3,200 | $38,400/yr |
| 70 | $3,968 | $47,616/yr |

Read from `social_security.retirement_monthly`, statement dated **<DATE>**. These are transcribed from the statement, not computed here — a benefit this skill calculated would be a guess wearing a statement's clothes. Re-pull the statement annually; the figures move with the earnings record.

- Whether a US–CA totalization agreement exists is not in the table. It determines whether contributions are duplicated and whether coverage periods combine — check ssa.gov/international rather than assuming.

- **Payment of benefits outside the US is restricted for non-citizens.** Entitlement and payability are different questions: credits can be fully earned and payment still stop after an extended absence, depending on citizenship and country of residence. The exceptions are specific and this table does not encode them — confirm with SSA before a plan depends on benefits arriving abroad.

## The spouse's own record

- **A short work history does not reduce spousal or survivor benefits.** Neither requires the spouse's own credits, so entitlement is unaffected — the usual intuition here is simply wrong, and acting on it wastes years.

- **But there is no floor.** Every dollar of this spouse's Social Security flows through the worker's record rather than their own, so anything that interrupts payment on that record interrupts all of it rather than part of it.

- **And their benefit is coupled to the worker's filing date.** A spousal benefit cannot begin until the worker files, so a decision to delay to 70 silently defers the spouse's income too — that cost belongs in the delay calculation and is routinely left out.

- Whether benefits are payable abroad is not recorded. For a spouse with no record of their own this is the difference between some exposure and total exposure — worth an answer from SSA rather than an assumption.

- Building the spouse's own record raises the household total only once their own benefit would exceed **half the worker's PIA** (about $1,600/mo on this statement). A late, short career averaged over 35 years rarely clears that bar — confirm against the spouse's own statement rather than assuming either way. Add `social_security.spouse_own_projected_monthly` to test it.

- Full retirement age **67**. Claiming at 62 costs roughly 30% permanently; waiting to 70 adds roughly 24%.

- **The benefit is inflation-adjusted and lasts as long as you do**, which makes delaying less an investment decision than the purchase of longevity insurance. Framing it as a break-even calculation against an assumed death date misses what it is actually for: the risk being insured is living a long time, not dying early.

- **For a single-income couple this is mostly a survivor decision, and that is usually the whole argument.** When one spouse dies the household keeps the *larger* of the two benefits, not both. Delaying the higher earner's claim raises the floor under the survivor for the rest of their life — often decades — and a non-earning spouse has no benefit record of their own to fall back on. This consideration routinely outweighs the break-even arithmetic and is routinely left out of it.

- Claiming early while still working can also trigger the earnings test, withholding benefits above an annual threshold.

## How to think about it

**Not as a break-even calculation.** The usual framing — *at what age does waiting pay off?* — quietly assumes you know when you will die, and answers the wrong question. The benefit is inflation-adjusted and lasts as long as you do, which makes delaying a purchase of longevity insurance. The risk being insured is living a long time.

Reasons to claim early that are actually good ones: poor health with a genuinely shortened life expectancy; needing the income now and having no alternative; or a portfolio so large the benefit is irrelevant either way.

Reasons that are not: *getting back what I paid in*, and *the programme might change*. Neither survives contact with the arithmetic, and the second argues for delaying if anything.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/retirement.py` with their reasons; every figure above is derived, not restated. Statutory adjustment rates only. Your actual benefit, spousal eligibility and earnings-test thresholds come from ssa.gov.*
