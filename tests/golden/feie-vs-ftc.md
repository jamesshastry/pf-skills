# FEIE vs FTC — Form 2555 or Form 1116

Filing status taken as **married_joint**. 2 child(ren) under 17.

**No recommendation is made.**

|  | Form 2555 — exclusion | Form 1116 — credit |
|---|---|---|
| Excluded from income | $130,000 | $0 |
| Taxable income | $20,000 | $150,000 |
| US tax before credit | $4,400 | $22,500 |
| Foreign tax creditable | $5,067 | $38,000 |
| §904 limitation | $1,760 | $18,750 |
| Credit used | $1,760 | $18,750 |
| **US tax owed** | **$2,640** | **$3,750** |
| Carryforward (10 yr) | $3,307 | $19,250 |
| Income supporting an IRA | $20,000 | $150,000 |

On this year's tax alone the **exclusion** is $1,110 cheaper.

- Remaining income is taxed at the rates that would have applied without the exclusion (the §911 stacking rule), not from the bottom bracket up.
- The §904 limitation apportions the standard deduction ratably between foreign- and US-source income. Foreign tax above the limitation is not refunded — it carries.
- Brackets as supplied, dated PLACEHOLDER — round numbers, not a real year's table.

## What the two numbers leave out

This is the section the rule of thumb — *credit in a high-tax country, exclusion in a low-tax one* — does not have. It is directionally right and it answers a smaller question than the one asked.

| Consequence | Favours | Valued at |
|---|---|---|
| IRA contribution room | Form 1116 | $0 |
| Refundable child tax credit | Form 1116 | **not valued** |
| Foreign tax credit carryforward | Form 1116 | **not valued** |

- The planned $7,000 contribution is supported under either election — $20,000 of compensation survives the exclusion. Worth re-checking in any year income falls, because the exclusion is a fixed amount and compensation is not.

- **Filing Form 2555 disqualifies the household from the refundable additional child tax credit entirely** — Schedule 8812 asks the question directly. With 2 qualifying child(ren) and little or no US tax left to offset, the refundable portion is frequently the *only* part of the credit worth anything to an expat, so this is not a rounding item. It is left unvalued because `assumptions.additional_ctc_per_child` is not recorded; the amount is year-specific and this repository does not hold it.

- The credit route generates **$19,250 of unused credit**, carrying back 1 year and forward 10. The exclusion generates $3,307. It is deliberately left unvalued: it is usable only against future US tax on foreign-source income in the same basket, so a household returning to the US next year will never use it, and one staying abroad probably will. Value it yourself against your own plan — it is an option, not a receivable.

- **The arithmetic favours the exclusion by $1,110, and no recommendation is made anyway**, because *Refundable child tax credit*; *Foreign tax credit carryforward* points the other way and cannot be valued from the facts recorded. Supply what is missing, or decide it deliberately. This is exactly the case the rule of thumb gets wrong: the current-year bill is the visible number and the smaller question.

## What this does not model

- **Self-employment tax.** §911 excludes income from *income* tax, not from SE tax. A self-employed expat owes roughly 15.3% on the excluded income anyway unless a totalization agreement covers them — and for some countries there is no agreement at all.
- **The foreign housing exclusion or deduction**, which rides on the same Form 2555 and can be worth more than people expect in an expensive city.
- **NIIT, AMT, itemised deductions, and the passive basket.** Foreign tax on investment income sits in a different credit basket and cannot be netted against the general one; nothing above attempts to.
- **State tax.** If a state still treats the household as resident, it may not conform to §911 at all. Run `state-domicile-exit`.
- **Any filing position.** This ends at a cross-border CPA or EA, and so does every other skill in this cluster.

**Weakest input:** the bracket table and standard deduction supplied in the facts file. Everything above is arithmetic on top of them, and nothing in this repository can tell whether they are the right year's.

**Being tax resident nowhere does not make a US citizen tax resident nowhere.** US taxation follows citizenship, not sleep. Someone moving between countries fast enough to trip no local threshold still files a US return on worldwide income — and has made their position *worse*, not better: with no foreign tax paid there is nothing to credit, and with no foreign tax home the §911 exclusion is unavailable even if the 330 days are there. The strategy that actually reduces the bill is the opposite one — becoming properly resident somewhere, and using the tax that creates.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/expat.py` with their reasons; every figure above is derived, not restated. Brackets, the standard deduction, the exclusion cap and the refundable child-credit amount come from your facts file, not from a tax table held here — keep them current and year-matched.*
