---
name: foreign-presence-tests
description: Evaluate the 330-day Physical Presence Test across every rolling twelve-month window, check what is checkable about bona fide residence, and count days against a destination country's own residency threshold — all from one travel ledger, with the different definitions of a day made explicit. Use when living or working abroad, before claiming the foreign earned income exclusion, or when wondering whether enough time has been spent somewhere to become tax resident there. Reads figures from a local facts file.
requires:
  - household.members
  - presence.days
---

# Foreign presence tests

## One ledger, because a day means three things

The same trip produces three different day counts, and all three are correct:

- **§911's Physical Presence Test counts full days** — a complete 24-hour
  period in a foreign country. A travel day to or from the US is not one, and
  neither is a day over international waters, even between two foreign points.
- **A destination's residency threshold** — the 183-day family — almost always
  counts any part of a day.
- **A US state** counting days toward statutory residence generally counts any
  part of a day too, with its own exceptions.

Two implementations of "a day" eventually disagree about the same Tuesday, and
the disagreement surfaces as a number nobody can reconcile. So there is one
ledger, and the definitions are attached to it rather than to whoever is
counting. `state-domicile-exit` reads the same ledger for state days.

## The window placement is a real optimisation

The test is **any** period of twelve consecutive months, chosen by you — not
the calendar year. A household that left in March and counts January to
December fails; the same travel counted from March to the following February
passes. So this searches every window rather than counting the tax year, and
reports both, because the difference between them is the difference between
having the exclusion and not.

It matters twice over: the exclusion is then prorated by the qualifying days
falling inside the tax year, so the placement moves the amount as well as the
eligibility.

## Unknown days count against you

A gap in the ledger is counted as *not* a full foreign day, and the days at
each end of the ledger do not count either — a day with an unknown neighbour
cannot be shown to have been complete. That is deliberate and it is the
conservative direction: under examination the ledger **is** the evidence, and
a day nobody recorded is a day nobody can prove. Recording a few days either
side of each trip recovers them honestly.

## Bona fide residence gets checks, not a verdict

It is not a day count. It turns on intent, the nature of the stay, and what
you told the host country — a facts-and-circumstances determination the IRS
makes. So the necessary conditions are checked and the conclusion is not
offered. Two of those conditions end more claims than the day count does:

- **An abode retained in the US defeats a foreign tax home.** It is about
  where personal and family ties sit, not who holds the deed.
- **Telling the host country you are a non-resident** while telling the IRS
  you are a bona fide resident of it is an inconsistency Form 2555 asks about
  directly.

There is also an eligibility gate worth knowing before planning around this
route: it is open to US citizens, and to resident aliens who are citizens or
nationals of a treaty country with a non-discrimination article. **The
Physical Presence Test has no such gate.** Whether a particular treaty
qualifies is not encoded here.

## No country's threshold is encoded here

Not one. The destination's threshold is supplied in the facts file — asked
for, never fetched — on the same terms as the cash benchmark. A 183-day rule
written from memory would be wrong for the country where it mattered, and some
jurisdictions use rolling windows, weight prior years, or have split-year
rules that change the answer entirely. Supply it, and check how that country
counts.

A day count is usually the backstop test anyway. A permanent home, a centre of
vital interests, or habitual abode can make someone resident well under the
threshold.

## The perpetual traveler myth

Worth stating because the arithmetic here invites it: **being tax resident
nowhere does not make a US citizen tax resident nowhere.** US taxation follows
citizenship, not sleep. Moving fast enough to trip no local threshold leaves
the US return exactly where it was and makes the position worse — no foreign
tax to credit, and no foreign tax home, so the exclusion is unavailable even
with 330 days in hand. The structure that actually reduces the bill is the
opposite one: becoming properly resident somewhere, and using the tax that
creates.

## Closing

1. **Read the best window, not the calendar year.** If they differ, that is
   the finding.
2. **Fix the ledger before fixing the plan.** Gaps and edges cost real days.
3. **Days are necessary and not sufficient.** §911 also needs a tax home
   abroad; see `feie-vs-ftc`.
4. **Then `state-domicile-exit`** — leaving the country does not by itself
   leave a state.

---

*Not financial, tax, or legal advice. Residency is determined on the full facts, not a day
count.*
