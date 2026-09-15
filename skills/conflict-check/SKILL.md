---
name: conflict-check
description: Identify where two skills in this library would give the same household opposite instructions — Roth conversions against ACA subsidies, S-Corp salary against Solo 401(k) room, rebalancing against wash-sale windows. Use when following advice from more than one skill, before acting on a recommendation that changes taxable income, or when two reports seem to disagree. Reads figures from a local facts file.
requires:
  - household.members
---

# Cross-skill conflict check

## The gap this exists to close

Every skill here is individually correct, and each is tested in isolation.
**Nothing tests the edges between them** — and some of those edges are
contradictions.

The worked example: `roth-conversion-window` says deliberately **raise**
taxable income in early retirement to fill low brackets before RMDs.
`aca-subsidy-optimization` says **suppress** modified AGI in exactly those
years, because the premium tax credit tapers. Both are right. For a household
retiring before 65, they are describing the same years.

Someone running one skill sees confident advice and no hint the other exists.
That is a worse failure than either skill being wrong, because **there is
nothing on the page to be suspicious of.**

## A conflict is not a bug

It is two pieces of **correct** advice that cannot both be followed. The
resolution is almost never "one of them is wrong" — it is a trade-off the
household has to price. This skill's job is to make sure nobody prices it
without knowing it is there.

## Why a registry rather than cross-imports

`education-funding` reaches into the retirement projection to apply the
retirement-first rule, and that coupling is earned — the rule is worthless
abstract and useful applied. Doing that for every pair would produce a
dependency graph nobody can reason about.

So conflicts are declared as **data**, in one place, each with the condition
that makes it live. Adding a skill means asking what it contradicts, and the
answer lives in the registry rather than in either skill.

## Reading the output

**Live** conflicts are triggered by the facts recorded. **Dormant** ones are
real but not currently triggered — listed because facts change, and because a
household planning to retire early should see the conversion/subsidy conflict
before it becomes live rather than after.

## The honest limit

This registry holds the conflicts somebody has **noticed and written down**.
The ones nobody has noticed are, by definition, not in it. It reduces the
problem; it does not solve it. Treat a clean report as "no known conflict",
not as "no conflict".

## Closing

1. **Live conflicts first**, each with the trade-off stated rather than
   resolved.
2. **Which skills are implicated** — those reports should be read together.
3. **Dormant ones** if a plan would trigger them.

---

*Not financial, tax, or legal advice.*
