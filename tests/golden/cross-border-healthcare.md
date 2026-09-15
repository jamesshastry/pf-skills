# Cross-border healthcare

🚫 **Medicare does not pay for care received outside the United States.** The exceptions are narrow and situational, not a travel benefit. Everything below follows from that one fact.

⚠️ **This cannot be decided on what is recorded.**

## The keep-or-drop arithmetic

|  | Cost |
|---|---|
| Keep Part B for 60 months abroad (premiums for cover you cannot use) | $11,100 |
| Drop it — permanent penalty of 50% (5 full year(s) × 10%) | $92/month |
| Penalty over the years back in the US | $22,200 |

At a standard premium of $185/month, which you supplied — it is not hard-coded here, because it changes annually and a stale figure would go wrong silently.

Over 20 years back in the US. The keep cost is linear in time abroad; the penalty cost is time abroad multiplied by years lived afterwards — which is why long absences followed by long lives favour keeping.

## Findings

- **Medicare does not pay for care outside the United States.** The exceptions are narrow and situational — a foreign hospital nearer than a US one in an emergency, and transit between Alaska and the lower 48 — not a travel benefit. Keeping Part B while living abroad buys nothing usable; it buys the *right to come back without a penalty*, which is a different product and worth pricing as one.

- **Dropping Part B for 60 months means 5 full year(s) uncovered — a permanent 50% surcharge**, about $92/month at today's standard premium, for as long as you hold Part B thereafter. It does not expire and it is not forgiven on appeal for having been abroad.

- **Whether you will return to the US is not recorded, and it decides this.** Never returning makes dropping free; returning makes it expensive. Both arms are priced below rather than one of them being assumed — an unknown intention is not the same as an intention to stay away.

- **If you do return**, keeping is cheaper on these numbers: $11,100 of premiums for unusable cover against $22,200 of permanent penalty over 20 years back in the US. **If you do not**, dropping costs nothing. Record the intention and the report will pick one.

- **Re-enrolment is not on demand.** Someone who dropped Part B gets back in during the General Enrolment Period (1 January – 31 March), so a return in April can mean months uninsured. Living abroad is generally **not** creditable coverage and does not create a special enrolment period — the SEP exists for coverage from current employment, which a foreign retirement is not.

- **The Medigap consequence is worse than the penalty and gets less attention.** Guaranteed issue runs for 6 months from Part B starting. Come back years later in poorer health and a carrier can medically underwrite or decline. The penalty is a known surcharge; being uninsurable for the supplement is not priceable at all.

- **Premiums are income-related.** A Roth conversion raises modified AGI and raises the Part B premium two years later (IRMAA) — and the penalty is a percentage, so a higher base makes the surcharge larger too. See `roth-conversion-window` and `roth-portability-check`.

- Premiums and penalties here are **nominal current-year figures you supplied**, not projected. The standard premium is asked for rather than hard-coded because it changes annually and a stale figure would go wrong silently.

## The Medigap foreign travel benefit is a holiday benefit

- **No Medigap policy**, so there is no foreign travel emergency benefit at all. Traditional Medicare alone pays nothing outside the US.

- Where a Medigap plan includes the foreign travel emergency benefit, it pays 80% of emergency care after a $250 deductible, only during the first 60 days of a trip, up to **$50,000 — a lifetime maximum, not an annual one.** Not every plan letter includes it. Read together, those four limits describe a holiday benefit: one serious admission abroad exhausts the lifetime cap, and month five of a five-month stay is outside the trip window entirely. It is not expatriate cover and should never be planned around as though it were.

| Limit | Value |
|---|---|
| Share of emergency care paid | 80% |
| Deductible | $250 |
| Covered window | first 60 days of a trip |
| Maximum | **$50,000 — lifetime, not annual** |

## The alternative: private expatriate cover

- **No expatriate policy premium is recorded**, so the alternative cannot be priced against the Part B arithmetic above. Get a real quote at your actual age — this is the one input where a placeholder is badly misleading, because expat premiums rise steeply with age rather than smoothly.

- **Check these four before relying on a private expat policy**: whether it is guaranteed renewable or can be declined at the next anniversary; whether it terminates or reprices sharply at an age cap; how pre-existing conditions are treated, which is where most claims fail; and whether it covers repatriation, which is the expensive event nobody budgets for.

- **A destination's public system may or may not admit you**, and on what terms is not in this repository's tables — residency status, contribution history and age limits all bear on it. Find out from the system itself rather than from an expatriate forum.

## What this will not do

- **It does not say whether a destination's public system will admit you**, or on what terms. Residency status, contribution history and age limits all bear on it and none of them is in this repository's tables.
- **It does not project premiums.** Every figure here is a nominal current-year amount you supplied.
- **It does not cover Medicare Advantage**, whose network rules abroad differ from traditional Medicare's and have to be read on the plan.

**The weakest input is whether you will return to the US.** It is an intention rather than a fact, it decides the whole comparison, and it is the one people revise — for family, for care, and because a plan made at 65 is not the plan at 80.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/crossborder.py` with their reasons; every figure above is derived, not restated. Enrolment rules and penalty mechanics should be confirmed against medicare.gov before acting; the premium and penalty figures here are yours, not fetched.*
