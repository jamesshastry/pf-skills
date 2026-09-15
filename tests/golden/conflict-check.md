# Cross-skill conflict check

Every skill here is individually correct and each is tested in isolation. **Nothing tests the edges between them**, and some of those edges are contradictions — two pieces of correct advice that cannot both be followed.

A household running one skill sees confident advice and no hint the other exists. That is worse than either skill being wrong, because there is nothing on the page to be suspicious of.

**13 conflict(s) live for this household**, involving 19 skills.

## `roth-conversion-window` ⇄ `aca-subsidy-optimization`

**The tension.** One says **raise** taxable income in early retirement to fill low brackets before RMDs. The other says **suppress** modified AGI in those same years, because the premium tax credit tapers as MAGI rises.

**When it bites.** Retiring before 65, so there are years funded on the individual market before Medicare begins. The conversion window and the subsidy years are then the same years.

**How to resolve it.** Price it rather than choosing a side. Each converted dollar costs tax now *and* some subsidy now, and saves tax later. The subsidy loss is immediate and certain; the conversion benefit is deferred and depends on future rates. A common shape is to convert lightly or not at all until Medicare starts, then convert hard between 65 and RMDs — but that window may be short, which is exactly the trade-off.

> **Sized elsewhere.** `lib/pf/healthcare.py — magi_conflicts()` computes the overlap and, where the inputs allow, the cost. This entry says the conflict exists; that one says how much it is worth.

## `roth-conversion-window` ⇄ `medicare-enrollment-timing`

**The tension.** Conversions raise MAGI. IRMAA surcharges look back **two years**, so income at 63 sets Medicare premiums at 65.

**When it bites.** Any conversion in the two years before Medicare enrolment, or in any year once enrolled.

**How to resolve it.** IRMAA tiers are **cliffs, not slopes** — a dollar over a threshold costs the whole step. Size each conversion to the headroom under the next tier rather than to a round number, and remember the lookback means this year's conversion shows up on a premium bill two years from now.

> **Sized elsewhere.** `lib/pf/healthcare.py — magi_conflicts()` computes the overlap and, where the inputs allow, the cost. This entry says the conflict exists; that one says how much it is worth.

## `entity-structure-comparison` ⇄ `solo-retirement-plan-choice`

**The tension.** Lowering W-2 salary in an S-Corp saves payroll tax and preserves qualified business income. Raising it increases the compensation base that the Solo 401(k) employer contribution is calculated on.

**When it bites.** An S-Corp owner-operator funding a Solo 401(k).

**How to resolve it.** The salary that minimises this year's tax is usually not the salary that maximises the shelter. Model both together — optimising either alone gives the wrong number, and the reasonable-salary figure has to survive scrutiny regardless.

## `rent-vs-buy` ⇄ `retirement-readiness`

**The tension.** A down payment moves a large sum out of invested assets. `rent-vs-buy` counts its opportunity cost within the housing comparison; `retirement-readiness` projects from a balance sheet that still includes it.

**When it bites.** A purchase under consideration while a retirement projection is being relied on.

**How to resolve it.** Re-run the retirement projection with the down payment and closing costs removed from investable assets, and with ownership costs rather than rent in spending. The retirement date usually moves, and that movement is part of the price of the house.

## `wash-sale-policy` ⇄ `rebalancing-rules`

**The tension.** Rebalancing buys the asset class that has fallen. Harvesting sells losses in that same class. A purchase within the 61-day window disallows the loss.

**When it bites.** Any taxable account where losses are being harvested — including automatically by a direct-indexing provider.

**How to resolve it.** Rebalance with **new contributions and tax-advantaged accounts first**. Where a taxable purchase is unavoidable, check it against the exclusion list. A purchase in an IRA disallows the loss **permanently, with no basis adjustment**, because the IRA cannot inherit the basis — which is why the policy must span every account.

## `employer-concentration-risk` ⇄ `charitable-giving-strategy`

**The tension.** Not opposed, but competing for the same shares: selling at vest realises gain and diversifies; donating appreciated shares avoids the gain entirely but gives the asset away.

**When it bites.** Concentrated appreciated employer stock plus any charitable intent.

**How to resolve it.** Donate the **most appreciated** lots and sell the rest. Donating avoids the largest embedded gains at no tax cost and reduces concentration at the same time; selling low-basis shares to fund a cash donation wastes the opportunity. Sequence matters more than the totals here.

## `roth-conversion-window` ⇄ `roth-portability-check`

**The tension.** One says convert to fill low brackets before RMDs. The other says a conversion is a **bet that a jurisdiction you may move to honours the Roth wrapper** — and several do not, taxing distributions as ordinary income anyway.

**When it bites.** Conversions contemplated alongside a destination whose Roth treatment is contested or simply not in the table.

**How to resolve it.** A conversion is **irreversible** and recharacterisation is no longer available, so this is not symmetric: converting into a wrapper the destination ignores means paying US tax now for nothing. Resolve the destination question, or at least its probability, before converting — not after. Where the destination is unknown, that uncertainty is itself an argument for converting less.

## `depreciation-election` ⇄ `entity-structure-comparison`

**The tension.** Accelerating cost recovery with §179 or bonus reduces qualified business income — so it also cuts the §199A deduction by twenty cents on every accelerated dollar.

**When it bites.** An owner-operator business claiming QBI and electing accelerated depreciation in the same year.

**How to resolve it.** Model them together. The deduction that minimises this year's taxable income is not automatically the one that maximises after-tax income, because part of it is clawed back through a smaller QBI deduction. Bonus can also create a loss where §179 cannot, which changes which years the benefit lands in.

## `passive-loss-eligibility` ⇄ `aca-subsidy-optimization`

**The tension.** Unlocked rental losses and accelerated depreciation **reduce** AGI — which raises the premium credit and can drop an IRMAA tier. The MAGI discussion elsewhere treats conversions as the only lever.

**When it bites.** Rental activity with deductible losses in a year where the premium credit or an IRMAA tier is in play.

**How to resolve it.** This one runs in the household's favour and is routinely missed for that reason. Count the losses when computing subsidy-relevant MAGI rather than treating the two questions separately — and note it cuts the other way on disposition, when suspended losses release and recapture lands in a single year.

## `asset-allocation-review` ⇄ `pfic-divest-or-comply`

**The tension.** An allocation target with an international sleeve says buy more foreign exposure. PFIC says exit foreign pooled funds. Rebalancing into international through the locally cheapest vehicle is precisely how a PFIC gets bought.

**When it bites.** A target allocation with international exposure alongside any foreign pooled holding.

**How to resolve it.** Hold the international allocation through **US-domiciled** funds. The exposure is the goal; the domicile of the wrapper is what creates the problem, and the two are separable. This is the same conclusion the India portfolio guide reached for a different reason.

## `feie-vs-ftc` ⇄ `contribution-space-audit`

**The tension.** Income excluded under the FEIE is **not compensation** for IRA purposes. Take the exclusion and then fund an IRA and you have made an excess contribution, which carries an annual excise charge until corrected.

**When it bites.** A FEIE election alongside any planned IRA contribution.

**How to resolve it.** Either leave enough income unexcluded to support the contribution, or take the foreign tax credit instead — which preserves IRA eligibility and generates carryforward credits. `feie-vs-ftc` handles this internally; it is registered here so it is visible from the contribution side too, where somebody may be looking at space without knowing an election was made.

## `charitable-giving-strategy` ⇄ `aca-subsidy-optimization`

**The tension.** Charitable deductions are **below the line**. They reduce taxable income and do **not** reduce AGI — so they do nothing for the premium credit, which is computed on MAGI.

**When it bites.** Charitable intent in a year where the premium credit matters.

**How to resolve it.** Do not expect bunching to help the subsidy; it will not. A qualified charitable distribution from an IRA **does** reduce AGI — but only from the qualifying age, which is after Medicare begins, so it arrives too late to help the credit and helps IRMAA instead. Sequence accordingly.

## `education-funding` ⇄ `retirement-readiness`

**The tension.** Education funding competes directly with retirement funding for the same annual savings.

**When it bites.** Dependants with an education obligation and a retirement target not yet reached.

**How to resolve it.** **Already handled inside `education-funding`**, which runs the readiness check and applies the retirement-first rule rather than stating it. Registered here so the resolution is discoverable from either side, and so the next person adding a skill sees the precedent for reaching across.

## Registered but not live

These are real conflicts that this household's facts do not currently trigger. They are listed because facts change:

- `hsa-review` ⇄ `medicare-enrollment-timing` — Approaching Medicare age while still contributing to an HSA.

## One quantity, two keys

A different defect from the conflicts above, and a quieter one. These are not two pieces of advice in tension — they are **one real-world figure recorded under two names**, read by two modules that cannot see each other. Each report stays internally consistent, so there is nothing on either page to be suspicious of.

**§168(k) bonus depreciation percentage** — diverged. Recorded twice with different values: `assumptions.bonus_depreciation_pct` = 1.0 (`depreciation-election` — business equipment), `assumptions.bonus_depreciation_rate` = 0.4 (`cost-segregation-screen` — reclassified property basis). These are the same quantity, so at least one is wrong, and each skill will report a confident figure built on its own copy.

**Shape.** `assumptions.standard_deduction` is a single figure (30000) while `assumptions.federal_brackets` is keyed by 2 filing statuses (married_joint, single). The one figure is used for **every** status, so a status whose real deduction differs gets a plausible liability computed from the wrong deduction. Supply the mapping shape instead.

## What this is not

Not a list of bugs. A conflict here is **two correct answers that cannot both be acted on**, and the resolution is almost never "one of them is wrong" — it is a trade-off someone has to price. The registry's job is to make sure nobody prices it without knowing it is there.

It is also not complete. It holds the conflicts somebody has noticed and written down; the ones nobody has noticed are, by definition, not here. Adding a skill should include asking what it contradicts.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/conflicts.py` with their reasons; every figure above is derived, not restated.*
