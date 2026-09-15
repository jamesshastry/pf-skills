# Foreign presence tests

Ledger: **5 stay(s)**, <DATE> to <DATE> (638 days). Tax year taken as **2025**.

- Physical Presence Test counts a complete 24-hour period present in a foreign country — travel days to or from the US, and days over international waters, do not count.
- The destination and state counts below use the other basis: any part of a day physically present counts as a day. **The same trip therefore produces different numbers in different rows, and both are correct.**

- ⚠️ **3 day(s) inside the ledger's span are unaccounted for**, in 1 gap(s). They are counted as *not* full foreign days. That is deliberate — under audit the ledger is the evidence, and a day nobody recorded is a day nobody can prove.

## Physical Presence Test — 330 full days in any 12 months

✅ **Met**, on the best 12-month window available.

| Window | Full foreign days | Against 330 |
|---|---|---|
| <DATE> → <DATE> (best rolling) | 360 | pass |
| Calendar 2025 | 310 | fail |

- **The calendar year fails and a rolling window passes.** 310 full days in 2025 against 360 in the 12 months from <DATE>. The test is *any* period of 12 consecutive months, and choosing it well is the difference between the exclusion being available and not. The exclusion is then prorated by the qualifying days falling inside the tax year, so the placement moves the amount as well as the eligibility.

**The window is the optimisation.** The test is any period of twelve consecutive months, chosen by you, and the exclusion is then prorated by the qualifying days that fall inside the tax year — so where the window sits changes both whether the exclusion is available and how much of it is.

A day at the edge of the ledger does not count, because a day with an unknown neighbour cannot be shown to have been complete. Extend the ledger a few days either side of every trip and those days come back.

## Bona fide residence — the other route, and not a day count

This test is not arithmetic and no verdict is offered on it. What is checkable is checked; sufficiency is an IRS determination on facts and circumstances.

| Condition |  | Why it decides claims |
|---|---|---|
| Uninterrupted period covering all of 2025 | 🚫 | The period must include one **entire** tax year. A move in June qualifies for the following full year, not the year of the move — though once qualified, the earlier and later partial years can be claimed too. |
| No abode retained in the US | 🚫 | **A tax home abroad is defeated by an abode in the US**, and this sinks more claims than the day count does. It is about where personal and family ties sit, not where a house is owned — a rented family home kept available, with a spouse and children living in it, is an abode. |
| Did not claim non-residence to the host country | ✅ | Telling the host country you are a non-resident, to avoid its tax, and telling the IRS you are a bona fide resident of it, is an inconsistency Form 2555 asks about directly. It generally ends the claim. |
| Assignment is indefinite rather than for a stated short term | · unknown | A posting with a defined end date, with the family and the home left behind, reads as a temporary absence from a US residence rather than residence abroad. |

- **Some of these have not been answered.** Unanswered is not the same as satisfied; each one has ended a claim on its own.

**The abode question is not confined to this test.** §911 requires a tax home in a foreign country under *either* route, and an abode retained in the US defeats it — so a household that meets the 330-day count and keeps a home available in the US may still have no exclusion. The day count is necessary, not sufficient.

## The destination's own residency threshold

| Country | Days present | Recorded threshold | Crossed |
|---|---|---|---|
| PT | 311 | 183 | yes |

- **311 days in PT against a recorded threshold of 183 — crossed.** Expect a local filing obligation and local tax on some or all income. That is not necessarily bad: foreign tax paid is what feeds the Foreign Tax Credit. It does mean a second return, and it is the point at which a treaty tie-breaker becomes relevant.

**No country's residency rule is encoded in this repository.** The threshold above is whatever you recorded. Check how that country actually counts before relying on it — rolling windows, weighted prior years and split-year rules all exist, and a bare number does not capture them.

## The perpetual traveler myth

**Being tax resident nowhere does not make a US citizen tax resident nowhere.** US taxation follows citizenship, not sleep. Someone moving between countries fast enough to trip no local threshold still files a US return on worldwide income — and has made their position *worse*, not better: with no foreign tax paid there is nothing to credit, and with no foreign tax home the §911 exclusion is unavailable even if the 330 days are there. The strategy that actually reduces the bill is the opposite one — becoming properly resident somewhere, and using the tax that creates.

**Weakest input:** the ledger itself. Every number above is a count of rows somebody typed. Reconstruct it from passport stamps, boarding passes and card transactions rather than memory, and keep it as you go — under examination the ledger is the evidence, and a calendar built afterwards is worth much less than one kept at the time.

---

*Not financial, tax, or legal advice. Thresholds are in `lib/pf/presence.py` with their reasons; every figure above is derived, not restated. Qualifying for §911 also requires a tax home in a foreign country, which days alone do not establish — see `feie-vs-ftc`.*
