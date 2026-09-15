# Geo arbitrage model

Blended burn **$80,000/yr** against **$102,000** for a full year at the dearest location — a saving of $22,000/yr, which cuts the portfolio target by **$550,000** at a 4.0% withdrawal rate.

## The split

| Location | Country | Months | Monthly | Annual | Est. days | Currency |
|---|---|---|---|---|---|---|
| Austin | US | 7 | $7,000 | $49,000 | 213 | home |
| Bengaluru | IN | 5 | $2,600 | $13,000 | 152 | **foreign** |

Plus $18,000/yr of costs that do not move with location. Estimated days are months × 30.44 — an estimate for flagging day tests, never a substitute for counting real days.

## The target, three ways

| Scenario | Annual burn | Target | Years to it |
|---|---|---|---|
| Full year at the dearest location | $102,000 | $2,550,000 | 21 |
| **Blended, as planned** | **$80,000** | **$2,000,000** | **17** |
| Blended, 20% adverse FX | $82,600 | $2,065,000 | — |

Assets $423,000, savings $42,000/yr, 5% real return. Targets use `retirement.target_for` and years use `retirement.years_to` — the same machinery as `retirement-readiness`, imported rather than reimplemented, so a location-adjusted target and an ordinary one cannot drift apart.

**Plan on the stressed row.** The saving is denominated in a currency the household neither earns nor holds, and that is the weakest input in the model — everything else here is arithmetic on figures you supplied.

## Findings

- **Every dollar off the annual burn takes 25 dollars off the target.** The blended $80,000 against a full year at the dearest leg ($102,000) saves $22,000 a year, which cuts the portfolio target by **$550,000**. That multiplier is why spending is the strongest lever in retirement planning and why location is the strongest lever on spending.

- On the same assets and savings, that is **4 year(s) earlier** — 17 years to the blended target against 21 to the full-cost one.

- **The saving is denominated in a currency you neither earn nor hold.** At a 20% adverse move on the Bengaluru leg(s), the blended burn rises to $82,600 and the target to $2,065,000 — giving back $65,000 of the $550,000 the move bought. This is the weakest input in the model: everything else here is arithmetic on figures you supplied, and this is a guess about exchange rates over decades. Treat the stressed row as the planning figure.

- **Whether housing is paid for in both places year-round is not recorded**, so it cannot be determined whether these monthly figures overlap. A split-living arrangement frequently pays rent or carrying costs in both locations for all twelve months while only occupying one, which can erase most of the saving above. Record `duplicate_housing` rather than letting the model assume the favourable case.

- 🚫 **Bengaluru: roughly 152 days a year crosses IN's 'resident — 60 days plus 365 over four years' test at 60 days.** 60 days or more in the year *and* 365 days or more across the four preceding years. This is the test that catches a split-living arrangement nobody thought was close to residency. This arrangement makes you tax resident there, which brings worldwide income into scope and changes every other answer in this repository. Count real days from a travel log — this figure is months × 30.44, which is an estimate, not a count.

- Every figure here is **real** — today's money — because it feeds `retirement.py`, which is real throughout. Local inflation in the cheaper location is the thing most likely to erode this over decades, and it is not modelled: a constant real cost differential is an assumption, not a finding.

- **Healthcare is not in these numbers and is usually the largest single line.** Medicare does not travel — see `cross-border-healthcare` before treating the saving above as spendable.

## What this will not do

- **It does not model local inflation.** A constant real cost differential over decades is an assumption, not a finding, and it is the thing most likely to erode this quietly.
- **It does not decide whether you are tax resident anywhere.** It flags where an estimated day count crosses or approaches a recorded threshold, from a table holding only IN, US.
- **It does not price healthcare**, which is usually the largest single line in an arrangement like this. See `cross-border-healthcare`.
- **It does not ask whether you want to live this way.** Two households a year, two sets of friendships, and a travel schedule are the actual cost, and no model here captures them.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/crossborder.py` with their reasons; every figure above is derived, not restated. Figures are real — today's money — throughout. Tax residency consequences of a split-living arrangement need a cross-border professional, not a day estimate.*
